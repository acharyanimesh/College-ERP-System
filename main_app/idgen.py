"""Issuing of the identifiers nobody types in by hand: employee IDs, student
roll numbers, student registration numbers, and the fee ledger's invoice and
receipt numbers.

    Employee ID           YYNNNN            250001
                          |  |
                          |  +-- serial within that joining year, from 0001
                          +----- last two digits of the joining year

    Roll number           YYSSNN            220101
                          |  | |
                          |  | +-- alphabetical position in that slot, 01 up
                          |  +---- slot: one per (course, shift) pair —
                          |         course 1 is 01 morning / 02 day, course 2
                          |         is 03 / 04, and so on up to 99
                          +------- last two digits of the session's start year

    Registration number   YYYY-01-BB-NNNN   2022-01-01-0001
                          |    |  |  |
                          |    |  |  +-- serial within the batch, from 0001
                          |    |  +----- Session.batch_code (college-wide)
                          |    +-------- constant institution code
                          +------------- session start year

    Invoice number        INV-YYYY-NNNNNN   INV-2026-000042
    Receipt number        FEE-YYYY-NNNNNN   FEE-2026-000042
                              |    |
                              |    +------ serial within that year, from 000001
                              +----------- year the document was raised

Employee IDs cover all three staff-room roles: Staff.staff_id,
Librarian.librarian_id and Accountant.accountant_id come out of one per-year
counter, so no two employees can end up carrying the same number.

Employee IDs and registration numbers are drawn from IssuedSequence counters, so
they are never reused after a deletion — a gap in the sequence is preferable to
handing a departed student's number to somebody else. Callers run inside the
transaction the API views already open, so an allocation that ends in a failed
save gives the number back; the unique constraints on staff_id and
registration_number are what ultimately guarantee no two rows collide.

Roll numbers are alphabetical, so they belong to a whole group rather than to
one student: adding "Bina" between "Anil" and "Chetan" has to push Chetan down.
`resequence_cohort` does that, and declines once the intake's RollNumberBatch
is locked (see that model's docstring for why).

Note the two different groupings at work. Numbering runs per (session, course,
SHIFT) — morning and day each count from 01, since the slot already keeps them
apart. Locking runs per (session, course), covering both shifts: admissions for
an intake close once, not once per shift.

Locking is one-way. There is deliberately no unlock: the numbers a locked
intake carries are already on attendance sheets and marksheets, and reopening
would let the next admission rewrite them.
"""
from datetime import date

from django.utils import timezone

from .models import SHIFT_SLOT_OFFSET, roll_slot

# Second group of every registration number. Constant today; the college would
# only need a second value here if it ever ran more than one campus.
INSTITUTION_CODE = "01"


def _highest(queryset, field):
    return queryset.order_by('-' + field).values_list(field, flat=True).first()


def _claim_serial(key, in_use):
    """Take the next serial under `key` and record it as spent.

    `in_use` is the highest serial visible in the table right now; it only
    matters for rows issued before this counter existed (the backfill
    migration), after which the counter itself is always ahead.
    """
    from .models import IssuedSequence

    counter, _ = IssuedSequence.objects.get_or_create(key=key)
    serial = max(counter.last_value, in_use) + 1
    counter.last_value = serial
    counter.save(update_fields=['last_value'])
    return serial


def _sort_key(student):
    """Alphabetical ordering within a cohort: surname, then first, then middle.

    Case-insensitive, and falls back to the student's id so two people with
    identical names still get a stable, repeatable order.
    """
    user = student.admin
    return (
        (user.last_name or "").strip().lower(),
        (user.first_name or "").strip().lower(),
        (user.middle_name or "").strip().lower(),
        student.pk or 0,
    )


# --------------------------------------------------------------------------
# Employee IDs (staff + librarians)
# --------------------------------------------------------------------------

