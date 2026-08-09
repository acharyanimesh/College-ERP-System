"""Bank-deposit slips: the student's claim, and the office's verdict on it.

The third way money reaches the college, after the counter and (eventually)
the gateway. A student pays into the college's bank account, photographs the
slip and uploads it; nothing has been paid as far as the ledger is concerned
until somebody at the accounts office has put that image beside the bank
statement and agreed.

That two-step shape is the whole point of the module. A DepositSlip is
evidence and moves through states; a FeePayment is a receipt and never moves.
Verification is the moment one becomes the other, and it goes through
payments.write_receipt so a slip-shaped receipt and a cash-shaped receipt are
the same row in the same ledger.

This is also the only place in the system where a file arrives from outside
the staffroom, so what may be uploaded is deliberately narrow.
"""
import os
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (ZERO, Accountant, DepositSlip, FeeInvoice, FeePayment,
                      NotificationStudent, Student)
from .payments import notify_payment, payment_refusal, write_receipt
from .permissions import IsAccountant, IsAccountantOrAdmin, IsStudent
from .serializers import deposit_slip_dict, fee_payment_dict

CENTS = Decimal('0.01')

# A photo of a paper slip or the bank's own PDF, and nothing else. Checked by
# extension AND by the content type the browser declared: neither is proof on
# its own, but between them they stop the ordinary accidents, and the file is
# never executed or served back as HTML.
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.pdf')
ALLOWED_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp',
                         'application/pdf')
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _bad(field, message):
    return Response({field: [message]}, status=status.HTTP_400_BAD_REQUEST)


def _money(value):
    try:
        return Decimal(str(value).strip()).quantize(CENTS)
    except (InvalidOperation, AttributeError, TypeError, ValueError):
        raise ValueError("not an amount")


def _check_upload(upload):
    """What is wrong with this file, or None. Size first, because a rejected
    50 MB upload has already cost the student their data either way."""
    if upload is None:
        return "Attach a photo or PDF of the deposit slip."
    if upload.size > MAX_UPLOAD_BYTES:
        return ("That file is larger than 5 MB. A photo of the slip taken on "
                "a phone is well under that.")
    if os.path.splitext(upload.name)[1].lower() not in ALLOWED_EXTENSIONS:
        return "Upload a JPG, PNG, WEBP or PDF."
    if (upload.content_type or '') not in ALLOWED_CONTENT_TYPES:
        return "That doesn't look like an image or a PDF."
    return None


# ------------------------------------------------------------ Student side

@api_view(['GET'])
@permission_classes([IsStudent])
def my_slips(request):
    """Every slip this student has submitted, newest first.

    Rejected ones stay in the list: the reason they were rejected is usually
    the only thing that tells the student what to do next.
    """
    student = get_object_or_404(Student, admin=request.user)
    slips = student.deposit_slips.select_related('invoice', 'payment')
    return Response([deposit_slip_dict(s) for s in slips])


@api_view(['POST'])
@permission_classes([IsStudent])
def submit_slip(request, invoice_id):
    """Claim to have paid a bill into the college's bank account.

    Scoped to the student's own bills, so somebody else's invoice is a 404
    rather than a refusal that confirms it exists.
    """
    student = get_object_or_404(Student, admin=request.user)
    invoice = get_object_or_404(
        FeeInvoice.objects.prefetch_related('lines', 'adjustments',
                                            'payments'),
        id=invoice_id, student=student)

    if invoice.is_cancelled:
        return Response(
            {'detail': "This invoice was withdrawn, so there is nothing to "
                       "pay against it."},
            status=status.HTTP_400_BAD_REQUEST)
    balance = invoice.balance
    if balance <= ZERO:
        return Response({'detail': "This bill is already settled."},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = _money(request.data.get('amount'))
    except ValueError:
        return _bad('amount', "Enter the amount you deposited.")
    if amount <= ZERO:
        return _bad('amount', "A deposit has to be more than zero.")
    if amount > balance:
        return _bad('amount', "That is more than the Rs. %s still owed on "
                              "this bill." % balance)

    bank_name = (request.data.get('bank_name') or '').strip()
    if not bank_name:
        return _bad('bank_name', "Which bank did you deposit it into?")
    reference = (request.data.get('reference') or '').strip()
    if not reference:
        return _bad('reference', "Enter the voucher or deposit slip number. "
                                 "This is what the office matches against "
                                 "the bank statement.")

    deposited_on, error = _deposited_on(request.data.get('deposited_on'))
    if error:
        return error

    upload = request.FILES.get('image')
    problem = _check_upload(upload)
    if problem:
        return _bad('image', problem)

    try:
        # Wrapped so the IntegrityError below is caught at a savepoint —
        # without one it poisons the whole request's transaction, and the
        # session write at the end of it fails too.
        with transaction.atomic():
            slip = DepositSlip.objects.create(
                invoice=invoice,
                student=student,
                amount=amount,
                deposited_on=deposited_on,
                bank_name=bank_name,
                reference=reference,
                image=upload,
                note=(request.data.get('note') or '').strip())
    except IntegrityError:
        # The unique constraint on (invoice, reference) for live rows. Almost
        # always the upload button pressed twice, so say so plainly.
        return Response(
            {'detail': "You've already submitted slip %s against this bill. "
                       "The office will get to it." % reference},
            status=status.HTTP_400_BAD_REQUEST)

    return Response(deposit_slip_dict(slip), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsStudent])
