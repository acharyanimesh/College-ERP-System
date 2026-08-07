from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.core.validators import (
    MaxValueValidator, MinValueValidator, RegexValidator)
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractUser
from datetime import datetime,timedelta


# Every course runs in both a Morning and a Day shift. A student belongs to one
# shift; attendance is recorded per shift by the assigned teacher.
SHIFT_CHOICES = (("morning", "Morning Shift"), ("day", "Day Shift"))

# Digits 3-4 of a roll number are a slot: one two-digit number per
# (course, shift) pair, allocated in course order — course 1 takes 01 morning
# and 02 day, course 2 takes 03 and 04, and so on. Spending both digits on the
# pair rather than one on the course and one on the shift is what lets the
# college pass ten courses without the scheme running out of room.
SHIFT_SLOT_OFFSET = {"morning": 0, "day": 1}
# 99 slots, two per course.
MAX_COURSE_CODE = 49


def roll_slot(course_code, shift):
    """The two-digit slot for a (course, shift), or None if either is unusable."""
    offset = SHIFT_SLOT_OFFSET.get(shift)
    if not course_code or offset is None:
        return None
    return "%02d" % ((course_code - 1) * 2 + 1 + offset)

# Registration numbers read YYYY-01-BB-NNNN — intake year, a constant
# institution code, the session's college-wide batch code, then a running
# number unique within that batch. Built by main_app.idgen.
REGISTRATION_NUMBER_RE = r'^\d{4}-\d{2}-\d{2}-\d{4}$'
REGISTRATION_NUMBER_HELP = (
    'Registration number must be 12 digits formatted as YYYY-XX-XX-XXXX')


class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = CustomUser(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        assert extra_fields["is_staff"]
        assert extra_fields["is_superuser"]
        return self._create_user(email, password, **extra_fields)


class Session(models.Model):
    start_year = models.DateField()
    end_year = models.DateField()
    # Third group of a student's registration number (YYYY-01-BB-NNNN). Counts
    # intakes college-wide: the first session ever created is 01, the next 02,
    # and so on. Assigned once on creation and never reshuffled afterwards —
    # backfilling a session with an earlier start_year must not rewrite the
    # registration numbers already issued under the existing ones.
    batch_code = models.PositiveSmallIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return "From " + str(self.start_year) + " to " + str(self.end_year)

    def save(self, *args, **kwargs):
        if self.batch_code is None:
            highest = Session.objects.exclude(pk=self.pk).aggregate(
                models.Max('batch_code'))['batch_code__max']
            self.batch_code = (highest or 0) + 1
        super().save(*args, **kwargs)


class CustomUser(AbstractUser):
    USER_TYPE = ((1, "HOD"), (2, "Staff"), (3, "Student"))
    GENDER = [("M", "Male"), ("F", "Female")]
    
    
    username = None  # Removed username, using email instead
    email = models.EmailField(unique=True)
    user_type = models.CharField(default=1, choices=USER_TYPE, max_length=1)
    middle_name = models.CharField(max_length=150, blank=True, default="")
    gender = models.CharField(max_length=1, choices=GENDER)
    profile_pic = models.ImageField()
    address = models.TextField(blank=True, default="")
    address_line1 = models.CharField(max_length=255, blank=True, default="")
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    province = models.CharField(max_length=100, blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    fcm_token = models.TextField(default="")  # For firebase notifications
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Staff/Student: flips to True together with is_active, the moment they
    # follow their account-creation email and set a password. Admin/HOD:
    # is_active is already True from creation (they need to be able to log
    # in immediately with a bootstrap password), so this is the ONLY signal
    # gating their separate first-login "confirm your institutional email"
    # flow — see api/auth.py's request/confirm_admin_email_verification.
    email_verified = models.BooleanField(default=False)
    # A new email address entered (via first-login setup or the profile
    # page) but not yet confirmed via the emailed link. Kept separate from
    # `email` so a failed or abandoned change never leaves the account
    # unable to log back in under its original address.
    pending_email = models.EmailField(blank=True, default="")
    # Staff/Student only: an admin must approve a `pending_email` change
    # (submitted from the profile page) before the verification link is
    # emailed to it — see api/auth.py's request/approve/reject_email_change.
    # Admin/HOD's own pending_email changes skip this gate entirely.
    pending_email_approved = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return  self.first_name + " " + self.last_name


class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)



class Course(models.Model):
    name = models.CharField(max_length=120)
    # Short form (e.g. "BE-IT") shown in tables/lists across the app; falls back
    # to the full name when not set.
    abbreviation = models.CharField(max_length=30, blank=True, default="")
    # This course's position in the roll-number slot table: course 1 owns
    # slots 01 (morning) and 02 (day), course 2 owns 03 and 04, and so on — so
    # a 2022 BE-IT morning student reads 22-01-NN. Auto-assigned on creation
    # but editable; changing it does NOT rewrite roll numbers already issued.
    code = models.PositiveSmallIntegerField(
        null=True, blank=True, unique=True, verbose_name='Course Code',
        validators=[MinValueValidator(1), MaxValueValidator(MAX_COURSE_CODE)],
        help_text="Position in the roll-number slot table (1-%d)." % MAX_COURSE_CODE)
    semesters = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            used = set(Course.objects.exclude(pk=self.pk).exclude(
                code__isnull=True).values_list('code', flat=True))
            for candidate in range(1, MAX_COURSE_CODE + 1):
                if candidate not in used:
                    self.code = candidate
                    break
            else:
                raise ValueError(
                    "All %d roll-number slots are in use — no course code is "
                    "free." % MAX_COURSE_CODE)
        super().save(*args, **kwargs)

    @property
    def roll_slots(self):
        """{'morning': '01', 'day': '02'} — this course's roll-number slots."""
        return {shift: roll_slot(self.code, shift)
                for shift in SHIFT_SLOT_OFFSET}

    @property
    def short_name(self):
        """Abbreviation if one is set, otherwise the full name."""
        return self.abbreviation or self.name

    @property
    def name_with_abbr(self):
        """Full name plus abbreviation in brackets, e.g. 'Bachelor ... (BE-IT)'."""
        return "%s (%s)" % (self.name, self.abbreviation) if self.abbreviation else self.name

class Book(models.Model):
    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.PositiveIntegerField()
    category = models.CharField(max_length=50)

    def __str__(self):
        return str(self.name) + " ["+str(self.isbn)+']'


class Student(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    # Both are issued by main_app.idgen when the student is created — never
    # typed in by the admin. See that module for the layout of each.
    registration_number = models.CharField(
        max_length=15, null=True, blank=True, unique=True,
        validators=[RegexValidator(REGISTRATION_NUMBER_RE, REGISTRATION_NUMBER_HELP)])
    roll_number = models.CharField(
        max_length=6, null=True, blank=True,
        validators=[RegexValidator(r'^\d{6}$', 'Roll number must be exactly 6 digits')])
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING, null=True)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default="morning")
    # Which semester the student is currently enrolled in. New students start at
    # semester 1; the "promote" actions bump this by one (an academic year is two
    # semesters), capped at the course's total number of semesters.
    current_semester = models.PositiveSmallIntegerField(default=1)
    # Set when the student finishes the final semester. Passed-out students are
    # excluded from the active student body (lists, attendance, promotion) and are
    # kept on record per course + session under "Passed Out Students".
    passed_out = models.BooleanField(default=False)
    passed_out_date = models.DateField(null=True, blank=True)
    parent_full_name = models.CharField(max_length=150, blank=True, default="")
    parent_phone_number = models.CharField(max_length=20, blank=True, default="")
    parent_relationship = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name