def next_employee_id(joining_year=None):
    """Allocate the next free employee ID for `joining_year` (default: today).

    One counter serves every staff-room role, so a staff member, a librarian
    and an accountant hired in the same year never share a number.
    """
    from .models import Accountant, Librarian, Staff

    year = joining_year or date.today().year
    prefix = "%02d" % (year % 100)
    # Highest number visible in any of the tables — only relevant for rows
    # issued before the counter existed (see _claim_serial).
    in_use = max(
        int(highest[2:]) if highest else 0
        for highest in (
            _highest(Staff.objects.filter(staff_id__startswith=prefix), 'staff_id'),
            _highest(Librarian.objects.filter(librarian_id__startswith=prefix),
                     'librarian_id'),
            _highest(Accountant.objects.filter(accountant_id__startswith=prefix),
                     'accountant_id'),
        ))
    serial = _claim_serial("staff:%d" % year, in_use)
    if serial > 9999:
        raise ValueError("All 9999 employee IDs for %d have been issued." % year)
    return "%s%04d" % (prefix, serial)


# --------------------------------------------------------------------------
# Fee invoice and receipt numbers
# --------------------------------------------------------------------------

def _next_document_number(prefix, counter, on=None):
    """INV-2026-000042 and friends: a year-scoped serial from IssuedSequence.

    Through the counter rather than "highest number in the table plus one",
    because a cancelled invoice must not hand its number to the next one —
    a gap in the register is a question somebody can answer, a reused number
    is one nobody can.
    """
    year = (on or date.today()).year
    serial = _claim_serial("%s:%d" % (counter, year), 0)
    if serial > 999999:
        raise ValueError(
            "All 999999 %s numbers for %d have been issued." % (counter, year))
    return "%s-%04d-%06d" % (prefix, year, serial)


def next_invoice_number(on=None):
    """The next fee invoice number, e.g. INV-2026-000042."""
    return _next_document_number("INV", "fee-invoice", on)


def next_receipt_number(on=None):
    """The next fee receipt number, e.g. FEE-2026-000042.

    Sequential rather than random for the same reason LibraryFine's receipts
    are: a receipt number gets read out at a counter and copied into a
    register by hand.
    """
    return _next_document_number("FEE", "fee-receipt", on)


# --------------------------------------------------------------------------
# Registration numbers
# --------------------------------------------------------------------------

def next_registration_number(session):
    """Allocate the next registration number in `session`'s batch.

    The serial runs across the whole session — every course admitted in that
    intake draws on one counter — so it is unique only within the batch, the
    YYYY-01-BB prefix already separating one intake from the next.
    """
    from .models import Student

    if session is None or not session.start_year:
        return None
    if session.batch_code is None:      # row predates the field
        session.save()                  # Session.save() assigns one
    prefix = "%04d-%s-%02d-" % (
        session.start_year.year, INSTITUTION_CODE, session.batch_code)
    highest = _highest(
        Student.objects.filter(registration_number__startswith=prefix),
        'registration_number')
    serial = _claim_serial(
        "registration:%d" % session.pk, int(highest[-4:]) if highest else 0)
    if serial > 9999:
        raise ValueError(
            "All 9999 registration numbers for the %s batch have been issued."
            % session)
    return "%s%04d" % (prefix, serial)


# --------------------------------------------------------------------------
# Roll numbers
# --------------------------------------------------------------------------

def roll_prefix(session, course, shift):
    """The YYSS lead of a roll number, or None if anything needed is missing."""
    if session is None or course is None or not session.start_year:
        return None
    slot = roll_slot(course.code, shift)
    if slot is None:
        return None
    return "%02d%s" % (session.start_year.year % 100, slot)


def get_batch(session, course):
    """The RollNumberBatch for this cohort, created on first use.

    A cohort already past Semester 1 is locked here rather than at promotion
    time, which covers intakes that predate this whole mechanism.
    """
    from .models import RollNumberBatch, Student

    if session is None or course is None:
        return None
    batch, created = RollNumberBatch.objects.get_or_create(
        session=session, course=course)
    if created and Student.objects.filter(
            session=session, course=course, passed_out=False,
            current_semester__gt=1).exists():
        batch.locked = True
        batch.locked_at = timezone.now()
        batch.save()
    return batch


