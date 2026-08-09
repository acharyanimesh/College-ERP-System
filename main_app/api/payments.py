"""Taking money against a fee bill.

The counter half of the fee system — cash, cheque and bank deposits recorded
by the accounts office. The online gateway writes its receipts through
gateways.py instead, but into the same FeePayment table, so the ledger has one
shape however the money arrived.

Modelled on api/library.py's _settle: the receipt is written inside a
transaction that re-reads the bill first, because what a payment is allowed to
be depends on what is still owed, and that can change between the accountant
opening the screen and pressing the button.
"""
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..idgen import next_receipt_number
from ..models import (ZERO, Accountant, FeeInvoice, FeePayment,
                      NotificationStudent)
from .permissions import IsAccountant, IsAccountantOrAdmin
from .serializers import fee_invoice_dict, fee_payment_dict

CENTS = Decimal('0.01')

# What the counter is allowed to record. ONLINE is deliberately absent: an
# online payment exists only because a gateway confirmed it, and letting the
# desk type one in by hand would put an unverifiable row in the ledger next to
# the verified ones.
COUNTER_MODES = (FeePayment.CASH, FeePayment.CHEQUE, FeePayment.BANK)

# Modes where "which cheque? which deposit slip?" has to be answerable later.
REFERENCE_REQUIRED = (FeePayment.CHEQUE, FeePayment.BANK)


def _money(value):
    try:
        return Decimal(str(value).strip()).quantize(CENTS)
    except (InvalidOperation, AttributeError, TypeError, ValueError):
        raise ValueError("not an amount")


def payment_refusal(invoice, amount):
    """Why `invoice` cannot take `amount` right now, or None if it can.

    Shared by the counter and by deposit-slip verification, because the rules
    are a property of the bill and not of how the money arrived. Call it
    inside the transaction that writes the receipt, on a re-read invoice: the
    balance is what decides, and another desk may have moved it since.

    Returns (field, message) so the caller can put it where the form expects.
    """
    if invoice.is_cancelled:
        return ('detail', "This invoice was withdrawn, so there is nothing "
                          "to pay against it.")
    balance = invoice.balance
    if balance <= ZERO:
        return ('detail', "This bill is already settled.")
    if amount > balance:
        # Refused rather than accepted as a credit: an amount over the
        # balance is nearly always a typo, and the college has no concept
        # of a student account holding a surplus.
        return ('amount', "That is more than the Rs. %s still owed on this "
                          "bill." % balance)
    return None


def write_receipt(invoice, amount, mode, reference, received_on, accountant,
                  note="", attempt=None):
    """Write the receipt itself.

    The caller owns the transaction and has already cleared `payment_refusal`
    — this only does the part that must look identical however the money
    arrived, so that one ledger shape survives cash, slips and the gateway.
    """
    return FeePayment.objects.create(
        invoice=invoice,
        student=invoice.student,
        receipt_no=next_receipt_number(received_on),
        amount=amount,
        mode=mode,
        reference=reference,
        received_on=received_on,
        collected_by=accountant,
        collected_by_name=str(accountant) if accountant else "",
        note=note,
        attempt=attempt)


@api_view(['GET'])
@permission_classes([IsAccountantOrAdmin])
def collectable(request):
    """Bills with money still on them, for the counter's search box.

    Searchable by roll number, name or invoice number — whichever the student
    happens to say at the window.
    """
    invoices = FeeInvoice.objects.outstanding().select_related(
        'student__admin', 'student__course', 'course', 'session')

    query = (request.query_params.get('q') or '').strip()
    if query:
        invoices = invoices.filter(
            Q(number__icontains=query)
            | Q(student__admin__first_name__icontains=query)
            | Q(student__admin__last_name__icontains=query)
            | Q(student__roll_number__icontains=query))

    course = request.query_params.get('course')
    if course:
        invoices = invoices.filter(course_id=course)

    return Response([fee_invoice_dict(i, for_office=True)
                     for i in invoices[:100]])


