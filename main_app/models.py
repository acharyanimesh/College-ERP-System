from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.core.validators import (
    MaxValueValidator, MinValueValidator, RegexValidator)
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.db.models import (
    DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value)
from django.db.models.functions import Cast, Coalesce
from django.contrib.auth.models import AbstractUser
from datetime import date,datetime,timedelta
from decimal import Decimal
import os
import uuid


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
    USER_TYPE = ((1, "HOD"), (2, "Staff"), (3, "Student"), (4, "Librarian"),
                 (5, "Accountant"))
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
    # Text, not a number: ISBNs are identifiers rather than quantities, and an
    # integer column silently eats the leading zeros some of them carry.
    isbn = models.CharField(max_length=13)
    category = models.CharField(max_length=50)
    # How many physical copies the library holds of this title. Approving a
    # borrow request is only meaningful against a count, so a catalogue row
    # carries one even when the library only owns a single copy.
    total_copies = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return str(self.name) + " ["+str(self.isbn)+']'

    @property
    def copies_out(self):
        """Copies not on the shelf. An approved-but-uncollected request holds
        one just as firmly as a collected loan does — otherwise the librarian
        could promise the same copy to five students."""
        return self.requests.filter(
            status__in=BookRequest.HOLDING_STATUSES).count()

    @property
    def available_copies(self):
        return max(self.total_copies - self.copies_out, 0)


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


class Staff(models.Model):
    # Issued by main_app.idgen on creation (YYNNNN — joining year plus a
    # per-year serial); never typed in by the admin, never reused. Staff and
    # Librarian draw on one counter, so an employee ID identifies exactly one
    # person regardless of which of the two roles they hold.
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


class Librarian(models.Model):
    """The college librarian: runs the book catalogue and decides on the
    students' borrow requests. Not a teacher — a librarian has no shifts,
    subjects or classes, which is why this is its own role rather than a flag
    on Staff."""
    # Drawn from the same per-year counter as Staff.staff_id — see idgen.
    librarian_id = models.CharField(
        max_length=6, null=True, blank=True, unique=True,
        validators=[RegexValidator(r'^\d{6}$', 'Librarian ID must be exactly 6 digits')])
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name


class Accountant(models.Model):
    """The college accounts office: bills the fees, takes the money and
    answers for the ledger.

    Its own role rather than a permission on Admin, for the same reason
    Librarian is: whoever handles money should not also be the person who can
    create, edit and delete the student the money is attached to. The admin
    keeps read-only oversight (see api/permissions.IsAccountantOrAdmin) —
    they can see every rupee, and move none of it.
    """
    # Drawn from the same per-year counter as Staff.staff_id and
    # Librarian.librarian_id — see idgen. One employee, one number, whichever
    # of the three roles they hold.
    accountant_id = models.CharField(
        max_length=6, null=True, blank=True, unique=True,
        validators=[RegexValidator(r'^\d{6}$', 'Accountant ID must be exactly 6 digits')])
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name


# How long a borrowed book may be kept, and what a late day costs.
LOAN_PERIOD_DAYS = 14
FINE_PER_DAY = 10
# An approved renewal pushes the due date out by this much. A loan may be
# renewed once; after that the book has to come back and be requested afresh.
RENEWAL_PERIOD_DAYS = 7
# How many days before the due date the "return or renew" nudge goes out.
DUE_SOON_REMINDER_DAYS = 3