def lock_batches_for_course(course, session_ids=None):
    """Freeze roll numbers for `course`'s cohorts. Returns the number newly
    frozen. Called on promotion, and by the admin's own Lock action."""
    from .models import RollNumberBatch, Student

    if course is None:
        return 0
    if session_ids is None:
        session_ids = Student.objects.filter(
            course=course, passed_out=False).values_list('session', flat=True)
    changed = 0
    for session_id in {s for s in session_ids if s is not None}:
        batch, _ = RollNumberBatch.objects.get_or_create(
            session_id=session_id, course=course)
        if not batch.locked:
            batch.locked = True
            batch.locked_at = timezone.now()
            batch.save()
            changed += 1
    return changed


def batch_lock_state(course, session_ids):
    """('locked' | 'open' | 'mixed' | None) for a group of cohorts.

    None means there is nothing to lock — no cohort, or none that could carry
    roll numbers in the first place.
    """
    from .models import RollNumberBatch

    session_ids = {s for s in session_ids if s is not None}
    if not course or not session_ids:
        return None
    locked = set(RollNumberBatch.objects.filter(
        course=course, session_id__in=session_ids, locked=True
    ).values_list('session_id', flat=True))
    if not locked:
        return 'open'
    return 'locked' if locked >= session_ids else 'mixed'


def next_roll_number(session, course, shift):
    """Roll number for an appended student — used when the intake is locked."""
    from .models import Student

    prefix = roll_prefix(session, course, shift)
    if prefix is None:
        return None
    highest = _highest(
        Student.objects.filter(session=session, course=course, shift=shift,
                               roll_number__startswith=prefix), 'roll_number')
    position = int(highest[4:]) + 1 if highest else 1
    if position > 99:
        raise ValueError(
            "All 99 roll numbers for this course, intake and shift have been "
            "issued.")
    return "%s%02d" % (prefix, position)


def resequence_cohort(session, course):
    """Renumber a (session, course) intake into alphabetical order.

    Each shift is sorted on its own, since the shift digit already separates
    them and both runs start at 01. No-op once the intake is locked. Returns
    how many students' roll numbers actually moved, so callers can tell the
    admin about it.
    """
    from .models import Student

    batch = get_batch(session, course)
    if batch is None or batch.locked:
        return 0

    moved = 0
    for shift in SHIFT_SLOT_OFFSET:
        prefix = roll_prefix(session, course, shift)
        if prefix is None:
            continue
        students = sorted(
            Student.objects.filter(
                session=session, course=course, shift=shift
            ).select_related('admin'), key=_sort_key)
        if len(students) > 99:
            raise ValueError(
                "A course intake cannot hold more than 99 students per shift — "
                "a roll number only has two digits for the alphabetical "
                "position.")
        for position, student in enumerate(students, 1):
            wanted = "%s%02d" % (prefix, position)
            if student.roll_number != wanted:
                Student.objects.filter(pk=student.pk).update(roll_number=wanted)
                moved += 1
    return moved


def assign_student_numbers(student, reissue_registration=False):
    """Give `student` a roll number, and a registration number if they lack one.

    Call after the student's session and course are set and saved. Returns the
    number of *other* students in the cohort whose roll number shifted — always
    0 once the cohort is locked.
    """
    from .models import Student

    if reissue_registration or not student.registration_number:
        number = next_registration_number(student.session)
        if number:
            student.registration_number = number
            Student.objects.filter(pk=student.pk).update(
                registration_number=number)

    batch = get_batch(student.session, student.course)
    if batch is None:
        return 0
    if batch.locked:
        student.roll_number = next_roll_number(
            student.session, student.course, student.shift)
        Student.objects.filter(pk=student.pk).update(
            roll_number=student.roll_number)
        return 0

    moved = resequence_cohort(student.session, student.course)
    student.refresh_from_db(fields=['roll_number'])
    # This student is themselves in `moved`; report only the knock-on effect.
    return max(moved - 1, 0)