@api_view(['POST'])
@permission_classes([IsAccountant])
def collect_payment(request, invoice_id):
    """Record money taken over the counter. Writes a permanent receipt.

    The receipt is append-only (see FeePayment): a mistake here is corrected
    by an offsetting adjustment on the bill, never by editing this row.
    """
    accountant = get_object_or_404(Accountant, admin=request.user)

    mode = request.data.get('mode') or FeePayment.CASH
    if mode not in COUNTER_MODES:
        return Response(
            {'mode': ["Record this as cash, cheque or bank deposit. An "
                      "online payment can only be created by the gateway "
                      "that confirmed it."]},
            status=status.HTTP_400_BAD_REQUEST)

    reference = (request.data.get('reference') or '').strip()
    if mode in REFERENCE_REQUIRED and not reference:
        return Response(
            {'reference': ["Record the cheque or deposit slip number — this "
                           "is what the bank statement gets matched against "
                           "later."]},
            status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = _money(request.data.get('amount'))
    except ValueError:
        return Response({'amount': ['Enter an amount.']},
                        status=status.HTTP_400_BAD_REQUEST)
    if amount <= ZERO:
        return Response({'amount': ['A payment has to be more than zero.']},
                        status=status.HTTP_400_BAD_REQUEST)

    received_on, error = _received_on(request.data.get('received_on'))
    if error:
        return error

    with transaction.atomic():
        # Re-read inside the transaction: the balance is what decides whether
        # this payment is allowed, and another desk may have taken money
        # since this screen was opened.
        invoice = get_object_or_404(
            FeeInvoice.objects.select_for_update().select_related(
                'student__admin'), id=invoice_id)

        refusal = payment_refusal(invoice, amount)
        if refusal:
            field, message = refusal
            return Response(
                {field: message if field == 'detail' else [message]},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            # Its own savepoint: catching an IntegrityError without one
            # leaves the surrounding transaction broken, and every later
            # query in this request — including the session write — dies
            # with it.
            with transaction.atomic():
                payment = write_receipt(
                    invoice, amount, mode, reference, received_on, accountant,
                    note=(request.data.get('note') or '').strip())
        except IntegrityError:
            return Response(
                {'detail': "That receipt number was just taken by another "
                           "desk. Try again."},
                status=status.HTTP_400_BAD_REQUEST)

    notify_payment(payment, invoice)

    invoice = FeeInvoice.objects.prefetch_related(
        'lines', 'adjustments', 'payments').get(pk=invoice.pk)
    return Response({
        'payment': fee_payment_dict(payment, for_office=True),
        'invoice': fee_invoice_dict(invoice, detail=True, for_office=True),
    }, status=status.HTTP_201_CREATED)


def _received_on(value):
    """Parse an optional received-on date. Defaults to today; the future is
    refused, because a receipt records something that has happened."""
    today = date_cls.today()
    if not value:
        return today, None
    try:
        received = date_cls.fromisoformat(str(value)[:10])
    except ValueError:
        return None, Response(
            {'received_on': ['Enter a valid date.']},
            status=status.HTTP_400_BAD_REQUEST)
    if received > today:
        return None, Response(
            {'received_on': ["A receipt can't be dated in the future."]},
            status=status.HTTP_400_BAD_REQUEST)
    return received, None


def notify_payment(payment, invoice, lead="Fees: Rs. %s received against %s"):
    """Tell the student their money landed, and what is left.

    Reads the balance back off the database rather than subtracting in
    Python, so the figure in the notification is the same one the bill will
    show when they open it.

    `lead` takes the amount and the invoice number, and lets the deposit-slip
    flow say what actually happened — "verified", not "received", since from
    the student's side the money left their hands days earlier.
    """
    remaining = FeeInvoice.objects.prefetch_related(
        'lines', 'adjustments', 'payments').get(pk=invoice.pk).balance
    tail = ("Nothing further is owed on this bill."
            if remaining <= ZERO else
            "Rs. %s is still outstanding." % remaining)
    NotificationStudent.objects.create(
        student=payment.student,
        message="%s (receipt %s). %s" % (
            lead % (payment.amount, invoice.number), payment.receipt_no, tail))


@api_view(['GET'])
@permission_classes([IsAccountantOrAdmin])
def payment_list(request):
    """The office's cash book: every fee receipt taken, newest first."""
    payments = FeePayment.objects.select_related(
        'student__admin', 'student__course', 'invoice')

    query = (request.query_params.get('q') or '').strip()
    if query:
        payments = payments.filter(
            Q(receipt_no__icontains=query)
            | Q(reference__icontains=query)
            | Q(invoice__number__icontains=query)
            | Q(student__admin__first_name__icontains=query)
            | Q(student__admin__last_name__icontains=query)
            | Q(student__roll_number__icontains=query))

    mode = request.query_params.get('mode')
    if mode:
        payments = payments.filter(mode=mode)
    on = request.query_params.get('on')
    if on:
        payments = payments.filter(received_on=on)

    rows = [fee_payment_dict(p, for_office=True) for p in payments[:300]]
    return Response({
        'payments': rows,
        'total': sum((row['amount'] for row in rows), ZERO),
    })


@api_view(['GET'])
def receipt(request, payment_id):
    """One receipt, for printing.

    Open to the office and to the student it belongs to — and to nobody else.
    The two callers get different routes through here on purpose: the
    student's is scoped by owner, so somebody else's receipt is a 404 rather
    than a refusal that confirms it exists. (Authentication itself is
    guaranteed by the project-wide IsAuthenticated default.)
    """
    student = getattr(request.user, 'student', None)
    if student is not None:
        payment = get_object_or_404(
            FeePayment.objects.select_related('invoice', 'student__admin'),
            id=payment_id, student=student)
        return Response(fee_payment_dict(payment))

    if not IsAccountantOrAdmin().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    payment = get_object_or_404(
        FeePayment.objects.select_related('invoice', 'student__admin'),
        id=payment_id)
    return Response(fee_payment_dict(payment, for_office=True))