class IssuedSequence(models.Model):
    """High-water mark for a family of serial numbers, e.g. staff IDs issued in
    2026 or registration numbers in the 2022 batch.

    Reading "highest number currently in the table, plus one" would quietly
    recycle a number as soon as its owner is deleted, handing a departed
    student's registration number to the next arrival. This table remembers
    what has been handed out regardless of who is still on the roll, so a
    deletion leaves a permanent gap instead.

    Roll numbers deliberately do NOT use this — they are positional and are
    meant to close up (see RollNumberBatch).
    """
    key = models.CharField(max_length=40, unique=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "%s → %d" % (self.key, self.last_value)


class RollNumberBatch(models.Model):
    """Roll-number state for one intake — a (session, course) cohort.

    Roll numbers end in the student's alphabetical position within their
    cohort, which only stays true if adding a student renumbers everyone who
    sorts after them. That is fine while the intake is still being filled, and
    unacceptable once the cohort has results on record under those numbers — so
    the cohort renumbers freely until it is locked, and afterwards late arrivals
    are simply appended at the end.

    The lock is set when the cohort leaves Semester 1 (see
    api/students._cascade_promote_course), or lazily by idgen the first time it
    notices a cohort that has already moved up.
    """
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('session', 'course')
        verbose_name_plural = 'Roll number batches'

    def __str__(self):
        return "%s — %s (%s)" % (
            self.course.short_name if self.course else '?', self.session,
            'locked' if self.locked else 'open')


class Library(models.Model):
    student = models.ForeignKey(Student,  on_delete=models.CASCADE, null=True, blank=False)
    book = models.ForeignKey(Book,  on_delete=models.CASCADE, null=True, blank=False)
    def __str__(self):
        return str(self.student)

def expiry():
    return datetime.today() + timedelta(days=14)
class IssuedBook(models.Model):
    student_id = models.CharField(max_length=100, blank=True) 
    isbn = models.CharField(max_length=13)
    issued_date = models.DateField(auto_now=True)
    expiry_date = models.DateField(default=expiry)



class Staff(models.Model):
    # Issued by main_app.idgen on creation (YYNNNN — joining year plus a
    # per-year serial); never typed in by the admin, never reused.
    staff_id = models.CharField(
        max_length=6, null=True, blank=True, unique=True,
        validators=[RegexValidator(r'^\d{6}$', 'Staff ID must be exactly 6 digits')])
    # A teacher can be assigned to the Morning shift, the Day shift, or both.
    teaches_morning = models.BooleanField(default=True)
    teaches_day = models.BooleanField(default=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.first_name + " " +  self.admin.last_name

    @property
    def taught_courses(self):
        """Courses this staff actually teaches in, derived from their
        Assign Subjects picks (CourseSubject.morning_staff/day_staff) rather
        than a manually-maintained list — picking up a subject in a course
        is what puts that course here."""
        return Course.objects.filter(
            Q(coursesubject__morning_staff=self) | Q(coursesubject__day_staff=self)
        ).distinct()

    @property
    def shifts(self):
        """List of shift values this staff teaches, e.g. ['morning', 'day']."""
        result = []
        if self.teaches_morning:
            result.append('morning')
        if self.teaches_day:
            result.append('day')
        return result

    @property
    def shifts_display(self):
        labels = dict(SHIFT_CHOICES)
        return ", ".join(labels[s] for s in self.shifts) or "—"


class Subject(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True, default="")
    credit_hours = models.PositiveSmallIntegerField(null=True, blank=True)
    courses = models.ManyToManyField(Course, through='CourseSubject', related_name='subjects')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CourseSubject(models.Model):
    """Links a Subject to a Course at a specific semester.

    A subject can belong to multiple courses, each at its own semester
    (e.g. Sem 2 in one course, Sem 4 in another). Teaching staff are assigned
    per course+subject, so different teachers can teach the same subject in
    different courses (or several teachers can share one course+subject)."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)
    # Teaching is per-shift: at most ONE teacher per (course, subject, shift).
    # Using a single FK per shift structurally enforces that rule, while the
    # same teacher can hold many slots across courses/subjects/shifts, and the
    # morning vs day teacher of the same class can differ.
    morning_staff = models.ForeignKey(
        Staff, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='morning_assignments')
    day_staff = models.ForeignKey(
        Staff, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='day_assignments')

    class Meta:
        unique_together = ('course', 'subject')

    def __str__(self):
        return "%s - %s (Sem %s)" % (self.course, self.subject, self.semester)

    def staff_for_shift(self, shift):
        return self.morning_staff if shift == 'morning' else self.day_staff


class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING)
    # A subject can be taught in several courses at different semesters, so the
    # session alone does NOT identify a class (two courses can share an intake
    # session). Storing the course + semester the attendance was taken for keeps
    # each class's records separate when viewing/updating.
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default="morning")
    date = models.DateField()
    # Once confirmed via the Update Attendance screen the record is locked: it can
    # no longer be edited, only viewed.
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subject', 'course', 'semester', 'shift', 'date')


class AttendanceReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    late = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# A+/A/A- down to D+/D/D-, plus a plain F (no F+/F-).
FINAL_GRADE_CHOICES = [(g, g) for g in (
    "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F",
)]


class StudentResult(models.Model):
    """One student's marks for one subject at one (course, semester) — kept
    even after the student is promoted, since `semester` is recorded here
    rather than read off the student's current state."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.PositiveSmallIntegerField()
    unit_test = models.FloatField(null=True, blank=True)
    internal = models.FloatField(null=True, blank=True)
    pre_board = models.FloatField(null=True, blank=True)
    final_grade = models.CharField(
        max_length=2, blank=True, default="", choices=FINAL_GRADE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'course', 'semester')


class ResultFinalization(models.Model):
    """Marks one (course, subject, semester) result set as locked. Staff can
    no longer edit any student's marks/grade for it once finalized; the
    finalize action itself requires every student's marks to be complete."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semester = models.PositiveSmallIntegerField()
    finalized_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'subject', 'semester')


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Coerce to str so it works whether user_type is passed as 1/2/3 (int) or '1'/'2'/'3'
        user_type = str(instance.user_type)
        if user_type == '1':
            Admin.objects.create(admin=instance)
        if user_type == '2':
            Staff.objects.create(admin=instance)
        if user_type == '3':
            Student.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    user_type = str(instance.user_type)
    if user_type == '1':
        instance.admin.save()
    if user_type == '2':
        instance.staff.save()
    if user_type == '3':
        instance.student.save()

# todos
