from datetime import date

from django.test import TestCase

from .idgen import (
    assign_student_numbers, lock_batches_for_course, next_staff_id,
    resequence_cohort)
from .models import Course, CustomUser, RollNumberBatch, Session, Staff, Student


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


class StaffIdTests(TestCase):
    def test_serial_runs_per_joining_year(self):
        self.assertEqual(next_staff_id(2025), "250001")
        Staff.objects.create(
            admin=CustomUser.objects.create_user(
                email="a@ncit.edu.np", user_type=1),
            staff_id="250001")
        self.assertEqual(next_staff_id(2025), "250002")
        # A new year restarts the serial but keeps IDs distinct via the prefix.
        self.assertEqual(next_staff_id(2026), "260001")

    def test_numbers_are_not_reused_after_a_deletion(self):
        user = CustomUser.objects.create_user(email="b@ncit.edu.np", user_type=2)
        user.staff.staff_id = next_staff_id(2025)
        user.staff.save()
        user.delete()
        self.assertEqual(Staff.objects.count(), 0)
        # 250001 belonged to someone; the next hire must not inherit it.
        self.assertEqual(next_staff_id(2025), "250002")


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
