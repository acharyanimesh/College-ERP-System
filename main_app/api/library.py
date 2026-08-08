"""Borrowing: a student asks for a book, the librarian decides, the book goes
out and comes back.

Every state change lives here rather than on the model so there is one place
that knows both which transitions are legal and what the student gets told
about them.
"""
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..library_reminders import send_due_soon_reminders
from ..models import (FINE_PER_DAY, LOAN_PERIOD_DAYS, RENEWAL_PERIOD_DAYS,
                      Book, BookRequest, Librarian, LibraryFine,
                      NotificationStudent, Student)
from .permissions import IsLibrarian, IsStudent
from .serializers import book_request_dict, library_fine_dict

# How many books a student may have in flight at once — pending requests,
# approved-and-uncollected ones and books actually in their bag all count.
MAX_OPEN_PER_STUDENT = 3


def _notify(student, message):
    """Tell the student what happened, through the notification list they
    already have on their sidebar."""
    NotificationStudent.objects.create(student=student, message=message)


def _requests_for(student):
    return BookRequest.objects.filter(student=student).select_related('book')


# --------------------------------------------------------------------------
# Student side
# --------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsStudent])
def my_requests(request):
    """The student's own borrowing history, and the endpoint they raise a new
    request on."""
    student = get_object_or_404(Student, admin=request.user)

    if request.method == 'GET':
        return Response([book_request_dict(r) for r in _requests_for(student)])

    if student.passed_out:
        return Response(
            {'detail': "Passed-out students can't borrow from the library."},
            status=status.HTTP_400_BAD_REQUEST)

    book = get_object_or_404(Book, id=request.data.get('book'))

    overdue = [r for r in _requests_for(student).filter(
        status=BookRequest.ISSUED) if r.days_overdue]
    if overdue:
        return Response(
            {'detail': "You have %d overdue book%s. Return %s before "
                       "requesting another." % (
                           len(overdue), '' if len(overdue) == 1 else 's',
                           'it' if len(overdue) == 1 else 'them')},
            status=status.HTTP_400_BAD_REQUEST)

    open_count = _requests_for(student).filter(
        status__in=BookRequest.OPEN_STATUSES).count()
    if open_count >= MAX_OPEN_PER_STUDENT:
        return Response(
            {'detail': "You already have %d books requested or borrowed, which "
                       "is the limit." % open_count},
            status=status.HTTP_400_BAD_REQUEST)

    try:
        # Inside a savepoint: a constraint violation must not poison the
        # surrounding transaction, since we go on to render a response.
        with transaction.atomic():
            req = BookRequest.objects.create(
                student=student, book=book,
                student_note=(request.data.get('note') or '').strip())
    except IntegrityError:
        # The partial unique constraint — they already have this one open.
        return Response(
            {'detail': "You already have an open request for this book."},
            status=status.HTTP_400_BAD_REQUEST)

    return Response(book_request_dict(req), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsStudent])
def cancel(request, request_id):
    """Withdraw a request the librarian hasn't acted on yet."""
    student = get_object_or_404(Student, admin=request.user)
    req = get_object_or_404(BookRequest, id=request_id, student=student)
    if req.status != BookRequest.PENDING:
        return Response(
            {'detail': "Only a request still awaiting a decision can be cancelled."},
            status=status.HTTP_400_BAD_REQUEST)
    req.status = BookRequest.CANCELLED
    req.decided_at = timezone.now()
    req.save()
    return Response(book_request_dict(req))


@api_view(['POST'])
@permission_classes([IsStudent])
def request_renewal(request, request_id):
    """Ask to keep a borrowed book a week longer.

    Refused in three cases, each for its own reason: the book is not actually
    on loan; it has already been renewed once (the rule is one extension per
    loan — return it and request it again); or it is already overdue, at
    which point what is owed is the book and the fine, not an extension.
    """
    student = get_object_or_404(Student, admin=request.user)
    req = get_object_or_404(
        BookRequest.objects.select_related('book'), id=request_id, student=student)

    if req.status != BookRequest.ISSUED:
        return Response({'detail': "Only a book you currently have out can be renewed."},
                        status=status.HTTP_400_BAD_REQUEST)
    if req.renewal_state != BookRequest.RENEWAL_NONE:
        already = (
            "\"%s\" has already been renewed once. Return it, then request it "
            "again if you still need it." % req.book.name
            if req.renewal_state == BookRequest.RENEWAL_GRANTED else
            "You have already asked to renew \"%s\"." % req.book.name)
        return Response({'detail': already}, status=status.HTTP_400_BAD_REQUEST)
    if req.days_overdue:
        return Response(
            {'detail': "\"%s\" is already %d day(s) overdue, so it can't be "
                       "renewed. Please return it — a fine of Rs. %d per day "
                       "is running." % (req.book.name, req.days_overdue, FINE_PER_DAY)},
            status=status.HTTP_400_BAD_REQUEST)

    req.renewal_state = BookRequest.RENEWAL_REQUESTED
    req.renewal_requested_at = timezone.now()
    req.renewal_reason = (request.data.get('reason') or '').strip()
    req.save()
    return Response(book_request_dict(req))