class BookRequest(models.Model):
    """A student's request to borrow a book, and the loan it turns into.

        PENDING ──approve──> APPROVED ──issue──> ISSUED ──return──> RETURNED
           │                     │
           ├──reject───> REJECTED┘   (also how an uncollected approval lapses)
           └──cancel───> CANCELLED

    Request and loan share one row on purpose: a student asking for a book,
    being allowed to have it, and carrying it home are three points on one
    story, and splitting them across tables would mean stitching that story
    back together for every "where is my book?" screen.
    """
    PENDING = 'pending'
    APPROVED = 'approved'
    ISSUED = 'issued'
    RETURNED = 'returned'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Ready for pickup'),
        (ISSUED, 'Borrowed'),
        (RETURNED, 'Returned'),
        (REJECTED, 'Rejected'),
        (CANCELLED, 'Cancelled'),
    )
    # A copy is off the shelf in these two states.
    HOLDING_STATUSES = (APPROVED, ISSUED)
    # These count against the student's borrowing limit, and are what makes a
    # second request for the same book a duplicate.
    OPEN_STATUSES = (PENDING, APPROVED, ISSUED)

    # Renewal is a sub-state of one ISSUED loan rather than a status of its
    # own: the loan carries on either way, only the due date may move. It runs
    # NONE → REQUESTED → GRANTED/DECLINED and never resets, which is what
    # enforces "a book cannot be renewed more than once" — a second extension
    # means returning the book and requesting it again.
    RENEWAL_NONE = 'none'
    RENEWAL_REQUESTED = 'requested'
    RENEWAL_GRANTED = 'granted'
    RENEWAL_DECLINED = 'declined'
    RENEWAL_CHOICES = (
        (RENEWAL_NONE, 'Not requested'),
        (RENEWAL_REQUESTED, 'Renewal requested'),
        (RENEWAL_GRANTED, 'Renewed'),
        (RENEWAL_DECLINED, 'Renewal declined'),
    )

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='book_requests')
    # PROTECT, not CASCADE: a title someone is currently holding must not be
    # deleteable out from under the loan record.
    book = models.ForeignKey(
        Book, on_delete=models.PROTECT, related_name='requests')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    student_note = models.TextField(blank=True, default="")
    # Why it was rejected, or any remark the librarian left on the decision.
    librarian_note = models.TextField(blank=True, default="")

    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        Librarian, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='decisions')
    # Set when the student actually collects the book — the loan clock starts
    # at the desk, not at approval.
    issued_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    returned_date = models.DateField(null=True, blank=True)

    # --- Renewal of this loan (see RENEWAL_CHOICES above) ---
    renewal_state = models.CharField(
        max_length=10, choices=RENEWAL_CHOICES, default=RENEWAL_NONE)
    renewal_requested_at = models.DateTimeField(null=True, blank=True)
    renewal_reason = models.TextField(blank=True, default="")
    renewal_decided_at = models.DateTimeField(null=True, blank=True)
    renewal_decided_by = models.ForeignKey(
        Librarian, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='renewal_decisions')
    renewal_librarian_note = models.TextField(blank=True, default="")
    # The due date as it stood before the extension, kept so the loan's own
    # history still shows what the original deadline was.
    due_date_before_renewal = models.DateField(null=True, blank=True)

    # Guards the due-soon reminder against going out twice (the sweep is meant
    # to be safe to run repeatedly, including by hand from the dashboard).
    reminder_sent_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        constraints = [
            # One live request per student per book, enforced by the database
            # rather than by whichever view happens to remember to check.
            # (OPEN_STATUSES spelled out: a nested Meta can't see the names
            # defined in the class body around it.)
            models.UniqueConstraint(
                fields=['student', 'book'],
                condition=Q(status__in=('pending', 'approved', 'issued')),
                name='one_open_request_per_student_book'),
        ]

    def __str__(self):
        return "%s → %s (%s)" % (self.student, self.book, self.status)

    @property
    def days_overdue(self):
        if self.status != self.ISSUED or not self.due_date:
            return 0
        return max((datetime.today().date() - self.due_date).days, 0)

    @property
    def days_late(self):
        """Days past the due date at the point the book actually came back;
        for a loan still out, days late so far."""
        if self.status == self.RETURNED and self.returned_date and self.due_date:
            return max((self.returned_date - self.due_date).days, 0)
        return self.days_overdue

    @property
    def fine(self):
        """What the student owes today. Frozen once the book comes back —
        a returned loan's fine is whatever it was on the day of return."""
        return self.days_late * FINE_PER_DAY

    @property
    def fine_settled(self):
        """True once the desk has taken the cash (or written the fine off).
        Settlement is the existence of a LibraryFine row, never a flag that
        could be flipped back."""
        return self.fine_records.exists()

    @property
    def fine_outstanding(self):
        """Still owed. A settled loan owes nothing even if the computed fine
        would say otherwise — the receipt is what counts."""
        return 0 if self.fine_settled else self.fine

    @property
    def can_request_renewal(self):
        """One renewal per loan, and only while the book is still in time:
        a loan already running late is a return, not an extension."""
        return (self.status == self.ISSUED
                and self.renewal_state == self.RENEWAL_NONE
                and self.days_overdue == 0)