def withdraw_slip(request, slip_id):
    """Take back a slip the office hasn't looked at yet.

    Only while it is pending: once it has been verified it is attached to a
    receipt, and once rejected the reason is a record of what the student was
    told.
    """
    student = get_object_or_404(Student, admin=request.user)
    slip = get_object_or_404(DepositSlip, id=slip_id, student=student)
    if not slip.is_pending:
        return Response(
            {'detail': "This slip has already been %s, so it can't be "
                       "withdrawn." % slip.get_status_display().lower()},
            status=status.HTTP_400_BAD_REQUEST)
    slip.image.delete(save=False)
    slip.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _deposited_on(value):
    """Parse the deposit date. Required, and the future is refused — this
    records something the bank has already done."""
    if not value:
        return None, _bad('deposited_on', "When did you deposit it?")
    try:
        deposited = date_cls.fromisoformat(str(value)[:10])
    except ValueError:
        return None, _bad('deposited_on', "Enter a valid date.")
    if deposited > date_cls.today():
        return None, _bad('deposited_on', "That date is in the future.")
    return deposited, None


# ------------------------------------------------------------- Office side

@api_view(['GET'])
@permission_classes([IsAccountantOrAdmin])
def slip_queue(request):
    """Slips waiting on the office, oldest claim first.

    Pending by default: this is a work queue, and the whole job is to empty
    it. `status` opens the history for a student asking what happened to one.
    """
    # The invoice's lines, adjustments and payments come along because the
    # office view reports its balance, and that walks all three — without the
    # prefetch this is three extra queries per row on the page.
    slips = DepositSlip.objects.select_related(
        'student__admin', 'student__course', 'invoice', 'payment'
    ).prefetch_related('invoice__lines', 'invoice__adjustments',
                       'invoice__payments')

    wanted = request.query_params.get('status') or DepositSlip.PENDING
    if wanted != 'all':
        slips = slips.filter(status=wanted)

    query = (request.query_params.get('q') or '').strip()
    if query:
        slips = slips.filter(
            Q(reference__icontains=query)
            | Q(bank_name__icontains=query)
            | Q(invoice__number__icontains=query)
            | Q(student__admin__first_name__icontains=query)
            | Q(student__admin__last_name__icontains=query)
            | Q(student__roll_number__icontains=query))

    if wanted == DepositSlip.PENDING:
        slips = slips.order_by('created_at')

    return Response({
        'slips': [deposit_slip_dict(s, for_office=True) for s in slips[:200]],
        'pending_count': DepositSlip.objects.filter(
            status=DepositSlip.PENDING).count(),
    })