@api_view(['GET'])
@permission_classes([IsStudent])
def my_fines(request):
    """The student's own fine receipts — their copy of the cash record."""
    student = get_object_or_404(Student, admin=request.user)
    records = LibraryFine.objects.filter(student=student).select_related(
        'request__book', 'collected_by__admin')
    return Response([library_fine_dict(f) for f in records])


# --------------------------------------------------------------------------
# Librarian side
# --------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsLibrarian])
def request_list(request):
    """The queue. `?status=` filters to one state; the default is everything
    still in flight, newest first."""
    requests = BookRequest.objects.select_related(
        'book', 'student__admin', 'student__course', 'decided_by__admin')
    wanted = request.query_params.get('status')
    if wanted:
        requests = requests.filter(status=wanted)
    query = (request.query_params.get('q') or '').strip()
    if query:
        requests = requests.filter(
            Q(book__name__icontains=query)
            | Q(student__admin__first_name__icontains=query)
            | Q(student__admin__last_name__icontains=query)
            | Q(student__roll_number__icontains=query))
    return Response([book_request_dict(r, for_librarian=True) for r in requests])


@api_view(['GET'])
@permission_classes([IsLibrarian])
def loans(request):
    """Books currently out, overdue ones first — the desk's working list."""
    issued = BookRequest.objects.filter(
        status=BookRequest.ISSUED).select_related(
        'book', 'student__admin', 'student__course')
    rows = [book_request_dict(r, for_librarian=True) for r in issued]
    rows.sort(key=lambda r: (-r['days_overdue'], r['due_date'] or ''))
    return Response(rows)


@api_view(['POST'])
@permission_classes([IsLibrarian])
def approve(request, request_id):
    """Allow the borrowing. Reserves a copy — the student collects it later."""
    librarian = get_object_or_404(Librarian, admin=request.user)
    with transaction.atomic():
        req = get_object_or_404(
            BookRequest.objects.select_for_update(), id=request_id)
        if req.status != BookRequest.PENDING:
            return Response(
                {'detail': "This request has already been decided."},
                status=status.HTTP_400_BAD_REQUEST)
        # Locked and re-read, because the free copy this request was queued
        # against may have gone to someone else in the meantime.
        book = Book.objects.select_for_update().get(pk=req.book_id)
        if book.available_copies < 1:
            return Response(
                {'detail': "Every copy of \"%s\" is out. Reject the request or "
                           "wait for a return." % book.name},
                status=status.HTTP_400_BAD_REQUEST)
        req.status = BookRequest.APPROVED
        req.decided_at = timezone.now()
        req.decided_by = librarian
        req.librarian_note = (request.data.get('note') or '').strip()
        req.save()

    _notify(req.student,
            "Your request to borrow \"%s\" was approved. Collect it from the "
            "library." % req.book.name)
    return Response(book_request_dict(req, for_librarian=True))


@api_view(['POST'])
@permission_classes([IsLibrarian])
def reject(request, request_id):
    """Turn a request down — either at the decision, or later when an approved
    copy was never collected."""
    librarian = get_object_or_404(Librarian, admin=request.user)
    req = get_object_or_404(BookRequest, id=request_id)
    if req.status not in (BookRequest.PENDING, BookRequest.APPROVED):
        return Response(
            {'detail': "Only a pending or uncollected request can be rejected."},
            status=status.HTTP_400_BAD_REQUEST)
    reason = (request.data.get('reason') or '').strip()
    if not reason:
        return Response({'reason': ['Please say why, so the student knows.']},
                        status=status.HTTP_400_BAD_REQUEST)
    req.status = BookRequest.REJECTED
    req.decided_at = timezone.now()
    req.decided_by = librarian
    req.librarian_note = reason
    req.save()

    _notify(req.student,
            "Your request to borrow \"%s\" was declined: %s"
            % (req.book.name, reason))
    return Response(book_request_dict(req, for_librarian=True))