class ImmutableRecord(models.Model):
    """A row that can be written once and never altered again.

    Django gives no built-in way to say "append only", so the two mutating
    paths are closed off here: save() refuses a second write to an existing
    row, and delete() refuses outright. This is enforcement, not convention —
    a careless view, a shell one-liner and the Django admin all hit the same
    wall.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise ValueError(
                "%s is an immutable record and cannot be modified."
                % type(self).__name__)
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "%s is an immutable record and cannot be deleted."
            % type(self).__name__)


class LibraryFine(ImmutableRecord):
    """The receipt for a late-return fine, settled in cash at the desk.

    Money changed hands in the real world, so this row is the record of that
    and is append-only (see ImmutableRecord): a mistake is corrected by
    issuing a second, offsetting record, never by editing or deleting this
    one. Both portals read the same rows — the student sees their own
    receipts, the librarian sees every receipt taken at the desk.

    The librarian is stored twice on purpose. The FK is for querying; the
    name is a snapshot, so who took the money survives that account later
    being removed.
    """
    PAID = 'paid'
    WAIVED = 'waived'
    KIND_CHOICES = ((PAID, 'Paid in cash'), (WAIVED, 'Waived'))

    # PROTECT throughout: nothing a receipt points at may be deleted out from
    # under it, or the record stops explaining itself.
    request = models.ForeignKey(
        BookRequest, on_delete=models.PROTECT, related_name='fine_records')
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='library_fines')
    receipt_no = models.CharField(max_length=20, unique=True)
    kind = models.CharField(max_length=6, choices=KIND_CHOICES, default=PAID)
    # In rupees. Whole numbers — the fine is a flat per-day rate.
    amount = models.PositiveIntegerField()
    days_late = models.PositiveSmallIntegerField(default=0)
    rate_per_day = models.PositiveSmallIntegerField(default=FINE_PER_DAY)
    collected_by = models.ForeignKey(
        Librarian, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='fines_collected')
    collected_by_name = models.CharField(max_length=150, blank=True, default="")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # One receipt per loan. A loan is fined once; anything else is a
            # double charge, and the database is the right place to say so.
            models.UniqueConstraint(
                fields=['request'], name='one_fine_record_per_loan'),
        ]

    def __str__(self):
        return "%s · %s · Rs. %d (%s)" % (
            self.receipt_no, self.student, self.amount, self.kind)

    @staticmethod
    def next_receipt_no():
        """LIB-FINE-000001, allocated on insert. Sequential rather than random
        because a cash receipt gets read out loud and written in a register."""
        last = LibraryFine.objects.order_by('-id').values_list(
            'receipt_no', flat=True).first()
        n = 0
        if last and last.rsplit('-', 1)[-1].isdigit():
            n = int(last.rsplit('-', 1)[-1])
        return "LIB-FINE-%06d" % (n + 1)


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


# --------------------------------------------------------------------------
# Fees
#
# Deliberately the same shape as the library's fine ledger above: what somebody
# owes is DERIVED from rows that each explain themselves, and every row
# recording money that changed hands is append-only (see ImmutableRecord).
#
#   FeeHead             "Tuition", "Exam", "Lab" — the college's chart of fees
#   FeeStructure        what one (course, session, semester) costs
#     └ FeeStructureItem    one head and its amount on that structure
#   FeeInvoice          one student's bill for one semester
#     ├ FeeInvoiceLine      the structure's items, SNAPSHOT at issue time
#     ├ FeeAdjustment       scholarship / waiver / late fine     [append-only]
#     └ FeePayment          a receipt                            [append-only]
#   PaymentAttempt      one handshake with an online payment gateway
#
# A balance is never stored. A stored balance means two places can disagree
# about what a student owes, and the one that is wrong is the one somebody
# reads out at the counter.
# --------------------------------------------------------------------------

# Fees carry paisa — a percentage scholarship on a Rs. 47,500 tuition alone
# guarantees it — so they are Decimal, unlike LibraryFine.amount, which is a
# whole number of rupees because that fine is a flat per-day rate. Never
# float: a rounding drift in a ledger is one somebody has to explain.
MONEY = {'max_digits': 10, 'decimal_places': 2}
ZERO = Decimal('0.00')
# Wider than MONEY: these hold sums over many rows, not one row's amount.
_TOTAL_FIELD = DecimalField(max_digits=14, decimal_places=2)
_ZERO_TOTAL = Value(ZERO, output_field=_TOTAL_FIELD)


def money(amount):
    """Wrap `amount` so it can be COMPARED against a computed money column.

    Django's SQLite backend binds every Decimal parameter as text
    (`Database.register_adapter(decimal.Decimal, str)`), and SQLite sorts
    every number below every string — so a plain

        .filter(total_balance__gt=Decimal('0.00'))

    is false however much is owed, silently and with no error to notice.
    Casting the literal back to a number restores the comparison; on
    Postgres the cast is a no-op, so this stays correct if a tenant moves
    (see the database-per-tenant plan).

    Only needed for comparisons against an ANNOTATED total. Filtering a
    stored column — FeePayment.amount and the like — goes through the
    field's own adapter and is fine.
    """
    return Cast(Value(amount, output_field=_TOTAL_FIELD), _TOTAL_FIELD)

# How long after issue a bill falls due, when the structure doesn't say.
DEFAULT_FEE_DUE_DAYS = 30


class FeeHead(models.Model):
    """A line a college bills under — Tuition, Admission, Exam, Library
    Deposit.

    A master table rather than free text on each structure, so "how much
    tuition did we collect this session?" is a query instead of a string
    match across every structure the college has ever written.
    """
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, blank=True, default="")
    description = models.CharField(max_length=200, blank=True, default="")
    # Charged every semester (tuition) as opposed to once at admission.
    recurring = models.BooleanField(default=True)
    # Refundable deposits are money the college is holding, not money it has
    # earned. Reports keep them apart.
    refundable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class FeeStructure(models.Model):
    """What one (course, session, semester) costs.

    A template, not a bill: editing a structure changes what the NEXT invoice
    run charges and never touches a bill already issued — FeeInvoiceLine
    copies the amounts at issue time precisely so a mid-session correction
    can't silently rewrite what a student was told to pay.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    semester = models.PositiveSmallIntegerField()
    # Days from issue to the due date, stamped onto each invoice this
    # structure raises.
    due_days = models.PositiveSmallIntegerField(default=DEFAULT_FEE_DUE_DAYS)
    # What a day past the due date costs, applied by the overdue sweep as a
    # FeeAdjustment. Zero means this college doesn't fine late fees.
    late_fine_per_day = models.DecimalField(default=ZERO, **MONEY)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'session', 'semester')
        ordering = ['course', 'session', 'semester']

    def __str__(self):
        return "%s — Sem %d (%s)" % (
            self.course.short_name if self.course else '?', self.semester,
            self.session)

    @property
    def total(self):
        return sum((item.amount for item in self.items.all()), ZERO)


