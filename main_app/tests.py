from datetime import date, timedelta
from decimal import Decimal

import os
import shutil
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from .api.library import MAX_OPEN_PER_STUDENT
from .fee_billing import (NothingToBill, add_adjustment, bill_active_cohorts,
                          generate_invoices, signed_amount)
from .idgen import (
    assign_student_numbers, lock_batches_for_course, next_employee_id,
    resequence_cohort)
from .library_reminders import send_due_soon_reminders
from .models import (DUE_SOON_REMINDER_DAYS, FINE_PER_DAY, LOAN_PERIOD_DAYS,
                     RENEWAL_PERIOD_DAYS, Accountant, Admin, Book, BookRequest,
                     Course, CustomUser, DepositSlip, FeeAdjustment, FeeHead,
                     FeeInvoice, FeePayment, FeeStructure, FeeStructureItem,
                     Librarian, LibraryFine, NotificationStudent,
                     RollNumberBatch, Session, Staff, Student)


def make_student(first, last, session, course, semester=1, shift="morning"):
    user = CustomUser.objects.create_user(
        email="%s.%s@ncit.edu.np" % (first.lower(), last.lower()),
        user_type=3, first_name=first, last_name=last)
    student = user.student
    student.session, student.course = session, course
    student.current_semester = semester
    student.shift = shift
    student.save()
    return student


def rolls(session, course):
    """(last name, roll number) for a cohort, in roll-number order."""
    return [(s.admin.last_name, s.roll_number) for s in Student.objects.filter(
        session=session, course=course).select_related('admin').order_by(
        'roll_number')]


class EmployeeIdTests(TestCase):
    def test_serial_runs_per_joining_year(self):
        self.assertEqual(next_employee_id(2025), "250001")
        Staff.objects.create(
            admin=CustomUser.objects.create_user(
                email="a@ncit.edu.np", user_type=1),
            staff_id="250001")
        self.assertEqual(next_employee_id(2025), "250002")
        # A new year restarts the serial but keeps IDs distinct via the prefix.
        self.assertEqual(next_employee_id(2026), "260001")

    def test_numbers_are_not_reused_after_a_deletion(self):
        user = CustomUser.objects.create_user(email="b@ncit.edu.np", user_type=2)
        user.staff.staff_id = next_employee_id(2025)
        user.staff.save()
        user.delete()
        self.assertEqual(Staff.objects.count(), 0)
        # 250001 belonged to someone; the next hire must not inherit it.
        self.assertEqual(next_employee_id(2025), "250002")

    def test_every_staffroom_role_shares_one_counter(self):
        """An employee ID identifies a person, not a person-within-a-role, so
        neither the librarian nor the accountant may be handed the teacher's
        number."""
        staff_user = CustomUser.objects.create_user(
            email="teacher@ncit.edu.np", user_type=2)
        staff_user.staff.staff_id = next_employee_id(2025)
        staff_user.staff.save()

        lib_user = CustomUser.objects.create_user(
            email="librarian@ncit.edu.np", user_type=4)
        lib_user.librarian.librarian_id = next_employee_id(2025)
        lib_user.librarian.save()

        acc_user = CustomUser.objects.create_user(
            email="accounts@ncit.edu.np", user_type=5)
        acc_user.accountant.accountant_id = next_employee_id(2025)
        acc_user.accountant.save()

        self.assertEqual(staff_user.staff.staff_id, "250001")
        self.assertEqual(lib_user.librarian.librarian_id, "250002")
        self.assertEqual(acc_user.accountant.accountant_id, "250003")
        self.assertEqual(next_employee_id(2025), "250004")


class LibrarianRoleTests(TestCase):
    def test_creating_a_type_4_user_creates_the_profile(self):
        user = CustomUser.objects.create_user(
            email="lib@ncit.edu.np", user_type=4, first_name="Rita",
            last_name="Gurung")
        self.assertEqual(Librarian.objects.count(), 1)
        self.assertEqual(user.librarian.admin_id, user.id)

    def test_the_other_roles_get_no_librarian_profile(self):
        for user_type in (1, 2, 3, 5):
            CustomUser.objects.create_user(
                email="u%d@ncit.edu.np" % user_type, user_type=user_type)
        self.assertEqual(Librarian.objects.count(), 0)


class AccountantRoleTests(TestCase):
    def test_creating_a_type_5_user_creates_the_profile(self):
        user = CustomUser.objects.create_user(
            email="accounts@ncit.edu.np", user_type=5, first_name="Sabina",
            last_name="Shrestha")
        self.assertEqual(Accountant.objects.count(), 1)
        self.assertEqual(user.accountant.admin_id, user.id)

    def test_the_other_roles_get_no_accountant_profile(self):
        for user_type in (1, 2, 3, 4):
            CustomUser.objects.create_user(
                email="u%d@ncit.edu.np" % user_type, user_type=user_type)
        self.assertEqual(Accountant.objects.count(), 0)


class AccountantApiTests(TestCase):
    """Who may manage the accounts office, and who may see its dashboard.

    The split this role exists for is the point of these: the admin creates
    and removes accountants but does not act as one, and nobody else gets
    near either side.
    """

    ACCOUNTANT_PAYLOAD = {
        'first_name': 'Sabina', 'last_name': 'Shrestha',
        'email': 'sabina@ncit.edu.np', 'gender': 'F',
        'address_line1': 'Lalitpur',
    }

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="pw", user_type=1)

    def make_accountant(self):
        user = CustomUser.objects.create_user(
            email="accounts@ncit.edu.np", password="pw", user_type=5,
            first_name="Sabina", last_name="Shrestha")
        return user

    def test_admin_creates_an_accountant_with_an_id_it_never_asked_for(self):
        self.client.force_login(self.admin)
        response = self.client.post("/api/v1/accountants/",
                                    self.ACCOUNTANT_PAYLOAD)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['accountant_id'],
                         "%02d0001" % (date.today().year % 100))
        created = CustomUser.objects.get(email='sabina@ncit.edu.np')
        self.assertEqual(str(created.user_type), '5')
        # Same creation flow as staff/librarians: no usable password, and the
        # account stays shut until the owner follows the emailed link.
        self.assertFalse(created.is_active)

    def test_a_posted_accountant_id_is_ignored(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/v1/accountants/",
            dict(self.ACCOUNTANT_PAYLOAD, accountant_id='999999'))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotEqual(response.data['accountant_id'], '999999')

    def test_only_the_admin_may_manage_accountants(self):
        for user_type, email in ((2, 'staff@ncit.edu.np'),
                                 (3, 'student@ncit.edu.np'),
                                 (4, 'lib@ncit.edu.np'),
                                 (5, 'acc@ncit.edu.np')):
            user = CustomUser.objects.create_user(
                email=email, password="pw", user_type=user_type)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/accountants/").status_code, 403,
                "user_type %s should not reach the accountant list" % user_type)
            self.assertEqual(
                self.client.post("/api/v1/accountants/",
                                 self.ACCOUNTANT_PAYLOAD).status_code, 403)

    def test_the_accountant_dashboard_is_for_the_accountant_and_the_admin(self):
        for user in (self.make_accountant(), self.admin):
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/dashboard/accountant/").status_code,
                200, "user_type %s should reach the accounts dashboard"
                     % user.user_type)

    def test_no_other_role_sees_the_accounts_dashboard(self):
        for user_type, email in ((2, 'staff@ncit.edu.np'),
                                 (3, 'student@ncit.edu.np'),
                                 (4, 'lib@ncit.edu.np')):
            user = CustomUser.objects.create_user(
                email=email, password="pw", user_type=user_type)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/dashboard/accountant/").status_code,
                403, "user_type %s should not see the accounts dashboard"
                     % user_type)

    def test_the_dashboard_reads_zero_before_anything_is_billed(self):
        self.client.force_login(self.make_accountant())
        data = self.client.get("/api/v1/dashboard/accountant/").data
        self.assertEqual(data['invoices_total'], 0)
        self.assertEqual(data['outstanding_count'], 0)
        self.assertEqual(data['most_overdue'], [])
        self.assertEqual(data['recent_payments'], [])


class CourseCodeTests(TestCase):
    def test_codes_are_auto_assigned_from_one(self):
        self.assertEqual(Course.objects.create(name="IT").code, 1)
        self.assertEqual(Course.objects.create(name="Software").code, 2)
        # An explicit code is respected, and the auto-assign skips over it.
        Course.objects.create(name="Civil", code=3)
        self.assertEqual(Course.objects.create(name="Arch").code, 4)

    def test_each_course_owns_a_pair_of_slots(self):
        it = Course.objects.create(name="IT")              # code 1
        software = Course.objects.create(name="Software")  # code 2
        self.assertEqual(it.roll_slots, {'morning': '01', 'day': '02'})
        self.assertEqual(software.roll_slots, {'morning': '03', 'day': '04'})

    def test_the_college_can_pass_ten_courses(self):
        # The whole point of two digits: the eleventh course still works, where
        # a one-digit course code would have run out.
        for i in range(1, 12):
            Course.objects.create(name="course %d" % i)
        eleventh = Course.objects.get(name="course 11")
        self.assertEqual(eleventh.code, 11)
        self.assertEqual(eleventh.roll_slots, {'morning': '21', 'day': '22'})

    def test_running_out_of_slots_is_reported(self):
        for i in range(1, 50):
            Course.objects.create(name="course %d" % i)
        with self.assertRaisesMessage(ValueError, "no course code is free"):
            Course.objects.create(name="one too many")