@api_view(['POST'])
@permission_classes([IsLibrarian])
def issue(request, request_id):
    """The student collected the book. This is where the loan clock starts."""
    req = get_object_or_404(BookRequest, id=request_id)
    if req.status != BookRequest.APPROVED:
        return Response(
            {'detail': "Only an approved request can be handed over."},
            status=status.HTTP_400_BAD_REQUEST)
    req.status = BookRequest.ISSUED
    req.issued_date = date.today()
    req.due_date = req.issued_date + timedelta(days=LOAN_PERIOD_DAYS)
    req.save()

    _notify(req.student,
            "You borrowed \"%s\". Please return it by %s."
            % (req.book.name, req.due_date.strftime('%b. %d, %Y')))
    return Response(book_request_dict(req, for_librarian=True))


@api_view(['POST'])
@permission_classes([IsLibrarian])
def mark_returned(request, request_id):
    """The book is back on the shelf; whatever fine had accrued is frozen."""
    req = get_object_or_404(BookRequest, id=request_id)
    if req.status != BookRequest.ISSUED:
        return Response({'detail': "This book is not currently on loan."},
                        status=status.HTTP_400_BAD_REQUEST)
    req.returned_date = date.today()
    req.status = BookRequest.RETURNED
    req.save()

    message = "You returned \"%s\". Thank you." % req.book.name
    if req.fine:
        message = ("You returned \"%s\" %d day(s) late. Fine due: Rs. %d — "
                   "please pay it in cash at the library desk."
                   % (req.book.name, req.days_late, req.fine))
    _notify(req.student, message)
    return Response(book_request_dict(req, for_librarian=True))


# --------------------------------------------------------------------------
# Renewal decisions
# --------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsLibrarian])
def approve_renewal(request, request_id):
    """Grant the extension: the due date moves out by one week."""
    librarian = get_object_or_404(Librarian, admin=request.user)
    with transaction.atomic():
        req = get_object_or_404(
            BookRequest.objects.select_for_update().select_related('book'),
            id=request_id)
        if req.renewal_state != BookRequest.RENEWAL_REQUESTED:
            return Response(
                {'detail': "There is no renewal request waiting on this loan."},
                status=status.HTTP_400_BAD_REQUEST)
        if req.status != BookRequest.ISSUED:
            return Response({'detail': "This book is not currently on loan."},
                            status=status.HTTP_400_BAD_REQUEST)

        req.due_date_before_renewal = req.due_date
        # Extended from the existing due date, not from today: a renewal adds
        # a week to the loan, it does not restart it from the moment the
        # librarian happens to get round to clicking approve.
        req.due_date = req.due_date + timedelta(days=RENEWAL_PERIOD_DAYS)
        req.renewal_state = BookRequest.RENEWAL_GRANTED
        req.renewal_decided_at = timezone.now()
        req.renewal_decided_by = librarian
        req.renewal_librarian_note = (request.data.get('note') or '').strip()
        # The new due date deserves its own reminder.
        req.reminder_sent_on = None
        req.save()

    _notify(req.student,
            "Your renewal of \"%s\" was approved. It is now due on %s. This "
            "loan can't be renewed again — return it and request it afresh if "
            "you need longer." % (
                req.book.name, req.due_date.strftime('%b. %d, %Y')))
    return Response(book_request_dict(req, for_librarian=True))


@api_view(['POST'])
@permission_classes([IsLibrarian])
def reject_renewal(request, request_id):
    """Turn the extension down; the original due date stands."""
    librarian = get_object_or_404(Librarian, admin=request.user)
    req = get_object_or_404(
        BookRequest.objects.select_related('book'), id=request_id)
    if req.renewal_state != BookRequest.RENEWAL_REQUESTED:
        return Response(
            {'detail': "There is no renewal request waiting on this loan."},
            status=status.HTTP_400_BAD_REQUEST)
    reason = (request.data.get('reason') or '').strip()
    if not reason:
        return Response({'reason': ['Please say why, so the student knows.']},
                        status=status.HTTP_400_BAD_REQUEST)

    req.renewal_state = BookRequest.RENEWAL_DECLINED
    req.renewal_decided_at = timezone.now()
    req.renewal_decided_by = librarian
    req.renewal_librarian_note = reason
    req.save()

    _notify(req.student,
            "Your renewal of \"%s\" was declined: %s. It is still due on %s."
            % (req.book.name, reason, req.due_date.strftime('%b. %d, %Y')))
    return Response(book_request_dict(req, for_librarian=True))