class FeeStructureItem(models.Model):
    """One head and its amount on a structure."""
    structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name='items')
    # PROTECT: a head that has been billed under must stay explicable.
    head = models.ForeignKey(FeeHead, on_delete=models.PROTECT)
    amount = models.DecimalField(**MONEY)

    class Meta:
        unique_together = ('structure', 'head')
        ordering = ['head__name']

    def __str__(self):
        return "%s · %s" % (self.head, self.amount)


class FeeInvoiceQuerySet(models.QuerySet):
    def with_totals(self):
        """Annotate total_gross, total_adjustments, total_paid, total_balance —
        in SQL, what FeeInvoice's gross/adjustment_total/paid/balance
        properties work out in Python.

        Three subqueries rather than three Sums over joins: joined aggregates
        multiply each other's rows, so an invoice with two lines and two
        payments would report double of both. Anything that filters on what
        is owed — the reminder sweep, the defaulter list — has to come
        through here.

        The total_ prefix keeps these clear of the properties of the same
        meaning: an annotation whose name matched one would be assigned onto
        the instance over it, and a property has no setter to assign to.
        """
        def _sum_of(model, field='amount'):
            # Resolved when the method runs, so the models defined further
            # down this file are available by then.
            rows = (model.objects
                    .filter(invoice=OuterRef('pk'))
                    .values('invoice')
                    .annotate(total=Sum(field))
                    .values('total'))
            return Coalesce(
                Subquery(rows, output_field=_TOTAL_FIELD), _ZERO_TOTAL)

        return self.annotate(
            total_gross=_sum_of(FeeInvoiceLine),
            total_adjustments=_sum_of(FeeAdjustment),
            total_paid=_sum_of(FeePayment),
        ).annotate(
            total_balance=ExpressionWrapper(
                F('total_gross') + F('total_adjustments') - F('total_paid'),
                output_field=_TOTAL_FIELD))

    def outstanding(self):
        """Live bills with money still on them."""
        return self.with_totals().filter(
            cancelled_at__isnull=True, total_balance__gt=money(ZERO))

    def overdue(self, on=None):
        """Outstanding bills whose due date has already passed."""
        return self.outstanding().filter(due_date__lt=on or date.today())

    def due_in(self, days, on=None):
        """Outstanding bills falling due EXACTLY `days` from now.

        Exactly, not "within" — as with the library's due-soon sweep, a bill
        due in a week should produce one reminder on one day, not a fresh one
        every morning until it is due.
        """
        return self.outstanding().filter(
            due_date=(on or date.today()) + timedelta(days=days))