class StudentNumberTests(TestCase):
    def setUp(self):
        self.s2022 = Session.objects.create(
            start_year=date(2022, 1, 1), end_year=date(2026, 1, 1))
        self.s2023 = Session.objects.create(
            start_year=date(2023, 1, 1), end_year=date(2027, 1, 1))
        self.it = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.civil = Course.objects.create(name="Civil", code=3, semesters=8)

    def test_registration_number_layout(self):
        student = make_student("Anil", "Rai", self.s2022, self.it)
        assign_student_numbers(student)
        self.assertEqual(student.registration_number, "2022-01-01-0001")

    def test_registration_serial_is_shared_across_courses_in_a_session(self):
        for first, last, course in [("Anil", "Rai", self.it),
                                    ("Bina", "Shah", self.civil)]:
            assign_student_numbers(
                make_student(first, last, self.s2022, course))
        self.assertEqual(
            sorted(Student.objects.values_list('registration_number', flat=True)),
            ["2022-01-01-0001", "2022-01-01-0002"])

    def test_batch_code_increments_per_session(self):
        a = make_student("Anil", "Rai", self.s2022, self.it)
        b = make_student("Bina", "Shah", self.s2023, self.it)
        assign_student_numbers(a)
        assign_student_numbers(b)
        # Same serial, different batch — only the last four are unique per batch.
        self.assertEqual(a.registration_number, "2022-01-01-0001")
        self.assertEqual(b.registration_number, "2023-01-02-0001")

    def test_roll_number_layout(self):
        student = make_student("Anil", "Rai", self.s2022, self.it)
        assign_student_numbers(student)
        self.assertEqual(student.roll_number, "220101")

    def test_roll_number_encodes_the_course(self):
        a = make_student("Anil", "Rai", self.s2022, self.it)
        b = make_student("Bina", "Shah", self.s2022, self.civil)
        assign_student_numbers(a)
        assign_student_numbers(b)
        self.assertEqual(a.roll_number, "220101")
        self.assertEqual(b.roll_number, "220501")

    def test_slot_separates_the_two_shifts(self):
        morning = make_student("Anil", "Rai", self.s2022, self.it)
        day = make_student("Bina", "Shah", self.s2022, self.it, shift="day")
        assign_student_numbers(morning)
        assign_student_numbers(day)
        # Same course and intake, so only the slot tells them apart — and each
        # shift counts from 01 rather than continuing the other's run.
        self.assertEqual(morning.roll_number, "220101")
        self.assertEqual(day.roll_number, "220201")

    def test_each_shift_sorts_independently(self):
        # Interleaved names: whoever sorts first WITHIN a shift gets 01, and a
        # name in the other shift never displaces them.
        for first, last, shift in [("Anil", "Adhikari", "day"),
                                   ("Bina", "Bhandari", "morning"),
                                   ("Chetan", "Chettri", "day"),
                                   ("Deepak", "Dahal", "morning")]:
            assign_student_numbers(
                make_student(first, last, self.s2022, self.it, shift=shift))
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Bhandari", "220101"), ("Dahal", "220102"),
             ("Adhikari", "220201"), ("Chettri", "220202")])

    def test_adding_to_one_shift_leaves_the_other_alone(self):
        for first, last, shift in [("Anil", "Adhikari", "morning"),
                                   ("Chetan", "Chettri", "morning"),
                                   ("Bikash", "Baral", "day")]:
            assign_student_numbers(
                make_student(first, last, self.s2022, self.it, shift=shift))
        # Aarav sorts first overall, but he is a day student — the morning run
        # must not shift for him.
        aarav = make_student("Aarav", "Aacharya", self.s2022, self.it, shift="day")
        assign_student_numbers(aarav)
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Adhikari", "220101"), ("Chettri", "220102"),
             ("Aacharya", "220201"), ("Baral", "220202")])

    def test_open_cohort_renumbers_to_stay_alphabetical(self):
        for first, last in [("Anil", "Adhikari"), ("Chetan", "Chettri")]:
            assign_student_numbers(make_student(first, last, self.s2022, self.it))
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Adhikari", "220101"), ("Chettri", "220102")])

        # Bina sorts between them, so Chetan has to move down.
        bina = make_student("Bina", "Bhandari", self.s2022, self.it)
        shifted = assign_student_numbers(bina)
        self.assertEqual(shifted, 1)
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Adhikari", "220101"), ("Bhandari", "220102"), ("Chettri", "220103")])

    def test_locked_cohort_appends_instead_of_renumbering(self):
        for first, last in [("Anil", "Adhikari"), ("Chetan", "Chettri")]:
            assign_student_numbers(make_student(first, last, self.s2022, self.it))
        lock_batches_for_course(self.it, [self.s2022.id])

        bina = make_student("Bina", "Bhandari", self.s2022, self.it)
        shifted = assign_student_numbers(bina)
        self.assertEqual(shifted, 0)
        # Bina lands at the end; nobody already on record moved.
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Adhikari", "220101"), ("Chettri", "220102"), ("Bhandari", "220103")])

    def test_cohort_past_semester_one_locks_itself(self):
        assign_student_numbers(
            make_student("Chetan", "Chettri", self.s2022, self.it, semester=3))
        bina = make_student("Bina", "Bhandari", self.s2022, self.it, semester=3)
        assign_student_numbers(bina)
        self.assertTrue(
            RollNumberBatch.objects.get(session=self.s2022, course=self.it).locked)
        self.assertEqual(bina.roll_number, "220102")

    def test_locking_one_cohort_leaves_the_others_open(self):
        assign_student_numbers(make_student("Anil", "Adhikari", self.s2022, self.it))
        lock_batches_for_course(self.it, [self.s2022.id])
        # Same course, different intake — still filling up, so still alphabetical.
        for first, last in [("Chetan", "Chettri"), ("Bina", "Bhandari")]:
            assign_student_numbers(make_student(first, last, self.s2023, self.it))
        self.assertEqual(
            rolls(self.s2023, self.it),
            [("Bhandari", "230101"), ("Chettri", "230102")])

    def test_deleting_from_an_open_cohort_closes_the_gap(self):
        for first, last in [("Anil", "Adhikari"), ("Bina", "Bhandari"),
                            ("Chetan", "Chettri")]:
            assign_student_numbers(make_student(first, last, self.s2022, self.it))
        Student.objects.get(admin__last_name="Bhandari").admin.delete()
        resequence_cohort(self.s2022, self.it)
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Adhikari", "220101"), ("Chettri", "220102")])

    def test_renaming_reorders_an_open_cohort(self):
        for first, last in [("Anil", "Adhikari"), ("Chetan", "Chettri")]:
            assign_student_numbers(make_student(first, last, self.s2022, self.it))
        chetan = Student.objects.get(admin__last_name="Chettri")
        chetan.admin.last_name = "Acharya"
        chetan.admin.save()
        resequence_cohort(self.s2022, self.it)
        self.assertEqual(
            rolls(self.s2022, self.it),
            [("Acharya", "220101"), ("Adhikari", "220102")])

    def test_no_numbers_without_a_session_or_course(self):
        student = make_student("Anil", "Rai", None, None)
        self.assertEqual(assign_student_numbers(student), 0)
        self.assertIsNone(student.registration_number)
        self.assertIsNone(student.roll_number)


