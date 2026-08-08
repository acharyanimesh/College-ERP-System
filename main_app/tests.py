from datetime import date, timedelta

from django.test import TestCase

from .api.library import MAX_OPEN_PER_STUDENT
from .idgen import (
    assign_student_numbers, lock_batches_for_course, next_employee_id,
    resequence_cohort)
from .library_reminders import send_due_soon_reminders
from .models import (DUE_SOON_REMINDER_DAYS, FINE_PER_DAY, LOAN_PERIOD_DAYS,
                     RENEWAL_PERIOD_DAYS, Book, BookRequest, Course,
                     CustomUser, Librarian, LibraryFine, NotificationStudent,
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

    def test_staff_and_librarians_share_one_counter(self):
        """An employee ID identifies a person, not a person-within-a-role, so
        the librarian must not be handed the teacher's number."""
        staff_user = CustomUser.objects.create_user(
            email="teacher@ncit.edu.np", user_type=2)
        staff_user.staff.staff_id = next_employee_id(2025)
        staff_user.staff.save()

        lib_user = CustomUser.objects.create_user(
            email="librarian@ncit.edu.np", user_type=4)
        lib_user.librarian.librarian_id = next_employee_id(2025)
        lib_user.librarian.save()

        self.assertEqual(staff_user.staff.staff_id, "250001")
        self.assertEqual(lib_user.librarian.librarian_id, "250002")
        self.assertEqual(next_employee_id(2025), "250003")


class LibrarianRoleTests(TestCase):
    def test_creating_a_type_4_user_creates_the_profile(self):
        user = CustomUser.objects.create_user(
            email="lib@ncit.edu.np", user_type=4, first_name="Rita",
            last_name="Gurung")
        self.assertEqual(Librarian.objects.count(), 1)
        self.assertEqual(user.librarian.admin_id, user.id)

    def test_the_other_roles_get_no_librarian_profile(self):
        for user_type in (1, 2, 3):
            CustomUser.objects.create_user(
                email="u%d@ncit.edu.np" % user_type, user_type=user_type)
        self.assertEqual(Librarian.objects.count(), 0)


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