class FeeInvoice(models.Model):
    """One student's bill for one semester.

    course/session/semester are copied here rather than read off the student,
    for the same reason StudentResult carries its own semester: the student
    moves on, and last year's bill has to keep saying what it was for.
    """
    # PROTECT throughout the fee models, as in LibraryFine: nothing a
    # financial record points at may be deleted out from under it.
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='fee_invoices')
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    session = models.ForeignKey(Session, on_delete=models.PROTECT)
    semester = models.PositiveSmallIntegerField()
    # Which semesterly bill this is, for colleges that split a semester into
    # instalments. Defaults to 1 and is what keeps the invoice run idempotent
    # (see the unique constraint) without ruling instalments out later.
    instalment = models.PositiveSmallIntegerField(default=1)
    # Informational — which template raised it. The LINES are the record of
    # what was charged; this only says where they came from.
    structure = models.ForeignKey(
        FeeStructure, null=True, blank=True, on_delete=models.SET_NULL)

    number = models.CharField(max_length=24, unique=True)
    issued_date = models.DateField()
    due_date = models.DateField()

    # A cancelled bill stays on the record with its reason attached — a
    # withdrawn charge is a thing that happened, not a thing to delete.
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        Accountant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='cancelled_invoices')
    cancel_reason = models.TextField(blank=True, default="")

    issued_by = models.ForeignKey(
        Accountant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='issued_invoices')
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FeeInvoiceQuerySet.as_manager()

    # Derived states, in the order they're checked by `status`.
    CANCELLED, PAID, OVERDUE, PARTIAL, DUE = (
        'cancelled', 'paid', 'overdue', 'partial', 'due')

    class Meta:
        ordering = ['-issued_date', '-id']
        constraints = [
            # Re-running the invoice run for a class must not double-bill
            # anybody, and the database is the right place to say so rather
            # than whichever view remembers to check.
            models.UniqueConstraint(
                fields=['student', 'session', 'semester', 'instalment'],
                name='one_invoice_per_student_semester'),
        ]

    def __str__(self):
        return "%s · %s · Sem %d" % (self.number, self.student, self.semester)

    # -- Money. Each is a plain sum so a single invoice explains itself
    # without the annotations above; use with_totals() for querying in bulk.
    @property
    def gross(self):
        """What the structure charged, before anything was done about it."""
        return sum((line.amount for line in self.lines.all()), ZERO)

    @property
    def adjustment_total(self):
        """Signed: a late fine adds, a scholarship takes away."""
        return sum((adj.amount for adj in self.adjustments.all()), ZERO)

    @property
    def payable(self):
        return self.gross + self.adjustment_total

    @property
    def paid(self):
        return sum((p.amount for p in self.payments.all()), ZERO)

    @property
    def balance(self):
        """What the student still owes. Never stored — see the section note."""
        return self.payable - self.paid

    @property
    def is_cancelled(self):
        return self.cancelled_at is not None

    @property
    def days_overdue(self):
        if self.is_cancelled or self.balance <= ZERO or not self.due_date:
            return 0
        return max((datetime.today().date() - self.due_date).days, 0)

    @property
    def status(self):
        if self.is_cancelled:
            return self.CANCELLED
        if self.balance <= ZERO:
            return self.PAID
        if self.days_overdue:
            return self.OVERDUE
        return self.PARTIAL if self.paid > ZERO else self.DUE