class AdminApiTests(TestCase):
    """The identifiers as the admin actually meets them — over the API, with
    nothing for the three numbers posted in the request body."""

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="pw", user_type=1)
        self.client.force_login(self.admin)
        self.session = Session.objects.create(
            start_year=date(2022, 1, 1), end_year=date(2026, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)

    def add_staff(self, first, last):
        return self.client.post("/api/v1/staff/", {
            'first_name': first, 'last_name': last,
            'email': "%s@ncit.edu.np" % last.lower(), 'gender': 'M',
            'address_line1': 'Kathmandu', 'teaches_morning': True})

    def add_student(self, first, last, semester=1):
        return self.client.post("/api/v1/students/", {
            'first_name': first, 'last_name': last,
            'email': "%s@ncit.edu.np" % last.lower(), 'gender': 'M',
            'address_line1': 'Kathmandu', 'course': self.course.id,
            'session': self.session.id, 'shift': 'morning',
            'current_semester': semester, 'parent_full_name': 'Ram Rai',
            'parent_phone_number': '9800000000',
            'parent_relationship': 'Father'})

    def test_staff_id_is_issued_without_being_asked_for(self):
        response = self.add_staff("Sita", "Karki")
        self.assertEqual(response.status_code, 201, response.data)
        expected = "%02d0001" % (date.today().year % 100)
        self.assertEqual(response.data['staff_id'], expected)
        self.assertEqual(self.add_staff("Hari", "Thapa").data['staff_id'],
                         "%02d0002" % (date.today().year % 100))

    def test_student_numbers_are_issued_without_being_asked_for(self):
        response = self.add_student("Anil", "Adhikari")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['registration_number'], "2022-01-01-0001")
        self.assertEqual(response.data['roll_number'], "220101")

    def test_posted_identifiers_are_ignored(self):
        response = self.client.post("/api/v1/students/", {
            'first_name': 'Anil', 'last_name': 'Adhikari',
            'email': 'anil@ncit.edu.np', 'gender': 'M',
            'address_line1': 'Kathmandu', 'course': self.course.id,
            'session': self.session.id, 'shift': 'morning',
            'current_semester': 1, 'parent_full_name': 'Ram Rai',
            'parent_phone_number': '9800000000',
            'parent_relationship': 'Father',
            'registration_number': '9999-99-99-9999', 'roll_number': '999999'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['registration_number'], "2022-01-01-0001")
        self.assertEqual(response.data['roll_number'], "220101")

    def test_adding_out_of_order_renumbers_and_says_so(self):
        self.add_student("Anil", "Adhikari")
        self.add_student("Chetan", "Chettri")
        response = self.add_student("Bina", "Bhandari")
        self.assertEqual(response.data['roll_number'], "220102")
        self.assertIn("renumbered 1 other", response.data.get('detail', ''))
        self.assertEqual(
            rolls(self.session, self.course),
            [("Adhikari", "220101"), ("Bhandari", "220102"),
             ("Chettri", "220103")])

    def test_promotion_freezes_the_cohort(self):
        self.add_student("Anil", "Adhikari")
        self.add_student("Chetan", "Chettri")
        promote = self.client.post(
            "/api/v1/courses/%d/promote/" % self.course.id,
            {'from_semester': 1})
        self.assertEqual(promote.status_code, 200, promote.data)
        self.assertTrue(RollNumberBatch.objects.get(
            session=self.session, course=self.course).locked)

        # A late arrival who sorts first is appended rather than promoted to 01.
        response = self.add_student("Bina", "Bhandari", semester=2)
        self.assertEqual(response.data['roll_number'], "220103")
        self.assertNotIn("renumbered", response.data.get('detail', '') or '')

    def test_renaming_reorders_an_open_cohort_over_the_api(self):
        self.add_student("Anil", "Adhikari")
        self.add_student("Chetan", "Chettri")
        chetan = Student.objects.get(admin__last_name="Chettri")
        response = self.client.put(
            "/api/v1/students/%d/" % chetan.id,
            {'first_name': 'Chetan', 'last_name': 'Acharya',
             'email': 'chettri@ncit.edu.np', 'gender': 'M',
             'address_line1': 'Kathmandu', 'course': self.course.id,
             'session': self.session.id, 'shift': 'morning',
             'current_semester': 1, 'parent_full_name': 'Ram Rai',
             'parent_phone_number': '9800000000',
             'parent_relationship': 'Father'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['roll_number'], "220101")
        self.assertEqual(
            rolls(self.session, self.course),
            [("Acharya", "220101"), ("Adhikari", "220102")])

    def lock(self, semester=1, password="pw"):
        return self.client.post(
            "/api/v1/courses/%d/semesters/%d/roll-lock/"
            % (self.course.id, semester), {'password': password},
            content_type='application/json')

    def test_manual_lock_stops_renumbering(self):
        self.add_student("Anil", "Adhikari")
        self.add_student("Chetan", "Chettri")
        response = self.lock()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['roll_lock'], 'locked')

        # Bina sorts first but arrives after the lock, so she goes on the end.
        added = self.add_student("Bina", "Bhandari")
        self.assertEqual(added.data['roll_number'], "220103")
        self.assertEqual(
            rolls(self.session, self.course),
            [("Adhikari", "220101"), ("Chettri", "220102"),
             ("Bhandari", "220103")])

    def test_wrong_password_does_not_lock(self):
        self.add_student("Anil", "Adhikari")
        response = self.lock(password="not-my-password")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(RollNumberBatch.objects.filter(locked=True).exists())
        # Still open, so the batch keeps renumbering alphabetically.
        self.add_student("Aarav", "Aacharya")
        self.assertEqual(
            rolls(self.session, self.course),
            [("Aacharya", "220101"), ("Adhikari", "220102")])

    def test_missing_password_does_not_lock(self):
        self.add_student("Anil", "Adhikari")
        response = self.client.post(
            "/api/v1/courses/%d/semesters/1/roll-lock/" % self.course.id, {},
            content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(RollNumberBatch.objects.filter(locked=True).exists())

    def test_there_is_no_way_to_unlock(self):
        self.add_student("Anil", "Adhikari")
        self.lock()
        # The old unlock payload is simply ignored — the endpoint only locks.
        response = self.client.post(
            "/api/v1/courses/%d/semesters/1/roll-lock/" % self.course.id,
            {'password': 'pw', 'locked': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['roll_lock'], 'locked')
        self.assertTrue(RollNumberBatch.objects.get(
            session=self.session, course=self.course).locked)

    def test_locking_twice_is_reported_as_a_no_op(self):
        self.add_student("Anil", "Adhikari")
        self.lock()
        response = self.lock()
        self.assertEqual(response.status_code, 200)
        self.assertIn("already locked", response.data['detail'])

    def test_lock_state_is_reported_on_the_semester_listing(self):
        self.add_student("Anil", "Adhikari")
        listing = self.client.get(
            "/api/v1/students/manage/courses/%d/semesters/" % self.course.id)
        by_number = {s['number']: s for s in listing.data['semester_data']}
        self.assertEqual(by_number[1]['roll_lock'], 'open')
        # A semester with nobody in it has no intake to lock.
        self.assertIsNone(by_number[2]['roll_lock'])

        self.lock()
        listing = self.client.get(
            "/api/v1/students/manage/courses/%d/semesters/" % self.course.id)
        by_number = {s['number']: s for s in listing.data['semester_data']}
        self.assertEqual(by_number[1]['roll_lock'], 'locked')

    def test_locking_an_empty_semester_is_rejected(self):
        response = self.lock(semester=4)
        self.assertEqual(response.status_code, 400)
        self.assertIn("No students", response.data['detail'])

    def test_deleting_closes_the_gap_in_an_open_cohort(self):
        self.add_student("Anil", "Adhikari")
        self.add_student("Bina", "Bhandari")
        self.add_student("Chetan", "Chettri")
        bina = Student.objects.get(admin__last_name="Bhandari")
        self.assertEqual(
            self.client.delete("/api/v1/students/%d/" % bina.id).status_code, 204)
        self.assertEqual(
            rolls(self.session, self.course),
            [("Adhikari", "220101"), ("Chettri", "220102")])


class LibraryApiTests(TestCase):
    """The borrow loop end to end: a student asks, the librarian decides, the
    book goes out and comes back."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2022, 1, 1), end_year=date(2026, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.student = make_student("Anil", "Adhikari", self.session, self.course)
        self.other = make_student("Bina", "Bhandari", self.session, self.course)
        self.librarian_user = CustomUser.objects.create_user(
            email="lib@ncit.edu.np", password="pw", user_type=4,
            first_name="Rita", last_name="Gurung")
        self.book = Book.objects.create(
            name="Clean Code", author="Martin", isbn="9780132350884",
            category="Software", total_copies=1)

    # -- helpers ----------------------------------------------------------
    def as_student(self, student=None):
        self.client.force_login((student or self.student).admin)

    def as_librarian(self):
        self.client.force_login(self.librarian_user)

    def request_book(self, book=None):
        return self.client.post("/api/v1/library/requests/mine/",
                                {'book': (book or self.book).id})

    def act(self, request_id, action, **body):
        return self.client.post(
            "/api/v1/library/requests/%d/%s/" % (request_id, action), body)

    def available(self):
        return Book.objects.get(pk=self.book.pk).available_copies

    # -- the happy path ---------------------------------------------------
    def test_the_whole_loop(self):
        self.as_student()
        created = self.request_book()
        self.assertEqual(created.status_code, 201, created.data)
        req_id = created.data['id']
        self.assertEqual(created.data['status'], 'pending')
        # A pending request does not yet take the copy off the shelf.
        self.assertEqual(self.available(), 1)

        self.as_librarian()
        approved = self.act(req_id, 'approve')
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data['status'], 'approved')
        # Approving reserves it, before anybody has collected anything.
        self.assertEqual(self.available(), 0)

        issued = self.act(req_id, 'issue')
        self.assertEqual(issued.data['status'], 'issued')
        self.assertEqual(
            issued.data['due_date'],
            (date.today() + timedelta(days=LOAN_PERIOD_DAYS)).isoformat())

        returned = self.act(req_id, 'return')
        self.assertEqual(returned.data['status'], 'returned')
        self.assertEqual(returned.data['fine'], 0)
        self.assertEqual(self.available(), 1)

    def test_the_student_is_told_at_every_step(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        self.act(req_id, 'issue')
        messages = list(NotificationStudent.objects.filter(
            student=self.student).order_by('id').values_list('message', flat=True))
        self.assertEqual(len(messages), 2)
        self.assertIn("approved", messages[0])
        self.assertIn("return it by", messages[1])

    # -- what the student may not do --------------------------------------
    def test_the_same_book_cannot_be_requested_twice(self):
        self.as_student()
        self.assertEqual(self.request_book().status_code, 201)
        second = self.request_book()
        self.assertEqual(second.status_code, 400)
        self.assertIn("already have an open request", second.data['detail'])

    def test_a_returned_book_can_be_requested_again(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        self.act(req_id, 'issue')
        self.act(req_id, 'return')
        self.as_student()
        self.assertEqual(self.request_book().status_code, 201)

    def test_the_borrowing_limit_is_enforced(self):
        for i in range(MAX_OPEN_PER_STUDENT):
            Book.objects.create(name="Book %d" % i, author="A",
                                isbn="100%d" % i, category="C")
        self.as_student()
        for book in Book.objects.exclude(pk=self.book.pk):
            self.assertEqual(self.request_book(book).status_code, 201)
        refused = self.request_book()
        self.assertEqual(refused.status_code, 400)
        self.assertIn("is the limit", refused.data['detail'])

    def test_an_overdue_book_blocks_new_requests(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        self.act(req_id, 'issue')
        BookRequest.objects.filter(pk=req_id).update(
            due_date=date.today() - timedelta(days=3))

        other_book = Book.objects.create(
            name="Algorithms", author="Cormen", isbn="123", category="CS")
        self.as_student()
        refused = self.request_book(other_book)
        self.assertEqual(refused.status_code, 400)
        self.assertIn("overdue", refused.data['detail'])

    def test_only_a_pending_request_can_be_cancelled(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.assertEqual(self.act(req_id, 'cancel').status_code, 200)
        self.as_librarian()
        self.assertEqual(self.act(req_id, 'approve').status_code, 400)

    def test_a_student_cannot_cancel_another_students_request(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_student(self.other)
        self.assertEqual(self.act(req_id, 'cancel').status_code, 404)

    # -- what the librarian may not do ------------------------------------
    def test_the_last_copy_cannot_be_promised_twice(self):
        self.as_student()
        first = self.request_book().data['id']
        self.as_student(self.other)
        second = self.request_book().data['id']

        self.as_librarian()
        self.assertEqual(self.act(first, 'approve').status_code, 200)
        refused = self.act(second, 'approve')
        self.assertEqual(refused.status_code, 400)
        self.assertIn("Every copy", refused.data['detail'])

    def test_rejecting_needs_a_reason_and_frees_the_copy(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        self.assertEqual(self.available(), 0)

        self.assertEqual(self.act(req_id, 'reject').status_code, 400)
        rejected = self.act(req_id, 'reject', reason="Reserved for staff")
        self.assertEqual(rejected.data['status'], 'rejected')
        self.assertEqual(self.available(), 1)

    def test_a_book_cannot_be_handed_over_before_it_is_approved(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.assertEqual(self.act(req_id, 'issue').status_code, 400)

    def test_the_fine_is_charged_per_day_and_freezes_on_return(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        self.act(req_id, 'issue')
        BookRequest.objects.filter(pk=req_id).update(
            due_date=date.today() - timedelta(days=4))

        loans = self.client.get("/api/v1/library/loans/")
        self.assertEqual(loans.data[0]['days_overdue'], 4)
        self.assertEqual(loans.data[0]['fine'], 4 * FINE_PER_DAY)

        returned = self.act(req_id, 'return')
        self.assertEqual(returned.data['fine'], 4 * FINE_PER_DAY)

    # -- who may touch what -----------------------------------------------
    def test_a_student_cannot_approve_their_own_request(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.assertEqual(self.act(req_id, 'approve').status_code, 403)

    def test_a_teacher_cannot_run_the_library(self):
        teacher = CustomUser.objects.create_user(
            email="teacher@ncit.edu.np", password="pw", user_type=2)
        self.client.force_login(teacher)
        self.assertEqual(
            self.client.get("/api/v1/library/requests/").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/books/", {
            'name': 'X', 'author': 'Y', 'isbn': '1', 'category': 'Z',
            'total_copies': 1}).status_code, 403)

    def test_only_the_librarian_may_add_to_the_catalogue(self):
        self.as_librarian()
        response = self.client.post("/api/v1/books/", {
            'name': 'Operating Systems', 'author': 'Silberschatz',
            'isbn': '9781118063330', 'category': 'CS', 'total_copies': 4})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['available_copies'], 4)

    def test_the_catalogue_shows_a_student_their_own_state(self):
        self.as_student()
        self.request_book()
        listing = self.client.get("/api/v1/books/")
        row = next(b for b in listing.data if b['id'] == self.book.id)
        self.assertEqual(row['my_request']['status'], 'pending')
        # ...and nothing about anybody else's.
        self.as_student(self.other)
        listing = self.client.get("/api/v1/books/")
        row = next(b for b in listing.data if b['id'] == self.book.id)
        self.assertIsNone(row['my_request'])

    def test_a_book_on_loan_cannot_be_deleted(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        response = self.client.delete("/api/v1/books/%d/" % self.book.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("open request", response.data['detail'])

    def test_the_shelf_cannot_shrink_below_what_is_lent_out(self):
        self.as_student()
        req_id = self.request_book().data['id']
        self.as_librarian()
        self.act(req_id, 'approve')
        response = self.client.put(
            "/api/v1/books/%d/" % self.book.id,
            data={'name': self.book.name, 'author': self.book.author,
                  'isbn': self.book.isbn, 'category': self.book.category,
                  'total_copies': 0},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('total_copies', response.data)


class LibraryRenewalTests(TestCase):
    """Renewing a loan: one extension of a week, never two, and never on a
    book that is already late."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2022, 1, 1), end_year=date(2026, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.student = make_student("Anil", "Adhikari", self.session, self.course)
        self.librarian_user = CustomUser.objects.create_user(
            email="lib@ncit.edu.np", password="pw", user_type=4,
            first_name="Rita", last_name="Gurung")
        self.book = Book.objects.create(
            name="Clean Code", author="Martin", isbn="9780132350884",
            category="Software", total_copies=2)

    def a_loan(self):
        """A book issued to the student, ready to be renewed."""
        self.client.force_login(self.student.admin)
        req_id = self.client.post(
            "/api/v1/library/requests/mine/", {'book': self.book.id}).data['id']
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/approve/" % req_id)
        self.client.post("/api/v1/library/requests/%d/issue/" % req_id)
        return req_id

    def test_an_approved_renewal_adds_one_week(self):
        req_id = self.a_loan()
        original_due = BookRequest.objects.get(id=req_id).due_date

        self.client.force_login(self.student.admin)
        asked = self.client.post(
            "/api/v1/library/requests/%d/renew/" % req_id, {'reason': 'Mid-terms'})
        self.assertEqual(asked.status_code, 200, asked.data)
        self.assertEqual(asked.data['renewal_state'], 'requested')

        self.client.force_login(self.librarian_user)
        granted = self.client.post(
            "/api/v1/library/requests/%d/renew/approve/" % req_id)
        self.assertEqual(granted.status_code, 200, granted.data)

        loan = BookRequest.objects.get(id=req_id)
        self.assertEqual(loan.renewal_state, BookRequest.RENEWAL_GRANTED)
        self.assertEqual(
            loan.due_date, original_due + timedelta(days=RENEWAL_PERIOD_DAYS))
        # The pre-renewal deadline stays on the record.
        self.assertEqual(loan.due_date_before_renewal, original_due)

    def test_a_loan_cannot_be_renewed_twice(self):
        req_id = self.a_loan()
        self.client.force_login(self.student.admin)
        self.client.post("/api/v1/library/requests/%d/renew/" % req_id)
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/renew/approve/" % req_id)

        self.client.force_login(self.student.admin)
        again = self.client.post("/api/v1/library/requests/%d/renew/" % req_id)
        self.assertEqual(again.status_code, 400)
        self.assertIn("already been renewed once", again.data['detail'])
        self.assertFalse(BookRequest.objects.get(id=req_id).can_request_renewal)

    def test_a_declined_renewal_leaves_the_due_date_alone(self):
        req_id = self.a_loan()
        original_due = BookRequest.objects.get(id=req_id).due_date
        self.client.force_login(self.student.admin)
        self.client.post("/api/v1/library/requests/%d/renew/" % req_id)

        self.client.force_login(self.librarian_user)
        bare = self.client.post("/api/v1/library/requests/%d/renew/reject/" % req_id)
        self.assertEqual(bare.status_code, 400, "a reason should be required")

        declined = self.client.post(
            "/api/v1/library/requests/%d/renew/reject/" % req_id,
            {'reason': 'Someone else is waiting for it'})
        self.assertEqual(declined.status_code, 200, declined.data)
        loan = BookRequest.objects.get(id=req_id)
        self.assertEqual(loan.renewal_state, BookRequest.RENEWAL_DECLINED)
        self.assertEqual(loan.due_date, original_due)

    def test_an_overdue_book_cannot_be_renewed(self):
        req_id = self.a_loan()
        BookRequest.objects.filter(id=req_id).update(
            due_date=date.today() - timedelta(days=2))

        self.client.force_login(self.student.admin)
        refused = self.client.post("/api/v1/library/requests/%d/renew/" % req_id)
        self.assertEqual(refused.status_code, 400)
        self.assertIn("overdue", refused.data['detail'])


class LibraryFineTests(TestCase):
    """Fines: Rs 10 a day, settled in cash at the desk, and the receipt is a
    permanent record neither portal can alter."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2022, 1, 1), end_year=date(2026, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.student = make_student("Anil", "Adhikari", self.session, self.course)
        self.librarian_user = CustomUser.objects.create_user(
            email="lib@ncit.edu.np", password="pw", user_type=4,
            first_name="Rita", last_name="Gurung")
        self.book = Book.objects.create(
            name="Clean Code", author="Martin", isbn="9780132350884",
            category="Software", total_copies=2)

    def a_late_return(self, days_late=4):
        """A returned loan carrying a fine, waiting to be settled."""
        self.client.force_login(self.student.admin)
        req_id = self.client.post(
            "/api/v1/library/requests/mine/", {'book': self.book.id}).data['id']
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/approve/" % req_id)
        self.client.post("/api/v1/library/requests/%d/issue/" % req_id)
        BookRequest.objects.filter(id=req_id).update(
            due_date=date.today() - timedelta(days=days_late))
        self.client.post("/api/v1/library/requests/%d/return/" % req_id)
        return req_id

    def test_the_fine_is_ten_rupees_a_day(self):
        self.assertEqual(FINE_PER_DAY, 10)
        req_id = self.a_late_return(days_late=4)
        self.assertEqual(BookRequest.objects.get(id=req_id).fine, 40)

    def test_a_fine_can_only_be_settled_once_the_book_is_back(self):
        self.client.force_login(self.student.admin)
        req_id = self.client.post(
            "/api/v1/library/requests/mine/", {'book': self.book.id}).data['id']
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/approve/" % req_id)
        self.client.post("/api/v1/library/requests/%d/issue/" % req_id)
        BookRequest.objects.filter(id=req_id).update(
            due_date=date.today() - timedelta(days=3))

        early = self.client.post(
            "/api/v1/library/requests/%d/fine/collect/" % req_id)
        self.assertEqual(early.status_code, 400)
        self.assertIn("comes back", early.data['detail'])

    def test_collecting_cash_writes_a_receipt_both_sides_can_see(self):
        req_id = self.a_late_return(days_late=4)
        self.client.force_login(self.librarian_user)
        receipt = self.client.post(
            "/api/v1/library/requests/%d/fine/collect/" % req_id,
            {'note': 'Cash at desk'})
        self.assertEqual(receipt.status_code, 201, receipt.data)
        self.assertEqual(receipt.data['amount'], 40)
        self.assertEqual(receipt.data['days_late'], 4)
        # Who took the money is snapshotted, not just linked.
        self.assertEqual(receipt.data['collected_by'], "Rita Gurung")

        desk = self.client.get("/api/v1/library/fines/")
        self.assertEqual(desk.data['total_collected'], 40)
        self.assertEqual(len(desk.data['records']), 1)

        self.client.force_login(self.student.admin)
        mine = self.client.get("/api/v1/library/fines/mine/")
        self.assertEqual(len(mine.data), 1)
        self.assertEqual(mine.data[0]['receipt_no'], receipt.data['receipt_no'])

    def test_the_same_fine_cannot_be_charged_twice(self):
        req_id = self.a_late_return()
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/fine/collect/" % req_id)
        again = self.client.post(
            "/api/v1/library/requests/%d/fine/collect/" % req_id)
        self.assertEqual(again.status_code, 400)
        self.assertEqual(LibraryFine.objects.count(), 1)

    def test_a_receipt_can_never_be_edited_or_deleted(self):
        req_id = self.a_late_return()
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/fine/collect/" % req_id)
        record = LibraryFine.objects.get()

        record.amount = 1
        with self.assertRaises(ValueError):
            record.save()
        with self.assertRaises(ValueError):
            record.delete()

        record.refresh_from_db()
        self.assertEqual(record.amount, 40)
        self.assertEqual(LibraryFine.objects.count(), 1)

    def test_a_waiver_is_recorded_with_its_reason(self):
        req_id = self.a_late_return(days_late=2)
        self.client.force_login(self.librarian_user)
        bare = self.client.post("/api/v1/library/requests/%d/fine/waive/" % req_id)
        self.assertEqual(bare.status_code, 400, "a waiver should need a reason")

        waived = self.client.post(
            "/api/v1/library/requests/%d/fine/waive/" % req_id,
            {'note': 'Student was in hospital'})
        self.assertEqual(waived.status_code, 201, waived.data)
        self.assertEqual(waived.data['kind'], LibraryFine.WAIVED)

        desk = self.client.get("/api/v1/library/fines/")
        self.assertEqual(desk.data['total_collected'], 0)
        self.assertEqual(desk.data['total_waived'], 20)

    def test_unsettled_list_empties_once_paid(self):
        req_id = self.a_late_return()
        self.client.force_login(self.librarian_user)
        self.assertEqual(
            len(self.client.get("/api/v1/library/fines/unsettled/").data), 1)
        self.client.post("/api/v1/library/requests/%d/fine/collect/" % req_id)
        self.assertEqual(
            len(self.client.get("/api/v1/library/fines/unsettled/").data), 0)


class LibraryReminderTests(TestCase):
    """The due-soon nudge: once per loan, three days out, and safe to re-run."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2022, 1, 1), end_year=date(2026, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.student = make_student("Anil", "Adhikari", self.session, self.course)
        self.librarian_user = CustomUser.objects.create_user(
            email="lib@ncit.edu.np", password="pw", user_type=4,
            first_name="Rita", last_name="Gurung")
        self.book = Book.objects.create(
            name="Clean Code", author="Martin", isbn="9780132350884",
            category="Software", total_copies=2)

    def a_loan(self):
        self.client.force_login(self.student.admin)
        req_id = self.client.post(
            "/api/v1/library/requests/mine/", {'book': self.book.id}).data['id']
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/approve/" % req_id)
        self.client.post("/api/v1/library/requests/%d/issue/" % req_id)
        return BookRequest.objects.get(id=req_id)

    def test_a_reminder_goes_out_three_days_before_the_due_date(self):
        loan = self.a_loan()
        NotificationStudent.objects.all().delete()

        three_days_before = loan.due_date - timedelta(days=DUE_SOON_REMINDER_DAYS)
        self.assertEqual(send_due_soon_reminders(today=three_days_before)['sent'], 1)

        message = NotificationStudent.objects.get(student=self.student).message
        self.assertIn(self.book.name, message)
        self.assertIn("renewal", message)

    def test_nobody_is_reminded_twice(self):
        loan = self.a_loan()
        NotificationStudent.objects.all().delete()
        three_days_before = loan.due_date - timedelta(days=DUE_SOON_REMINDER_DAYS)

        send_due_soon_reminders(today=three_days_before)
        self.assertEqual(send_due_soon_reminders(today=three_days_before)['sent'], 0)
        self.assertEqual(NotificationStudent.objects.count(), 1)

    def test_no_reminder_on_any_other_day(self):
        loan = self.a_loan()
        for offset in (1, 2, 5, 10):
            self.assertEqual(
                send_due_soon_reminders(
                    today=loan.due_date - timedelta(days=offset))['sent'], 0)

    def test_a_renewal_earns_a_fresh_reminder(self):
        loan = self.a_loan()
        first_due = loan.due_date
        send_due_soon_reminders(
            today=first_due - timedelta(days=DUE_SOON_REMINDER_DAYS))

        self.client.force_login(self.student.admin)
        self.client.post("/api/v1/library/requests/%d/renew/" % loan.id)
        self.client.force_login(self.librarian_user)
        self.client.post("/api/v1/library/requests/%d/renew/approve/" % loan.id)

        loan.refresh_from_db()
        # The new deadline gets its own nudge rather than inheriting the
        # "already reminded" flag from the old one.
        self.assertEqual(
            send_due_soon_reminders(
                today=loan.due_date - timedelta(days=DUE_SOON_REMINDER_DAYS))['sent'],
            1)

    def test_the_librarian_can_fire_the_sweep_by_hand(self):
        loan = self.a_loan()
        BookRequest.objects.filter(id=loan.id).update(
            due_date=date.today() + timedelta(days=DUE_SOON_REMINDER_DAYS))
        self.client.force_login(self.librarian_user)
        response = self.client.post("/api/v1/library/reminders/send/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sent'], 1)


# --------------------------------------------------------------------- Fees

class FeeBillingTests(TestCase):
    """The invoice run, and the rule the whole thing is built around: running
    it twice must not bill anybody twice."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.tuition = FeeHead.objects.create(name="Tuition")
        self.exam = FeeHead.objects.create(name="Exam")
        self.structure = FeeStructure.objects.create(
            course=self.course, session=self.session, semester=1,
            due_days=30, late_fine_per_day=Decimal('50.00'))
        # A paisa amount on purpose: the totals below prove the arithmetic
        # stays exact rather than drifting through float.
        FeeStructureItem.objects.create(
            structure=self.structure, head=self.tuition,
            amount=Decimal('47500.00'))
        FeeStructureItem.objects.create(
            structure=self.structure, head=self.exam, amount=Decimal('2750.50'))
        self.anil = make_student("Anil", "Adhikari", self.session, self.course)
        self.bina = make_student("Bina", "Bhandari", self.session, self.course)

    def run_it(self, semester=1):
        return generate_invoices(self.course, self.session, semester)

    def test_one_invoice_per_student_with_the_structures_lines(self):
        result = self.run_it()
        self.assertEqual(len(result['created']), 2)
        self.assertEqual(result['skipped'], 0)
        invoice = FeeInvoice.objects.get(student=self.anil)
        self.assertEqual(invoice.gross, Decimal('50250.50'))
        self.assertEqual(invoice.balance, Decimal('50250.50'))
        self.assertEqual(
            sorted(line.head_name for line in invoice.lines.all()),
            ["Exam", "Tuition"])
        self.assertEqual(invoice.due_date, date.today() + timedelta(days=30))

    def test_running_it_again_bills_nobody_twice(self):
        self.run_it()
        again = self.run_it()
        self.assertEqual(len(again['created']), 0)
        self.assertEqual(again['skipped'], 2)
        self.assertEqual(FeeInvoice.objects.count(), 2)

    def test_a_new_student_is_picked_up_by_a_re_run(self):
        self.run_it()
        chetan = make_student("Chetan", "Chettri", self.session, self.course)
        again = self.run_it()
        self.assertEqual(len(again['created']), 1)
        self.assertEqual(again['skipped'], 2)
        self.assertTrue(FeeInvoice.objects.filter(student=chetan).exists())

    def test_passed_out_students_are_not_billed(self):
        self.bina.passed_out = True
        self.bina.save()
        result = self.run_it()
        self.assertEqual(len(result['created']), 1)
        self.assertFalse(FeeInvoice.objects.filter(student=self.bina).exists())

    def test_a_class_with_no_structure_is_refused_with_a_reason(self):
        with self.assertRaisesMessage(NothingToBill, "No fee structure exists"):
            self.run_it(semester=4)

    def test_a_structure_with_no_heads_is_refused(self):
        self.structure.items.all().delete()
        with self.assertRaisesMessage(NothingToBill, "no fee heads"):
            self.run_it()

    def test_issuing_a_bill_notifies_the_student(self):
        self.run_it()
        note = NotificationStudent.objects.get(student=self.anil)
        self.assertIn("Semester 1 bill", note.message)
        self.assertIn("50250.50", note.message)

    def test_invoice_numbers_are_sequential_and_unique(self):
        self.run_it()
        numbers = sorted(FeeInvoice.objects.values_list('number', flat=True))
        year = date.today().year
        self.assertEqual(numbers, ["INV-%d-000001" % year,
                                   "INV-%d-000002" % year])

    def test_editing_the_structure_does_not_rewrite_issued_bills(self):
        """The reason FeeInvoiceLine snapshots instead of pointing at the
        structure: a mid-session correction must not change what a student
        was already told to pay."""
        self.run_it()
        item = self.structure.items.get(head=self.tuition)
        item.amount = Decimal('99999.00')
        item.save()
        self.assertEqual(
            FeeInvoice.objects.get(student=self.anil).gross,
            Decimal('50250.50'))


class FeeAdjustmentTests(TestCase):
    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        structure = FeeStructure.objects.create(
            course=self.course, session=self.session, semester=1)
        FeeStructureItem.objects.create(
            structure=structure, head=FeeHead.objects.create(name="Tuition"),
            amount=Decimal('50000.00'))
        self.student = make_student("Anil", "Adhikari", self.session,
                                    self.course)
        generate_invoices(self.course, self.session, 1)
        self.invoice = FeeInvoice.objects.get(student=self.student)

    def test_the_kind_decides_the_sign(self):
        """The form asks for a plain positive number; a scholarship must not
        depend on the accountant remembering to type a minus."""
        self.assertEqual(signed_amount(FeeAdjustment.SCHOLARSHIP, 5000),
                         Decimal('-5000'))
        self.assertEqual(signed_amount(FeeAdjustment.WAIVER, -5000),
                         Decimal('-5000'))
        self.assertEqual(signed_amount(FeeAdjustment.LATE_FINE, 150),
                         Decimal('150'))
        # A correction is the one kind that has to go either way.
        self.assertEqual(signed_amount(FeeAdjustment.CORRECTION, -75),
                         Decimal('-75'))

    def test_a_scholarship_reduces_the_balance(self):
        add_adjustment(self.invoice, FeeAdjustment.SCHOLARSHIP, 9500, "Merit")
        invoice = FeeInvoice.objects.get(pk=self.invoice.pk)
        self.assertEqual(invoice.payable, Decimal('40500.00'))
        self.assertEqual(invoice.balance, Decimal('40500.00'))

    def test_adjustments_are_append_only(self):
        adjustment = add_adjustment(
            self.invoice, FeeAdjustment.LATE_FINE, 150, "3 days")
        with self.assertRaises(ValueError):
            adjustment.save()
        with self.assertRaises(ValueError):
            adjustment.delete()


class FeePromotionBillingTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="pw", user_type=1)
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.student = make_student("Anil", "Adhikari", self.session,
                                    self.course)

    def structure_for(self, semester):
        structure = FeeStructure.objects.create(
            course=self.course, session=self.session, semester=semester)
        FeeStructureItem.objects.create(
            structure=structure,
            head=FeeHead.objects.get_or_create(name="Tuition")[0],
            amount=Decimal('50000.00'))
        return structure

    def promote(self):
        self.client.force_login(self.admin)
        return self.client.post(
            "/api/v1/courses/%d/promote/" % self.course.id,
            {'from_semester': 1})

    def test_promotion_bills_the_new_semester(self):
        self.structure_for(2)
        response = self.promote()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("raised 1 fee invoice", response.data['detail'])
        self.assertTrue(FeeInvoice.objects.filter(
            student=self.student, semester=2).exists())

    def test_promotion_still_works_when_no_structure_exists(self):
        """An academic promotion must not fail on the accounts office's
        paperwork."""
        response = self.promote()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("promoted 1 student", response.data['detail'])
        self.assertNotIn("invoice", response.data['detail'])
        self.assertEqual(FeeInvoice.objects.count(), 0)
        self.student.refresh_from_db()
        self.assertEqual(self.student.current_semester, 2)

    def test_a_cohort_missed_at_promotion_is_picked_up_later(self):
        """bill_active_cohorts sweeps rather than diffing, so writing the
        structure after the promotion still bills the cohort."""
        self.promote()
        self.assertEqual(FeeInvoice.objects.count(), 0)
        self.structure_for(2)
        self.assertEqual(bill_active_cohorts(self.course), 1)


class FeeApiTests(TestCase):
    """Who may write the college's fee structures, and who may only look."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        self.head = FeeHead.objects.create(name="Tuition")
        self.admin = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="pw", user_type=1)
        self.accountant_user = CustomUser.objects.create_user(
            email="accounts@ncit.edu.np", password="pw", user_type=5,
            first_name="Sabina", last_name="Shrestha")
        self.student = make_student("Anil", "Adhikari", self.session,
                                    self.course)

    def structure_payload(self, **overrides):
        payload = {
            'course': self.course.id,
            'session': self.session.id,
            'semester': 1,
            'due_days': 30,
            'items': [{'head': self.head.id, 'amount': '47500.50'}],
        }
        payload.update(overrides)
        return payload

    def post_structure(self):
        return self.client.post("/api/v1/fees/structures/",
                                self.structure_payload(),
                                content_type="application/json")

    def run_invoices(self):
        return self.client.post("/api/v1/fees/invoice-run/",
                                {'course': self.course.id,
                                 'session': self.session.id, 'semester': 1})

    def test_the_accountant_writes_a_structure(self):
        self.client.force_login(self.accountant_user)
        response = self.post_structure()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['total'], Decimal('47500.50'))
        self.assertEqual(len(response.data['items']), 1)

    def test_the_admin_may_read_structures_but_not_write_them(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get("/api/v1/fees/structures/").status_code, 200)
        response = self.post_structure()
        self.assertEqual(response.status_code, 403, response.data)
        self.assertIn("accounts office", response.data['detail'])

    def test_no_other_role_reaches_the_fee_structures(self):
        for user_type, email in ((2, 'staff@ncit.edu.np'),
                                 (3, 'stu@ncit.edu.np'),
                                 (4, 'lib@ncit.edu.np')):
            user = CustomUser.objects.create_user(
                email=email, password="pw", user_type=user_type)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/fees/structures/").status_code, 403,
                "user_type %s should not see fee structures" % user_type)

    def test_a_second_structure_for_the_same_class_is_refused(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        response = self.post_structure()
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.data['detail'])

    def test_a_negative_amount_is_refused_with_advice(self):
        self.client.force_login(self.accountant_user)
        response = self.client.post(
            "/api/v1/fees/structures/",
            self.structure_payload(
                items=[{'head': self.head.id, 'amount': '-500'}]),
            content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("scholarship or discount", str(response.data['items']))

    def test_the_invoice_run_is_idempotent_through_the_api(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        first = self.run_invoices()
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data['created'], 1)
        second = self.run_invoices()
        self.assertEqual(second.data['created'], 0)
        self.assertEqual(second.data['skipped'], 1)
        self.assertEqual(FeeInvoice.objects.count(), 1)

    def test_the_preview_says_who_would_be_billed(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        response = self.client.get(
            "/api/v1/fees/invoice-run/preview/",
            {'course': self.course.id, 'session': self.session.id,
             'semester': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['to_bill']), 1)
        self.assertEqual(response.data['already_billed'], [])
        self.assertIsNotNone(response.data['structure'])

    def test_the_preview_warns_when_there_is_no_structure(self):
        self.client.force_login(self.accountant_user)
        response = self.client.get(
            "/api/v1/fees/invoice-run/preview/",
            {'course': self.course.id, 'session': self.session.id,
             'semester': 3})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['structure'])

    def test_an_adjustment_needs_a_reason(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        self.run_invoices()
        invoice = FeeInvoice.objects.get()
        response = self.client.post(
            "/api/v1/fees/invoices/%d/adjust/" % invoice.id,
            {'kind': FeeAdjustment.SCHOLARSHIP, 'amount': '5000'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('reason', response.data)

    def test_an_adjustment_records_who_made_it(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        self.run_invoices()
        invoice = FeeInvoice.objects.get()
        response = self.client.post(
            "/api/v1/fees/invoices/%d/adjust/" % invoice.id,
            {'kind': FeeAdjustment.SCHOLARSHIP, 'amount': '5000',
             'reason': 'Merit scholarship'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['payable'], Decimal('42500.50'))
        adjustment = response.data['adjustments'][0]
        self.assertEqual(adjustment['amount'], Decimal('-5000.00'))
        self.assertEqual(adjustment['created_by_name'], "Sabina Shrestha")

    def test_cancelling_needs_a_reason_and_clears_the_debt(self):
        self.client.force_login(self.accountant_user)
        self.post_structure()
        self.run_invoices()
        invoice = FeeInvoice.objects.get()
        self.assertEqual(
            self.client.post(
                "/api/v1/fees/invoices/%d/cancel/" % invoice.id).status_code,
            400)
        response = self.client.post(
            "/api/v1/fees/invoices/%d/cancel/" % invoice.id,
            {'reason': 'Raised against the wrong cohort'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], FeeInvoice.CANCELLED)
        # ...and a cancelled bill is no longer money the college is owed.
        self.assertFalse(
            FeeInvoice.objects.outstanding().filter(pk=invoice.pk).exists())


class StudentFeeViewTests(TestCase):
    """What a student can see of their own fees — and, more to the point,
    what they can see of somebody else's."""

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        structure = FeeStructure.objects.create(
            course=self.course, session=self.session, semester=1, due_days=30)
        FeeStructureItem.objects.create(
            structure=structure, head=FeeHead.objects.create(name="Tuition"),
            amount=Decimal('50000.00'))
        self.anil = make_student("Anil", "Adhikari", self.session, self.course)
        self.bina = make_student("Bina", "Bhandari", self.session, self.course)
        generate_invoices(self.course, self.session, 1)
        self.anil_invoice = FeeInvoice.objects.get(student=self.anil)
        self.bina_invoice = FeeInvoice.objects.get(student=self.bina)

    def login_as(self, student):
        self.client.force_login(student.admin)

    def test_a_student_sees_their_own_position(self):
        self.login_as(self.anil)
        response = self.client.get("/api/v1/fees/mine/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['outstanding_total'],
                         Decimal('50000.00'))
        self.assertEqual(len(response.data['invoices']), 1)
        self.assertEqual(response.data['invoices'][0]['number'],
                         self.anil_invoice.number)

    def test_a_student_cannot_open_another_students_bill(self):
        """Scoped by owner rather than checked after lookup, so somebody
        else's invoice is a 404 — there is no reason to confirm it exists."""
        self.login_as(self.anil)
        response = self.client.get(
            "/api/v1/fees/mine/%d/" % self.bina_invoice.id)
        self.assertEqual(response.status_code, 404)

    def test_the_students_own_bill_opens(self):
        self.login_as(self.anil)
        response = self.client.get(
            "/api/v1/fees/mine/%d/" % self.anil_invoice.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['lines']), 1)
        self.assertEqual(response.data['lines'][0]['head_name'], "Tuition")

    def test_the_students_view_never_leaks_the_office_fields(self):
        """fee_invoice_dict's for_office half carries other people's contact
        details; the student's own view has no use for any of it."""
        self.login_as(self.anil)
        data = self.client.get("/api/v1/fees/mine/").data
        self.assertNotIn('student_email', data['invoices'][0])
        self.assertNotIn('student_name', data['invoices'][0])

    def test_a_scholarship_shows_on_the_students_own_bill(self):
        add_adjustment(self.anil_invoice, FeeAdjustment.SCHOLARSHIP, 9500,
                       "Merit")
        self.login_as(self.anil)
        data = self.client.get(
            "/api/v1/fees/mine/%d/" % self.anil_invoice.id).data
        self.assertEqual(data['payable'], Decimal('40500.00'))
        self.assertEqual(data['adjustments'][0]['reason'], "Merit")

    def test_a_cancelled_bill_stays_visible_but_owes_nothing(self):
        """A student who was told they owed something deserves to see it was
        withdrawn, rather than watching it vanish."""
        self.anil_invoice.cancelled_at = timezone.now()
        self.anil_invoice.cancel_reason = "Billed in error"
        self.anil_invoice.save()
        self.login_as(self.anil)
        data = self.client.get("/api/v1/fees/mine/").data
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['status'], FeeInvoice.CANCELLED)
        self.assertEqual(data['outstanding_total'], Decimal('0.00'))

    def test_no_other_role_reaches_the_student_fee_endpoints(self):
        for user_type, email in ((1, 'hod@ncit.edu.np'),
                                 (2, 'staff@ncit.edu.np'),
                                 (4, 'lib@ncit.edu.np'),
                                 (5, 'acc@ncit.edu.np')):
            user = CustomUser.objects.create_user(
                email=email, password="pw", user_type=user_type)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/fees/mine/").status_code, 403,
                "user_type %s should not reach /fees/mine/" % user_type)

    def test_the_dashboard_warns_without_blocking(self):
        """The college's decision: fees are a warning, never a gate. The
        number shows up, and results stay reachable."""
        self.login_as(self.anil)
        dashboard = self.client.get("/api/v1/dashboard/student/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['fees_outstanding'],
                         Decimal('50000.00'))
        # Overdue by nothing yet — the bill has 30 days on it.
        self.assertEqual(dashboard.data['fees_overdue'], Decimal('0.00'))
        # ...and nothing is gated behind paying it.
        self.assertEqual(
            self.client.get("/api/v1/results/mine/").status_code, 200)


class FeeCounterTests(TestCase):
    """Taking money at the counter.

    The rules here are the ones that stop the ledger disagreeing with the cash
    box: what may be recorded, by whom, against which bill, and what can never
    be revised afterwards.
    """

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        structure = FeeStructure.objects.create(
            course=self.course, session=self.session, semester=1, due_days=30)
        FeeStructureItem.objects.create(
            structure=structure, head=FeeHead.objects.create(name="Tuition"),
            amount=Decimal('50000.00'))
        self.anil = make_student("Anil", "Adhikari", self.session, self.course)
        self.bina = make_student("Bina", "Bhandari", self.session, self.course)
        generate_invoices(self.course, self.session, 1)
        self.invoice = FeeInvoice.objects.get(student=self.anil)
        self.bina_invoice = FeeInvoice.objects.get(student=self.bina)

        self.admin = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="pw", user_type=1)
        self.accountant_user = CustomUser.objects.create_user(
            email="accounts@ncit.edu.np", password="pw", user_type=5,
            first_name="Sabina", last_name="Shrestha")

    def collect(self, invoice=None, **data):
        payload = {'amount': '50000.00', 'mode': FeePayment.CASH}
        payload.update(data)
        return self.client.post(
            "/api/v1/fees/invoices/%d/collect/" % (invoice or self.invoice).id,
            payload)

    def as_accountant(self):
        self.client.force_login(self.accountant_user)

    def test_cash_over_the_counter_settles_the_bill(self):
        self.as_accountant()
        response = self.collect()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['payment']['amount'],
                         Decimal('50000.00'))
        # Who took the money is snapshotted, not just referenced.
        self.assertEqual(response.data['payment']['collected_by_name'],
                         "Sabina Shrestha")
        self.assertEqual(response.data['invoice']['balance'], Decimal('0.00'))
        self.assertEqual(response.data['invoice']['status'], FeeInvoice.PAID)

    def test_a_part_payment_leaves_the_rest_owing(self):
        self.as_accountant()
        response = self.collect(amount='20000')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['invoice']['paid'], Decimal('20000.00'))
        self.assertEqual(response.data['invoice']['balance'],
                         Decimal('30000.00'))
        self.assertEqual(response.data['invoice']['status'],
                         FeeInvoice.PARTIAL)

    def test_a_scholarship_lowers_what_the_counter_may_take(self):
        """The balance the counter is held to is the derived one — lines plus
        signed adjustments minus payments — not the invoice's face value."""
        add_adjustment(self.invoice, FeeAdjustment.SCHOLARSHIP, 10000, "Merit")
        self.as_accountant()
        too_much = self.collect(amount='45000')
        self.assertEqual(too_much.status_code, 400)
        self.assertIn("40000.00", too_much.data['amount'][0])
        self.assertEqual(self.collect(amount='40000').status_code, 201)

    def test_more_than_the_balance_is_refused(self):
        """Nearly always a typo, and the college has no concept of a student
        account carrying a surplus."""
        self.as_accountant()
        response = self.collect(amount='50000.01')
        self.assertEqual(response.status_code, 400)
        self.assertIn("still owed", response.data['amount'][0])
        self.assertFalse(FeePayment.objects.exists())

    def test_a_settled_bill_takes_no_more_money(self):
        self.as_accountant()
        self.collect()
        again = self.collect(amount='100')
        self.assertEqual(again.status_code, 400)
        self.assertIn("already settled", again.data['detail'])
        self.assertEqual(FeePayment.objects.count(), 1)

    def test_nothing_can_be_taken_against_a_withdrawn_bill(self):
        self.invoice.cancelled_at = timezone.now()
        self.invoice.cancel_reason = "Billed in error"
        self.invoice.save()
        self.as_accountant()
        response = self.collect(amount='100')
        self.assertEqual(response.status_code, 400)
        self.assertIn("withdrawn", response.data['detail'])

    def test_zero_and_nonsense_amounts_are_refused(self):
        self.as_accountant()
        for amount in ('0', '-500', '', 'lots'):
            response = self.collect(amount=amount)
            self.assertEqual(response.status_code, 400,
                             "%r should not be collectable" % amount)
        self.assertFalse(FeePayment.objects.exists())

    def test_the_counter_cannot_type_in_an_online_payment(self):
        """An online payment exists only because a gateway confirmed it.
        Letting the desk enter one by hand would put an unverifiable row in
        the ledger beside the verified ones."""
        self.as_accountant()
        response = self.collect(mode=FeePayment.ONLINE)
        self.assertEqual(response.status_code, 400)
        self.assertIn("gateway", response.data['mode'][0])
        self.assertFalse(FeePayment.objects.exists())

    def test_a_cheque_or_deposit_needs_its_number(self):
        self.as_accountant()
        for mode in (FeePayment.CHEQUE, FeePayment.BANK):
            bare = self.collect(mode=mode)
            self.assertEqual(bare.status_code, 400,
                             "%s should need a reference" % mode)
            self.assertIn('reference', bare.data)
        response = self.collect(mode=FeePayment.CHEQUE, reference="0092841")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['payment']['reference'], "0092841")

    def test_a_receipt_cannot_be_dated_in_the_future(self):
        self.as_accountant()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = self.collect(received_on=tomorrow)
        self.assertEqual(response.status_code, 400)
        self.assertIn('received_on', response.data)

    def test_the_student_is_told_what_landed_and_what_is_left(self):
        self.as_accountant()
        self.collect(amount='20000')
        message = NotificationStudent.objects.filter(
            student=self.anil).latest('id').message
        self.assertIn("20000.00", message)
        self.assertIn("30000.00", message)
        self.collect(amount='30000')
        self.assertIn(
            "Nothing further is owed",
            NotificationStudent.objects.filter(
                student=self.anil).latest('id').message)

    def test_a_receipt_can_never_be_edited_or_deleted(self):
        self.as_accountant()
        self.collect()
        payment = FeePayment.objects.get()

        payment.amount = Decimal('1.00')
        with self.assertRaises(ValueError):
            payment.save()
        with self.assertRaises(ValueError):
            payment.delete()

        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('50000.00'))

    def test_receipt_numbers_are_sequential_and_unique(self):
        self.as_accountant()
        self.collect(amount='10000')
        self.collect(invoice=self.bina_invoice, amount='10000')
        numbers = list(
            FeePayment.objects.order_by('id').values_list('receipt_no',
                                                          flat=True))
        self.assertEqual(len(set(numbers)), 2)
        self.assertTrue(all(n.startswith("FEE-") for n in numbers), numbers)

    def test_a_settled_bill_drops_off_the_counters_list(self):
        self.as_accountant()
        listed = self.client.get("/api/v1/fees/collectable/")
        self.assertEqual(len(listed.data), 2)
        self.collect()
        remaining = self.client.get("/api/v1/fees/collectable/")
        self.assertEqual([i['id'] for i in remaining.data],
                         [self.bina_invoice.id])

    def test_the_counter_finds_a_bill_by_name_roll_or_invoice(self):
        """Whichever of the three the person at the window happens to say."""
        assign_student_numbers(self.anil)
        self.as_accountant()

        by_name = self.client.get("/api/v1/fees/collectable/", {'q': "Bina"})
        self.assertEqual([i['id'] for i in by_name.data],
                         [self.bina_invoice.id])
        by_roll = self.client.get("/api/v1/fees/collectable/",
                                  {'q': self.anil.roll_number})
        self.assertEqual([i['id'] for i in by_roll.data], [self.invoice.id])
        by_number = self.client.get("/api/v1/fees/collectable/",
                                    {'q': self.invoice.number})
        self.assertEqual([i['id'] for i in by_number.data], [self.invoice.id])

    def test_the_cash_book_totals_what_was_taken(self):
        self.as_accountant()
        self.collect(amount='20000')
        self.collect(invoice=self.bina_invoice, amount='5000',
                     mode=FeePayment.BANK, reference="DEP-77")
        book = self.client.get("/api/v1/fees/payments/")
        self.assertEqual(book.status_code, 200)
        self.assertEqual(book.data['total'], Decimal('25000.00'))
        self.assertEqual(len(book.data['payments']), 2)
        # ...and it narrows by how the money arrived.
        bank = self.client.get("/api/v1/fees/payments/",
                               {'mode': FeePayment.BANK})
        self.assertEqual(bank.data['total'], Decimal('5000.00'))

    def test_the_admin_reads_the_cash_book_but_takes_no_money(self):
        """The whole reason the accountant is its own role: oversight sees
        every rupee and moves none of it."""
        self.as_accountant()
        self.collect(amount='20000')
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get("/api/v1/fees/payments/").status_code, 200)
        self.assertEqual(
            self.client.get("/api/v1/fees/collectable/").status_code, 200)
        refused = self.collect(amount='100')
        self.assertEqual(refused.status_code, 403, refused.data)
        self.assertEqual(FeePayment.objects.count(), 1)

    def test_no_other_role_reaches_the_counter(self):
        for user_type, email in ((2, 'staff@ncit.edu.np'),
                                 (4, 'lib@ncit.edu.np')):
            user = CustomUser.objects.create_user(
                email=email, password="pw", user_type=user_type)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/fees/collectable/").status_code, 403,
                "user_type %s should not see the counter" % user_type)
            self.assertEqual(self.collect(amount='100').status_code, 403)
        self.client.force_login(self.anil.admin)
        self.assertEqual(self.collect(amount='100').status_code, 403)

    def test_a_student_sees_their_own_receipt_and_no_other(self):
        """Scoped by owner, so somebody else's receipt is a 404 rather than a
        refusal that confirms it exists."""
        self.as_accountant()
        mine = self.collect(amount='20000').data['payment']
        theirs = self.collect(invoice=self.bina_invoice,
                              amount='20000').data['payment']

        self.client.force_login(self.anil.admin)
        own = self.client.get("/api/v1/fees/payments/%d/receipt/" % mine['id'])
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data['receipt_no'], mine['receipt_no'])
        # The student's copy carries no office fields...
        self.assertNotIn('student_email', own.data)
        # ...and their neighbour's receipt does not exist as far as they know.
        self.assertEqual(
            self.client.get(
                "/api/v1/fees/payments/%d/receipt/" % theirs['id']).status_code,
            404)

    def test_a_student_can_list_every_receipt_they_hold(self):
        """Across all their bills — the list you want when what you have is a
        receipt number and no idea which semester it belonged to."""
        self.as_accountant()
        first = self.collect(amount='20000').data['payment']
        second = self.collect(amount='30000').data['payment']
        # ...and a classmate's receipt, which must not appear below.
        self.collect(invoice=self.bina_invoice, amount='5000')

        self.client.force_login(self.anil.admin)
        response = self.client.get("/api/v1/fees/mine/receipts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(r['receipt_no'] for r in response.data),
            sorted([first['receipt_no'], second['receipt_no']]))
        # Every row can be opened as a printable receipt without a second
        # lookup for which bill it belongs to.
        self.assertEqual(response.data[0]['invoice_id'], self.invoice.id)

    def test_a_receipt_shows_up_on_the_students_own_bill(self):
        self.as_accountant()
        receipt = self.collect(amount='20000').data['payment']
        self.client.force_login(self.anil.admin)
        bill = self.client.get("/api/v1/fees/mine/%d/" % self.invoice.id)
        self.assertEqual(bill.data['balance'], Decimal('30000.00'))
        self.assertEqual([p['receipt_no'] for p in bill.data['payments']],
                         [receipt['receipt_no']])