# --------------------------------------------------------------------------
# Fines — cash taken at the desk, recorded once and never edited
# --------------------------------------------------------------------------

def _settle(request, request_id, kind):
    """Shared body of collect/waive: both write one LibraryFine receipt."""
    librarian = get_object_or_404(Librarian, admin=request.user)
    note = (request.data.get('note') or '').strip()
    if kind == LibraryFine.WAIVED and not note:
        return Response(
            {'note': ['A waived fine needs a reason on the record.']},
            status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        req = get_object_or_404(
            BookRequest.objects.select_for_update().select_related(
                'book', 'student__admin'), id=request_id)
        if req.status != BookRequest.RETURNED:
            return Response(
                {'detail': "Settle the fine when the book comes back — until "
                           "then the amount is still growing."},
                status=status.HTTP_400_BAD_REQUEST)
        if not req.fine:
            return Response({'detail': "There is no fine on this loan."},
                            status=status.HTTP_400_BAD_REQUEST)
        if req.fine_settled:
            return Response(
                {'detail': "This fine has already been recorded as %s."
                           % req.fine_records.first().get_kind_display().lower()},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            record = LibraryFine.objects.create(
                request=req,
                student=req.student,
                receipt_no=LibraryFine.next_receipt_no(),
                kind=kind,
                amount=req.fine,
                days_late=req.days_late,
                rate_per_day=FINE_PER_DAY,
                collected_by=librarian,
                collected_by_name=str(librarian),
                note=note)
        except IntegrityError:
            # Two desks settling the same loan at once; the constraint caught
            # the second one.
            return Response({'detail': "This fine has already been recorded."},
                            status=status.HTTP_400_BAD_REQUEST)

    if kind == LibraryFine.PAID:
        _notify(req.student,
                "Library fine of Rs. %d for \"%s\" received in cash. "
                "Receipt %s." % (record.amount, req.book.name, record.receipt_no))
    else:
        _notify(req.student,
                "Your library fine of Rs. %d for \"%s\" was waived: %s. "
                "Receipt %s." % (record.amount, req.book.name, note,
                                 record.receipt_no))
    return Response(library_fine_dict(record), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsLibrarian])
def collect_fine(request, request_id):
    """Record cash taken over the counter. Writes a permanent receipt."""
    return _settle(request, request_id, LibraryFine.PAID)


@api_view(['POST'])
@permission_classes([IsLibrarian])
def waive_fine(request, request_id):
    """Write the fine off. Still a receipt — the ledger has to explain the
    gap as much as it explains the cash."""
    return _settle(request, request_id, LibraryFine.WAIVED)


@api_view(['GET'])
@permission_classes([IsLibrarian])
def fine_records(request):
    """The desk's cash book: every fine ever settled, newest first."""
    records = LibraryFine.objects.select_related(
        'request__book', 'student__admin', 'student__course',
        'collected_by__admin')
    query = (request.query_params.get('q') or '').strip()
    if query:
        records = records.filter(
            Q(receipt_no__icontains=query)
            | Q(request__book__name__icontains=query)
            | Q(student__admin__first_name__icontains=query)
            | Q(student__admin__last_name__icontains=query)
            | Q(student__roll_number__icontains=query))
    rows = [library_fine_dict(f, for_librarian=True) for f in records]
    return Response({
        'records': rows,
        'total_collected': sum(
            r['amount'] for r in rows if r['kind'] == LibraryFine.PAID),
        'total_waived': sum(
            r['amount'] for r in rows if r['kind'] == LibraryFine.WAIVED),
    })


@api_view(['GET'])
@permission_classes([IsLibrarian])
def unsettled_fines(request):
    """Returned loans that came back late and haven't been paid up yet."""
    late = BookRequest.objects.filter(
        status=BookRequest.RETURNED,
        returned_date__gt=F('due_date'),
        fine_records__isnull=True,
    ).select_related('book', 'student__admin', 'student__course')
    return Response([book_request_dict(r, for_librarian=True) for r in late])


# --------------------------------------------------------------------------
# Due-date reminders
# --------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsLibrarian])
def send_reminders(request):
    """Run the due-soon sweep by hand.

    The same code the `send_due_reminders` management command runs, exposed
    so the desk can fire it without waiting for the scheduled job — and
    idempotent, so pressing it twice sends nothing the second time.
    """
    result = send_due_soon_reminders()
    return Response(result)
