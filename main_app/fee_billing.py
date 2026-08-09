"""Raising fee bills: turning a fee structure into one invoice per student.

Lives outside the API layer because two callers need it — the accountant's
invoice-run screen and the promotion cascade that bills a cohort the moment it
moves up a semester (see api/students._cascade_promote_course). Both go
through generate_invoices() so a bill reads the same however it was raised,
the way send_due_soon_reminders() does for the library.

The one rule everything here exists to protect: **running the same invoice run
twice must not bill anybody twice.** The database says so via the unique
constraint on (student, session, semester, instalment); this module is
written so that hitting that constraint is an ordinary, reported outcome
rather than an error the accountant has to interpret.
"""
from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction

from .idgen import next_invoice_number
from .models import (ZERO, FeeAdjustment, FeeInvoice, FeeInvoiceLine,
                     FeeStructure, NotificationStudent, Session, Student)


def structure_for(course, session, semester):
    """The fee structure covering a class, or None if nobody has written one."""
    return FeeStructure.objects.filter(
        course=course, session=session, semester=semester
    ).prefetch_related('items__head').first()


def billable_students(course, session, semester):
    """Who a run for this class would bill.

    Passed-out students are excluded for the same reason the library won't
    lend to them: they have left, and a bill raised against them is one
    nobody will ever collect.
    """
    return Student.objects.filter(
        course=course, session=session, current_semester=semester,
        passed_out=False,
    ).select_related('admin').order_by('roll_number', 'admin__last_name')


def already_billed_ids(session, semester, instalment=1):
    """Student ids that already hold an invoice for this class."""
    return set(FeeInvoice.objects.filter(
        session=session, semester=semester, instalment=instalment
    ).values_list('student_id', flat=True))


def preview_invoice_run(course, session, semester, instalment=1):
    """What a run would do, without doing it.

    The accountant sees this before committing: which structure will be
    applied, who gets billed, and who is skipped because they already hold a
    bill for this semester.
    """
    structure = structure_for(course, session, semester)
    billed = already_billed_ids(session, semester, instalment)
    students = list(billable_students(course, session, semester))
    return {
        'structure': structure,
        'to_bill': [s for s in students if s.id not in billed],
        'already_billed': [s for s in students if s.id in billed],
    }


class NothingToBill(Exception):
    """Raised when a run can't proceed, carrying the reason to show."""


def generate_invoices(course, session, semester, issued_by=None,
                      instalment=1, today=None, notify=True):
    """Raise one invoice per un-billed student in a class.

    Returns {'created': [FeeInvoice], 'skipped': int, 'structure':
    FeeStructure}. Raises NothingToBill when there is no structure to apply
    or it has no lines — billing somebody Rs. 0 is not a thing anybody meant
    to do.

    Each invoice is written in its own savepoint, so one student colliding
    with the unique constraint (a concurrent run, a double-clicked button)
    is counted as skipped and leaves the rest of the run intact.
    """
    today = today or date_cls.today()
    structure = structure_for(course, session, semester)
    if structure is None:
        raise NothingToBill(
            "No fee structure exists for %s, Semester %d in %s. Set one up "
            "before billing this class." % (
                course.short_name if course else '?', semester, session))
    items = list(structure.items.all())
    if not items:
        raise NothingToBill(
            "The fee structure for %s, Semester %d has no fee heads on it "
            "yet, so there is nothing to bill." % (
                course.short_name if course else '?', semester))

    billed = already_billed_ids(session, semester, instalment)
    created, skipped = [], 0

    for student in billable_students(course, session, semester):
        if student.id in billed:
            skipped += 1
            continue
        try:
            # Savepoint per student: a collision here must not roll back the
            # invoices already raised in this run.
            with transaction.atomic():
                invoice = FeeInvoice.objects.create(
                    student=student,
                    course=student.course,
                    session=session,
                    semester=semester,
                    instalment=instalment,
                    structure=structure,
                    number=next_invoice_number(today),
                    issued_date=today,
                    due_date=today + _due_delta(structure),
                    issued_by=issued_by)
                FeeInvoiceLine.objects.bulk_create([
                    FeeInvoiceLine(
                        invoice=invoice, head=item.head,
                        head_name=item.head.name, amount=item.amount)
                    for item in items])
        except IntegrityError:
            skipped += 1
            continue
        created.append(invoice)
        if notify:
            _notify_issued(invoice, structure)

    return {'created': created, 'skipped': skipped, 'structure': structure}


def _due_delta(structure):
    return timedelta(days=structure.due_days or 0)


def _notify_issued(invoice, structure):
    """Tell the student a bill has been raised, through the notification list
    already on their sidebar.

    In-app only. The emailed version goes out from the fee reminder sweep,
    which can afford to fail and retry one student at a time — an invoice run
    for a class of sixty cannot stop halfway because one mailbox is full.
    """
    total = sum((item.amount for item in structure.items.all()), ZERO)
    NotificationStudent.objects.create(
        student=invoice.student,
        message="Fees: your Semester %d bill of Rs. %s (%s) is due on %s." % (
            invoice.semester, total, invoice.number,
            invoice.due_date.strftime('%b. %d, %Y')))


# --------------------------------------------------------------------------
# Adjustments
# --------------------------------------------------------------------------

def signed_amount(kind, amount):
    """Put the right sign on an adjustment the accountant typed in.

    The form asks for a plain positive number and the KIND decides which way
    it moves the bill — a scholarship of "5000" reduces, a late fine of
    "150" adds. A correction is the exception: it is the one kind that has
    to be able to go either way, so its sign is taken as given.
    """
    amount = Decimal(amount)
    if kind == FeeAdjustment.CORRECTION:
        return amount
    magnitude = abs(amount)
    return -magnitude if kind in FeeAdjustment.CREDIT_KINDS else magnitude


def add_adjustment(invoice, kind, amount, reason, accountant=None):
    """Write an adjustment onto a bill. Append-only — see the model."""
    return FeeAdjustment.objects.create(
        invoice=invoice,
        kind=kind,
        amount=signed_amount(kind, amount),
        reason=reason or '',
        created_by=accountant,
        created_by_name=str(accountant) if accountant else '')


# --------------------------------------------------------------------------
# Promotion hook
# --------------------------------------------------------------------------

def bill_active_cohorts(course, today=None):
    """Raise bills for every active cohort of `course` that has a structure
    and isn't billed yet.

    Called after the promotion cascade, where it reads as "bill whoever has
    just moved up" — but it is written as a sweep over the whole course
    rather than as a diff of who moved, because generate_invoices() already
    skips anyone holding a bill. Sweeping is both simpler and self-healing:
    a cohort missed on the day it was promoted (no structure written yet)
    gets picked up by the next run instead of being lost.

    Deliberately quiet: a class with no fee structure is simply not billed.
    Promotion is an academic action and must not fail because the accounts
    office hasn't written next semester's fees. Returns how many invoices
    were raised, for the message the admin sees.
    """
    cohorts = Student.objects.filter(
        course=course, passed_out=False, session__isnull=False
    ).values_list('session', 'current_semester').distinct()

    total = 0
    sessions = {s.id: s for s in Session.objects.filter(
        id__in={c[0] for c in cohorts})}
    for session_id, semester in cohorts:
        try:
            result = generate_invoices(
                course, sessions[session_id], semester, today=today)
        except NothingToBill:
            continue
        total += len(result['created'])
    return total