class BootstrapAdminTests(TestCase):
    """`bootstrap_admin`, which build.sh runs on every Render deploy.

    Render's free plan has no shell, so this command is the only way to
    create or repair the administrator of a deployed instance. Every
    assertion here corresponds to a way the deployment was actually locked
    out during setup.
    """

    EMAIL = 'hod@ncit.edu.np'
    PASSWORD = 'not-a-common-password-42'
    ENV = {'DJANGO_SUPERUSER_EMAIL': EMAIL,
           'DJANGO_SUPERUSER_PASSWORD': PASSWORD}

    def bootstrap(self, **overrides):
        env = dict(self.ENV)
        env.update(overrides)
        with patch.dict(os.environ, env):
            call_command('bootstrap_admin', verbosity=0)

    def login(self, email=None, password=None):
        return self.client.post("/api/v1/auth/login/", {
            'email': email or self.EMAIL,
            'password': password or self.PASSWORD})

    def test_it_creates_an_admin_who_can_log_straight_in(self):
        self.bootstrap()

        user = CustomUser.objects.get(email=self.EMAIL)
        self.assertTrue(user.is_superuser, "needs /django-admin/ access")
        self.assertEqual(str(user.user_type), '1', "the app's own admin role")
        self.assertTrue(Admin.objects.filter(admin=user).exists())

        response = self.login()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['user_type'], '1')

    def test_the_admin_does_not_have_to_verify_an_email_first(self):
        """The lockout this command exists for: an unverified admin is sent
        to a setup screen whose email an unconfigured deployment writes to
        its own logs."""
        self.bootstrap()
        response = self.login()
        self.assertTrue(response.data['email_verified'])
        self.assertEqual(response.data['pending_email'], '')

    def test_it_repairs_an_account_that_is_mid_email_change(self):
        """Exactly the state a half-finished verification leaves behind."""
        self.bootstrap()
        stuck = CustomUser.objects.get(email=self.EMAIL)
        stuck.email_verified = False
        stuck.pending_email = 'somewhere.else@ncit.edu.np'
        stuck.save()

        self.bootstrap()

        stuck.refresh_from_db()
        self.assertTrue(stuck.email_verified)
        self.assertEqual(stuck.pending_email, '')

    def test_running_it_again_resets_the_password_and_adds_nobody(self):
        """Redeploying is how a forgotten password gets reset, and it must
        never quietly accumulate a second administrator."""
        self.bootstrap()
        self.bootstrap(DJANGO_SUPERUSER_PASSWORD='a-different-password-99')

        self.assertEqual(
            CustomUser.objects.filter(email=self.EMAIL).count(), 1)
        self.assertEqual(self.login().status_code, 400, "old password")
        self.assertEqual(
            self.login(password='a-different-password-99').status_code, 200)

    def test_it_promotes_and_verifies_an_existing_account(self):
        """If the email already belongs to somebody, the environment wins —
        that is what makes the command a repair and not just a create."""
        existing = CustomUser.objects.create_user(
            email=self.EMAIL, password='whatever', user_type=3,
            first_name="Anil", last_name="Adhikari")
        existing.is_active = False
        existing.save()

        self.bootstrap()

        existing.refresh_from_db()
        self.assertEqual(str(existing.user_type), '1')
        self.assertTrue(existing.is_active)
        self.assertTrue(existing.email_verified)
        self.assertTrue(Admin.objects.filter(admin=existing).exists())
        self.assertEqual(self.login().status_code, 200)

    def test_it_does_nothing_at_all_without_the_variables(self):
        """Local development and any already-configured deploy run this with
        nothing set, and it must not fail the build."""
        with patch.dict(os.environ, {}, clear=True):
            call_command('bootstrap_admin', verbosity=0)
        self.assertFalse(CustomUser.objects.exists())