class FeeInvoiceLine(models.Model):
    """One charge on a bill, snapshotted from the structure at issue time.

    head_name is stored beside the FK for the same reason LibraryFine keeps
    collected_by_name: the FK is for querying, the text is so the bill still
    reads correctly after the head is renamed.
    """
    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.CASCADE, related_name='lines')
    head = models.ForeignKey(
        FeeHead, null=True, blank=True, on_delete=models.PROTECT)
    head_name = models.CharField(max_length=80)
    amount = models.DecimalField(**MONEY)

    class Meta:
        ordering = ['head_name']

    def __str__(self):
        return "%s · %s" % (self.head_name, self.amount)


class FeeAdjustment(ImmutableRecord):
    """Something that changed what a bill comes to, after it was issued.

    Append-only, and signed: POSITIVE adds to what is owed (a late fine),
    NEGATIVE takes away (a scholarship, a waiver). A mistake is corrected by
    writing the opposite adjustment, never by editing this row — which is
    what lets the invoice show not just the number but how it got there.
    """
    SCHOLARSHIP = 'scholarship'
    DISCOUNT = 'discount'
    WAIVER = 'waiver'
    LATE_FINE = 'late_fine'
    CORRECTION = 'correction'
    KIND_CHOICES = (
        (SCHOLARSHIP, 'Scholarship'),
        (DISCOUNT, 'Discount'),
        (WAIVER, 'Waiver'),
        (LATE_FINE, 'Late fine'),
        (CORRECTION, 'Correction'),
    )
    # The kinds that may only ever reduce a bill. LATE_FINE may only add;
    # CORRECTION goes either way, which is what makes it a correction.
    CREDIT_KINDS = (SCHOLARSHIP, DISCOUNT, WAIVER)

    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.PROTECT, related_name='adjustments')
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    amount = models.DecimalField(
        help_text="Positive adds to the bill, negative reduces it.", **MONEY)
    reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        Accountant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='fee_adjustments')
    created_by_name = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return "%s · %s %s" % (self.invoice.number, self.get_kind_display(),
                               self.amount)