@api_view(['POST'])
@permission_classes([IsAccountant])
def verify_slip(request, slip_id):
    """Agree that the money is in the bank, and turn the claim into a receipt.

    The amount credited is the accountant's, not the student's: the desk is
    looking at the statement and the student is looking at a photograph, and
    when the two disagree the statement is right. It still cannot exceed what
    the bill owes — payment_refusal is re-checked here against a re-read
    invoice, because a slip can sit in the queue for days while the counter
    takes money against the same bill.
    """
    accountant = get_object_or_404(Accountant, admin=request.user)

    amount_given = request.data.get('amount')
    with transaction.atomic():
        slip = get_object_or_404(
            DepositSlip.objects.select_for_update().select_related('student'),
            id=slip_id)
        if not slip.is_pending:
            return Response(
                {'detail': "This slip has already been %s."
                           % slip.get_status_display().lower()},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = (_money(amount_given) if amount_given not in (None, '')
                      else slip.amount)
        except ValueError:
            return _bad('amount', "Enter the amount the bank actually shows.")
        if amount <= ZERO:
            return _bad('amount', "A payment has to be more than zero.")

        invoice = FeeInvoice.objects.select_for_update().select_related(
            'student__admin').get(pk=slip.invoice_id)
        refusal = payment_refusal(invoice, amount)
        if refusal:
            field, message = refusal
            # Deliberately not auto-rejecting: the money may well be in the
            # bank, and what to do about a bill that has since been settled
            # or withdrawn is a judgement for the office, not for this view.
            return Response(
                {field: message if field == 'detail' else [message]},
                status=status.HTTP_400_BAD_REQUEST)

        note = ("Bank deposit verified from slip %s (%s), deposited %s."
                % (slip.reference, slip.bank_name, slip.deposited_on))
        extra = (request.data.get('note') or '').strip()
        if extra:
            note = "%s %s" % (note, extra)

        try:
            # Savepoint, so a clashing receipt number doesn't take the
            # enclosing transaction down with it.
            with transaction.atomic():
                payment = write_receipt(
                    invoice, amount, FeePayment.BANK, slip.reference,
                    slip.deposited_on, accountant, note=note)
        except IntegrityError:
            return Response(
                {'detail': "That receipt number was just taken by another "
                           "desk. Try again."},
                status=status.HTTP_400_BAD_REQUEST)

        slip.status = DepositSlip.VERIFIED
        slip.payment = payment
        slip.reviewed_by = accountant
        slip.reviewed_by_name = str(accountant)
        slip.reviewed_at = timezone.now()
        slip.review_note = extra
        slip.save()

    notify_payment(payment, invoice,
                   lead="Fees: your bank deposit of Rs. %s against %s has "
                        "been verified")

    slip = DepositSlip.objects.select_related(
        'student__admin', 'student__course', 'invoice', 'payment').get(
        pk=slip.pk)
    return Response({
        'slip': deposit_slip_dict(slip, for_office=True),
        'payment': fee_payment_dict(payment, for_office=True),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAccountant])
def reject_slip(request, slip_id):
    """Turn a claim down, with a reason the student can act on.

    The reason is required and goes straight to the student. A slip the
    office cannot match is the one case in the fee system where somebody is
    told their money doesn't exist, and "rejected" on its own is not
    something anybody can do anything about.
    """
    accountant = get_object_or_404(Accountant, admin=request.user)
    reason = (request.data.get('reason') or '').strip()
    if not reason:
        return _bad('reason', "Say why, so the student knows what to fix — "
                              "the slip is unreadable, the reference doesn't "
                              "appear on the statement, and so on.")

    with transaction.atomic():
        slip = get_object_or_404(
            DepositSlip.objects.select_for_update().select_related(
                'student', 'invoice'), id=slip_id)
        if not slip.is_pending:
            return Response(
                {'detail': "This slip has already been %s."
                           % slip.get_status_display().lower()},
                status=status.HTTP_400_BAD_REQUEST)

        slip.status = DepositSlip.REJECTED
        slip.reviewed_by = accountant
        slip.reviewed_by_name = str(accountant)
        slip.reviewed_at = timezone.now()
        slip.review_note = reason
        slip.save()

    NotificationStudent.objects.create(
        student=slip.student,
        message=("Fees: the deposit slip %s you submitted against %s could "
                 "not be verified. %s" % (slip.reference, slip.invoice.number,
                                          reason)))

    slip = DepositSlip.objects.select_related(
        'student__admin', 'student__course', 'invoice', 'payment').get(
        pk=slip.pk)
    return Response(deposit_slip_dict(slip, for_office=True))