class LoginCaptchaTests(TestCase):
    """Whether the login page's reCAPTCHA is enforced.

    This used to switch itself on whenever DEBUG was off — which is to say,
    the moment the app was deployed — against a key pair hardcoded here and
    registered to domains no deployment of it would own. The result was an
    app that locked out everyone including its own administrator, and said
    only "Invalid Captcha".
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="not-a-common-password-42",
            user_type=1, first_name="Hari", last_name="Oli")

    def login(self, **extra):
        payload = {'email': "hod@ncit.edu.np",
                   'password': "not-a-common-password-42"}
        payload.update(extra)
        return self.client.post("/api/v1/auth/login/", payload)

    def test_login_works_when_no_captcha_is_configured(self):
        """The default. No RECAPTCHA_SECRET, no check — anything else would
        make a fresh deployment unusable before it was even configured."""
        response = self.login()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email'], "hod@ncit.edu.np")

    @patch('main_app.api.auth.requests.post')
    def test_a_configured_captcha_is_enforced(self, post):
        """And once a secret IS set, a login without a valid token is
        refused — the check is off by absence, never by accident."""
        post.return_value.text = '{"success": false}'
        with patch('main_app.api.auth.CAPTCHA_SECRET', 'a-real-secret'):
            response = self.login(captcha="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Captcha", response.data['detail'])
        self.assertTrue(post.called, "the token should have been verified")

    @patch('main_app.api.auth.requests.post')
    def test_a_valid_captcha_token_lets_the_login_through(self, post):
        post.return_value.text = '{"success": true}'
        with patch('main_app.api.auth.CAPTCHA_SECRET', 'a-real-secret'):
            response = self.login(captcha="a-token-google-would-accept")
        self.assertEqual(response.status_code, 200, response.data)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='erp-slip-tests-'))
class DepositSlipTests(TestCase):
    """A student's claim to have paid into the bank, and what the office does
    with it.

    The rule the whole flow turns on: uploading a slip pays nothing. Money
    only exists in the ledger once somebody at the accounts office has agreed
    it is in the bank.
    """

    @classmethod
    def tearDownClass(cls):
        # The uploads are real files under a temporary MEDIA_ROOT; take them
        # with us rather than leaving slips behind on somebody's disk.
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.session = Session.objects.create(
            start_year=date(2026, 1, 1), end_year=date(2030, 1, 1))
        self.course = Course.objects.create(name="BE-IT", code=1, semesters=8)
        structure = FeeStructure.objects.create(
            course=self.course, session=self.session, semester=1, due_days=30)
        FeeStructureItem.objects.create(
            structure=structure, head=FeeHead.objects.create(name="Tuition"),
            amount=Decimal('50000.00'))
        self.anil = make_student("Anil", "Adhikari", self.session, self.course)
        self.bina = make_student("Bina", "Bhandari", self.session, self.course)
        generate_invoices(self.course, self.session, 1)
        self.invoice = FeeInvoice.objects.get(student=self.anil)
        self.bina_invoice = FeeInvoice.objects.get(student=self.bina)

        self.admin = CustomUser.objects.create_user(
            email="hod@ncit.edu.np", password="pw", user_type=1)
        self.accountant_user = CustomUser.objects.create_user(
            email="accounts@ncit.edu.np", password="pw", user_type=5,
            first_name="Sabina", last_name="Shrestha")

    # -- helpers ---------------------------------------------------------

    def slip_file(self, name="slip.jpg", content_type="image/jpeg",
                  size=1024):
        return SimpleUploadedFile(name, b"x" * size, content_type=content_type)

    def submit(self, invoice=None, student=None, **overrides):
        """Upload a slip as a student. Multipart, since a file is involved."""
        self.client.force_login((student or self.anil).admin)
        payload = {
            'amount': '50000.00',
            'deposited_on': date.today().isoformat(),
            'bank_name': "Nabil Bank",
            'reference': "DEP-1001",
            'image': self.slip_file(),
        }
        payload.update(overrides)
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.client.post(
            "/api/v1/fees/mine/%d/slips/" % (invoice or self.invoice).id,
            payload)

    def as_accountant(self):
        self.client.force_login(self.accountant_user)

    def a_pending_slip(self, **overrides):
        response = self.submit(**overrides)
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    # -- the student's side ----------------------------------------------

    def test_uploading_a_slip_pays_nothing_yet(self):
        """The point of the whole flow: a claim is not a receipt."""
        slip = self.a_pending_slip()
        self.assertEqual(slip['status'], DepositSlip.PENDING)
        self.assertFalse(FeePayment.objects.exists())
        self.assertEqual(
            FeeInvoice.objects.get(pk=self.invoice.pk).balance,
            Decimal('50000.00'))
        # Nothing is announced to the student either — the only notification
        # they have is the one that told them the bill was raised.
        self.assertEqual(
            [n.message for n in NotificationStudent.objects.filter(
                student=self.anil) if 'deposit' in n.message.lower()], [])

    def test_a_student_sees_their_own_slips_and_no_others(self):
        mine = self.a_pending_slip()
        self.submit(invoice=self.bina_invoice, student=self.bina)

        self.client.force_login(self.anil.admin)
        response = self.client.get("/api/v1/fees/mine/slips/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s['id'] for s in response.data], [mine['id']])

    def test_a_slip_cannot_be_hung_on_somebody_elses_bill(self):
        response = self.submit(invoice=self.bina_invoice)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(DepositSlip.objects.exists())

    def test_more_than_the_balance_is_refused(self):
        response = self.submit(amount='50000.01')
        self.assertEqual(response.status_code, 400)
        self.assertIn("still owed", response.data['amount'][0])

    def test_a_settled_or_withdrawn_bill_takes_no_slip(self):
        self.invoice.cancelled_at = timezone.now()
        self.invoice.cancel_reason = "Billed in error"
        self.invoice.save()
        withdrawn = self.submit()
        self.assertEqual(withdrawn.status_code, 400)
        self.assertIn("withdrawn", withdrawn.data['detail'])

    def test_the_details_the_office_needs_are_all_required(self):
        for field, value in (('amount', ''), ('amount', '0'),
                             ('bank_name', ''), ('reference', ''),
                             ('deposited_on', '')):
            response = self.submit(**{field: value})
            self.assertEqual(response.status_code, 400,
                             "%s=%r should be refused" % (field, value))
            self.assertIn(field, response.data)

    def test_a_deposit_cannot_be_dated_in_the_future(self):
        response = self.submit(
            deposited_on=(date.today() + timedelta(days=1)).isoformat())
        self.assertEqual(response.status_code, 400)
        self.assertIn('deposited_on', response.data)

    def test_only_a_photo_or_a_pdf_is_accepted(self):
        """The one place in the system where a file arrives from outside the
        staffroom, so what may be uploaded is deliberately narrow."""
        missing = self.submit(image=None)
        self.assertEqual(missing.status_code, 400)
        self.assertIn('image', missing.data)

        script = self.submit(image=self.slip_file(
            "slip.svg", content_type="image/svg+xml"))
        self.assertEqual(script.status_code, 400)

        # A permitted content type does not make a forbidden extension safe.
        disguised = self.submit(image=self.slip_file(
            "slip.exe", content_type="image/jpeg"))
        self.assertEqual(disguised.status_code, 400)

        oversized = self.submit(image=self.slip_file(size=6 * 1024 * 1024))
        self.assertEqual(oversized.status_code, 400)
        self.assertIn("5 MB", oversized.data['image'][0])

        self.assertEqual(
            self.submit(image=self.slip_file("slip.pdf",
                                             content_type="application/pdf")
                        ).status_code, 201)

    def test_the_same_slip_cannot_be_submitted_twice(self):
        """Almost always the upload button pressed twice."""
        self.a_pending_slip()
        again = self.submit()
        self.assertEqual(again.status_code, 400)
        self.assertIn("already submitted", again.data['detail'])
        self.assertEqual(DepositSlip.objects.count(), 1)

    def test_a_pending_slip_can_be_withdrawn(self):
        slip = self.a_pending_slip()
        response = self.client.delete("/api/v1/fees/mine/slips/%d/"
                                      % slip['id'])
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DepositSlip.objects.exists())
        # ...and the reference is free again afterwards.
        self.assertEqual(self.submit().status_code, 201)

    def test_a_reviewed_slip_can_no_longer_be_withdrawn(self):
        slip = self.a_pending_slip()
        self.as_accountant()
        self.client.post("/api/v1/fees/slips/%d/verify/" % slip['id'])
        self.client.force_login(self.anil.admin)
        response = self.client.delete("/api/v1/fees/mine/slips/%d/"
                                      % slip['id'])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DepositSlip.objects.count(), 1)

    # -- the office's side -----------------------------------------------

    def test_verifying_turns_the_claim_into_a_receipt(self):
        slip = self.a_pending_slip(amount='20000')
        self.as_accountant()
        response = self.client.post("/api/v1/fees/slips/%d/verify/"
                                    % slip['id'])
        self.assertEqual(response.status_code, 201, response.data)

        payment = response.data['payment']
        self.assertEqual(payment['amount'], Decimal('20000.00'))
        # The receipt records how the money actually arrived, and carries the
        # slip's own reference so it can be matched to the statement.
        self.assertEqual(payment['mode'], FeePayment.BANK)
        self.assertEqual(payment['reference'], "DEP-1001")
        self.assertEqual(payment['collected_by_name'], "Sabina Shrestha")
        # Dated when the bank took it, not when the office got round to it.
        self.assertEqual(payment['received_on'],
                         slip['deposited_on'])

        self.assertEqual(response.data['slip']['status'], DepositSlip.VERIFIED)
        self.assertEqual(response.data['slip']['receipt_no'],
                         payment['receipt_no'])
        self.assertEqual(
            FeeInvoice.objects.get(pk=self.invoice.pk).balance,
            Decimal('30000.00'))

    def test_the_student_is_told_their_deposit_was_verified(self):
        slip = self.a_pending_slip(amount='20000')
        self.as_accountant()
        self.client.post("/api/v1/fees/slips/%d/verify/" % slip['id'])
        message = NotificationStudent.objects.filter(
            student=self.anil).latest('id').message
        self.assertIn("verified", message)
        self.assertIn("20000.00", message)
        self.assertIn("30000.00", message)

    def test_the_bank_wins_when_the_amounts_disagree(self):
        """The desk is reading the statement; the student is reading a
        photograph."""
        slip = self.a_pending_slip(amount='20000')
        self.as_accountant()
        response = self.client.post(
            "/api/v1/fees/slips/%d/verify/" % slip['id'], {'amount': '18000'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['payment']['amount'],
                         Decimal('18000.00'))
        self.assertEqual(
            FeeInvoice.objects.get(pk=self.invoice.pk).balance,
            Decimal('32000.00'))

    def test_a_slip_is_credited_once_however_often_verify_is_pressed(self):
        slip = self.a_pending_slip(amount='20000')
        self.as_accountant()
        self.client.post("/api/v1/fees/slips/%d/verify/" % slip['id'])
        again = self.client.post("/api/v1/fees/slips/%d/verify/" % slip['id'])
        self.assertEqual(again.status_code, 400)
        self.assertEqual(FeePayment.objects.count(), 1)

    def test_a_slip_for_a_bill_paid_meanwhile_is_left_for_a_human(self):
        """Not auto-rejected: the money may well be in the bank, and what to
        do about it is a judgement for the office."""
        slip = self.a_pending_slip()
        self.as_accountant()
        self.client.post("/api/v1/fees/invoices/%d/collect/" % self.invoice.id,
                         {'amount': '50000', 'mode': FeePayment.CASH})
        response = self.client.post("/api/v1/fees/slips/%d/verify/"
                                    % slip['id'])
        self.assertEqual(response.status_code, 400)
        self.assertIn("already settled", response.data['detail'])
        self.assertEqual(
            DepositSlip.objects.get(pk=slip['id']).status, DepositSlip.PENDING)

    def test_rejecting_needs_a_reason_the_student_can_act_on(self):
        slip = self.a_pending_slip()
        self.as_accountant()
        bare = self.client.post("/api/v1/fees/slips/%d/reject/" % slip['id'])
        self.assertEqual(bare.status_code, 400)
        self.assertIn('reason', bare.data)

        response = self.client.post(
            "/api/v1/fees/slips/%d/reject/" % slip['id'],
            {'reason': "That reference isn't on the bank statement."})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], DepositSlip.REJECTED)
        self.assertEqual(response.data['reviewed_by_name'], "Sabina Shrestha")
        self.assertFalse(FeePayment.objects.exists())
        self.assertIn(
            "bank statement",
            NotificationStudent.objects.filter(
                student=self.anil).latest('id').message)

    def test_a_rejected_slip_can_be_corrected_and_resubmitted(self):
        """The uniqueness rule is scoped to live rows for exactly this."""
        slip = self.a_pending_slip()
        self.as_accountant()
        self.client.post("/api/v1/fees/slips/%d/reject/" % slip['id'],
                         {'reason': "The photograph is unreadable."})
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(DepositSlip.objects.count(), 2)

    def test_the_queue_holds_what_the_office_still_owes_an_answer(self):
        pending = self.a_pending_slip()
        other = self.submit(invoice=self.bina_invoice, student=self.bina,
                            reference="DEP-2002")
        self.as_accountant()
        self.client.post("/api/v1/fees/slips/%d/reject/" % other.data['id'],
                         {'reason': "Not on the statement."})

        queue = self.client.get("/api/v1/fees/slips/")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual([s['id'] for s in queue.data['slips']],
                         [pending['id']])
        self.assertEqual(queue.data['pending_count'], 1)
        # The desk can see what the bill owes without opening it.
        self.assertEqual(queue.data['slips'][0]['invoice_balance'],
                         Decimal('50000.00'))
        # ...and the history is still reachable for a student who asks.
        everything = self.client.get("/api/v1/fees/slips/", {'status': 'all'})
        self.assertEqual(len(everything.data['slips']), 2)

    def test_the_admin_reads_the_queue_but_verifies_nothing(self):
        slip = self.a_pending_slip()
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get("/api/v1/fees/slips/").status_code, 200)
        for action in ('verify', 'reject'):
            response = self.client.post(
                "/api/v1/fees/slips/%d/%s/" % (slip['id'], action),
                {'reason': 'no'})
            self.assertEqual(response.status_code, 403,
                             "the admin should not %s a slip" % action)
        self.assertFalse(FeePayment.objects.exists())
        self.assertEqual(
            DepositSlip.objects.get(pk=slip['id']).status, DepositSlip.PENDING)

    def test_the_office_dashboard_counts_what_is_waiting(self):
        """A slip nobody looks at is a student who has paid and is still
        being chased, so the count belongs on the landing page."""
        self.as_accountant()
        self.assertEqual(
            self.client.get("/api/v1/dashboard/accountant/").data[
                'slips_pending'], 0)
        slip = self.a_pending_slip()
        self.as_accountant()
        self.assertEqual(
            self.client.get("/api/v1/dashboard/accountant/").data[
                'slips_pending'], 1)
        self.client.post("/api/v1/fees/slips/%d/verify/" % slip['id'])
        self.assertEqual(
            self.client.get("/api/v1/dashboard/accountant/").data[
                'slips_pending'], 0)

    def test_no_other_role_reaches_the_slip_queue(self):
        for user_type, email in ((2, 'staff@ncit.edu.np'),
                                 (4, 'lib@ncit.edu.np')):
            user = CustomUser.objects.create_user(
                email=email, password="pw", user_type=user_type)
            self.client.force_login(user)
            self.assertEqual(
                self.client.get("/api/v1/fees/slips/").status_code, 403,
                "user_type %s should not see the slip queue" % user_type)
        self.client.force_login(self.anil.admin)
        self.assertEqual(
            self.client.get("/api/v1/fees/slips/").status_code, 403)