class FeePayment(ImmutableRecord):
    """The receipt for money received against a bill.

    Append-only for the same reason LibraryFine is: money changed hands in the
    real world, and this row is the record of that. A mistake is corrected by
    a second, offsetting record — never by editing or deleting this one.

    Both portals read these rows: the student sees their own receipts, the
    accounts office sees every receipt taken.
    """
    CASH = 'cash'
    CHEQUE = 'cheque'
    BANK = 'bank'
    ONLINE = 'online'
    MODE_CHOICES = (
        (CASH, 'Cash at counter'),
        (CHEQUE, 'Cheque'),
        (BANK, 'Bank deposit'),
        (ONLINE, 'Online payment'),
    )

    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.PROTECT, related_name='payments')
    # Denormalised from the invoice so "this student's receipts" is one query,
    # exactly as LibraryFine.student is.
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='fee_payments')
    receipt_no = models.CharField(max_length=24, unique=True)
    amount = models.DecimalField(**MONEY)
    mode = models.CharField(max_length=8, choices=MODE_CHOICES, default=CASH)
    # The gateway handshake this receipt came out of, for online payments.
    # OneToOne, so one successful attempt can be credited exactly once — a
    # structural guard against a replayed callback, on top of the unique
    # (gateway, gateway_ref) on PaymentAttempt itself.
    attempt = models.OneToOneField(
        'PaymentAttempt', null=True, blank=True, on_delete=models.PROTECT,
        related_name='payment')
    # Cheque number, bank voucher number or gateway reference — whatever the
    # counter would write in the register beside this receipt.
    reference = models.CharField(max_length=100, blank=True, default="")
    received_on = models.DateField()
    # FK to query by, name so who took the money survives the account being
    # removed. Null for an online payment: nobody took it.
    collected_by = models.ForeignKey(
        Accountant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='fees_collected')
    collected_by_name = models.CharField(max_length=150, blank=True, default="")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return "%s · %s · %s (%s)" % (
            self.receipt_no, self.student, self.amount, self.mode)


class PaymentAttempt(models.Model):
    """One handshake with an online gateway.

    Kept apart from FeePayment on purpose: most of what happens here is
    students changing their minds, gateways timing out and callbacks arriving
    twice, and none of that belongs in a receipt ledger. A FeePayment comes
    into existence only once an attempt has been verified server-to-server —
    never from what the browser came back holding.

    Unlike the receipt, this row is meant to move: it is the one part of the
    fee system that is a state machine rather than a record.
    """
    ESEWA = 'esewa'
    KHALTI = 'khalti'
    SANDBOX = 'sandbox'
    GATEWAY_CHOICES = (
        (ESEWA, 'eSewa'),
        (KHALTI, 'Khalti'),
        # No credentials, always succeeds. Lets the whole flow be exercised
        # in development, the way EMAIL_BACKEND falls back to the console.
        (SANDBOX, 'Sandbox (development)'),
    )

    INITIATED = 'initiated'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    EXPIRED = 'expired'
    STATUS_CHOICES = (
        (INITIATED, 'Initiated'),
        (SUCCEEDED, 'Succeeded'),
        (FAILED, 'Failed'),
        # Nothing came back and the reconciliation sweep gave up on it.
        (EXPIRED, 'Expired'),
    )
    # Nothing more will happen to an attempt in one of these.
    FINAL_STATUSES = (SUCCEEDED, FAILED, EXPIRED)

    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.PROTECT, related_name='payment_attempts')
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='payment_attempts')
    # Ours, generated at initiation and handed to the gateway as the order id.
    # This is what the verification call looks the attempt back up by, so it
    # must not be guessable from the invoice number.
    reference = models.CharField(max_length=36, unique=True)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES)
    # Theirs, learnt on the callback. Blank until then.
    gateway_ref = models.CharField(max_length=100, blank=True, default="")
    # Fixed at initiation from the invoice the server looked up — never from
    # what the browser posted, which is the whole point of doing it here.
    amount = models.DecimalField(**MONEY)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=INITIATED,
        db_index=True)
    # The gateway's verification response, kept verbatim. When a payment is
    # disputed months later this is the only thing that can settle it.
    payload = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # A gateway reference is credited once and once only. A callback
            # that arrives twice — and they do — hits this instead of paying
            # the bill down twice. Conditional so the many attempts still
            # waiting on a reference don't collide on the empty string.
            models.UniqueConstraint(
                fields=['gateway', 'gateway_ref'],
                condition=~Q(gateway_ref=''),
                name='one_attempt_per_gateway_reference'),
        ]

    def __str__(self):
        return "%s · %s · %s (%s)" % (
            self.reference, self.gateway, self.amount, self.status)

    @property
    def is_final(self):
        return self.status in self.FINAL_STATUSES


def deposit_slip_path(instance, filename):
    """Where an uploaded slip lands.

    The client's filename decides only the extension — the rest is ours. A
    student-uploaded name is untrusted input, and this is the one place in the
    system where a file arrives from outside the staffroom.
    """
    extension = os.path.splitext(filename)[1].lower()[:10]
    return "deposit_slips/%s/%s%s" % (
        datetime.today().strftime('%Y/%m'), uuid.uuid4().hex, extension)


class DepositSlip(models.Model):
    """A student's claim that they paid a bill into the college's bank.

    The slip is NOT a payment. It is a claim, and the FeePayment only comes
    into existence when somebody at the accounts office has looked at the
    image beside the bank statement and said yes — the same rule the gateway
    flow follows, where a PaymentAttempt becomes a receipt only after a
    server-to-server verification. What the student types here is evidence,
    never a ledger entry.

    Like PaymentAttempt and unlike FeePayment, this row is a state machine and
    is meant to move.
    """
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (PENDING, 'Awaiting verification'),
        (VERIFIED, 'Verified'),
        (REJECTED, 'Rejected'),
    )

    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.PROTECT, related_name='deposit_slips')
    # Denormalised exactly as FeePayment.student is, so "my slips" is one
    # query and stays answerable if the invoice is later cancelled.
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='deposit_slips')
    amount = models.DecimalField(**MONEY)
    deposited_on = models.DateField()
    bank_name = models.CharField(max_length=100)
    # The voucher or deposit-slip number, which is what the office matches
    # against the bank statement.
    reference = models.CharField(max_length=100)
    image = models.FileField(upload_to=deposit_slip_path)
    note = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    # The receipt this slip turned into. OneToOne, so a slip can be credited
    # exactly once however many times the verify button is pressed — the same
    # structural guard PaymentAttempt gets from FeePayment.attempt.
    payment = models.OneToOneField(
        FeePayment, null=True, blank=True, on_delete=models.PROTECT,
        related_name='deposit_slip')
    # FK to query by, name so the reviewer survives the account being removed.
    reviewed_by = models.ForeignKey(
        Accountant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='slips_reviewed')
    reviewed_by_name = models.CharField(max_length=150, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # Why it was rejected. Required on rejection: a student whose money the
    # college says it cannot see is owed a reason it can act on.
    review_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # The same slip cannot be submitted against the same bill twice —
            # the common case being an impatient student pressing upload again
            # rather than anything dishonest. Scoped to live rows so a
            # rejected slip can be corrected and resubmitted.
            models.UniqueConstraint(
                fields=['invoice', 'reference'],
                condition=~Q(status='rejected'),
                name='one_live_slip_per_invoice_reference'),
        ]

    def __str__(self):
        return "%s · %s · %s (%s)" % (
            self.reference, self.student, self.amount, self.status)

    @property
    def is_pending(self):
        return self.status == self.PENDING


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
        if user_type == '4':
            Librarian.objects.create(admin=instance)
        if user_type == '5':
            Accountant.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    user_type = str(instance.user_type)
    if user_type == '1':
        instance.admin.save()
    if user_type == '2':
        instance.staff.save()
    if user_type == '3':
        instance.student.save()
    if user_type == '4':
        instance.librarian.save()
    if user_type == '5':
        instance.accountant.save()

# todos
