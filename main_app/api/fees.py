"""Fee heads, fee structures, and the invoice run.

The accounts office's side of billing. Everything that WRITES is behind
IsAccountant; the admin's oversight is read-only and comes in through
IsAccountantOrAdmin on the GET-only endpoints — see the Accountant model's
docstring for why that split exists at all.

The billing itself lives in main_app/fee_billing.py, not here, because the
promotion cascade raises bills too and both have to raise them the same way.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..fee_billing import (NothingToBill, add_adjustment, generate_invoices,
                           preview_invoice_run)
from ..models import (ZERO, Course, FeeAdjustment, FeeHead, FeeInvoice,
                      FeeStructure, FeeStructureItem, Session, Student)
from .permissions import IsAccountant, IsAccountantOrAdmin, IsStudent
from .serializers import (fee_head_dict, fee_invoice_dict, fee_payment_dict,
                          fee_structure_dict)

CENTS = Decimal('0.01')


def _money(value):
    """Parse a posted amount into a 2dp Decimal, or raise ValueError.

    Via str() rather than float(): float('47500.10') is not 47500.10, and a
    ledger is the last place to let that in.
    """
    try:
        return Decimal(str(value).strip()).quantize(CENTS)
    except (InvalidOperation, AttributeError, TypeError, ValueError):
        raise ValueError("not an amount")


def _accountant(request):
    """The Accountant profile acting, or None when an admin is just looking."""
    return getattr(request.user, 'accountant', None)


def _student_brief(student):
    user = student.admin
    return {
        'id': student.id,
        'name': ("%s %s" % (user.first_name, user.last_name)).strip(),
        'roll_number': student.roll_number or '',
        'email': user.email,
    }


# --------------------------------------------------------------- Fee heads

@api_view(['GET', 'POST'])
@permission_classes([IsAccountantOrAdmin])
def head_list(request):
    if request.method == 'GET':
        return Response([fee_head_dict(h) for h in FeeHead.objects.all()])

    if not IsAccountant().has_permission(request, None):
        return Response({'detail': "Only the accounts office can change the "
                                   "fee heads."},
                        status=status.HTTP_403_FORBIDDEN)
    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'name': ['This field is required.']},
                        status=status.HTTP_400_BAD_REQUEST)
    if FeeHead.objects.filter(name__iexact=name).exists():
        return Response({'name': ['A fee head by that name already exists.']},
                        status=status.HTTP_400_BAD_REQUEST)
    head = FeeHead.objects.create(
        name=name,
        code=(request.data.get('code') or '').strip(),
        description=(request.data.get('description') or '').strip(),
        recurring=bool(request.data.get('recurring', True)),
        refundable=bool(request.data.get('refundable', False)))
    return Response(fee_head_dict(head), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAccountant])
def head_item(request, head_id):
    head = get_object_or_404(FeeHead, id=head_id)
    if request.method == 'GET':
        return Response(fee_head_dict(head))

    if request.method == 'DELETE':
        # PROTECT on FeeStructureItem.head and FeeInvoiceLine.head: a head
        # that has been billed under stays, or the bills stop explaining
        # themselves.
        try:
            head.delete()
        except Exception:
            return Response(
                {'detail': "This fee head is used by a fee structure or has "
                           "already been billed, so it can't be deleted. "
                           "Remove it from the structures instead."},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'name': ['This field is required.']},
                        status=status.HTTP_400_BAD_REQUEST)
    if FeeHead.objects.exclude(pk=head.pk).filter(name__iexact=name).exists():
        return Response({'name': ['A fee head by that name already exists.']},
                        status=status.HTTP_400_BAD_REQUEST)
    head.name = name
    head.code = (request.data.get('code') or '').strip()
    head.description = (request.data.get('description') or '').strip()
    head.recurring = bool(request.data.get('recurring', head.recurring))
    head.refundable = bool(request.data.get('refundable', head.refundable))
    head.save()
    return Response(fee_head_dict(head))


# ---------------------------------------------------------- Fee structures

@api_view(['GET', 'POST'])
@permission_classes([IsAccountantOrAdmin])
def structure_list(request):
    if request.method == 'GET':
        structures = FeeStructure.objects.select_related(
            'course', 'session').prefetch_related('items__head')
        for param, field in (('course', 'course_id'),
                             ('session', 'session_id'),
                             ('semester', 'semester')):
            value = request.query_params.get(param)
            if value:
                structures = structures.filter(**{field: value})
        return Response([fee_structure_dict(s) for s in structures])

    if not IsAccountant().has_permission(request, None):
        return Response({'detail': "Only the accounts office can write fee "
                                   "structures."},
                        status=status.HTTP_403_FORBIDDEN)
    return _save_structure(request, None)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAccountantOrAdmin])
def structure_item(request, structure_id):
    structure = get_object_or_404(
        FeeStructure.objects.prefetch_related('items__head'), id=structure_id)
    if request.method == 'GET':
        return Response(fee_structure_dict(structure))

    if not IsAccountant().has_permission(request, None):
        return Response({'detail': "Only the accounts office can change fee "
                                   "structures."},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        if FeeInvoice.objects.filter(structure=structure).exists():
            # Not PROTECT (the FK is SET_NULL so a deleted template doesn't
            # take bills with it), but a structure that has been billed from
            # is still the only record of what that run charged.
            return Response(
                {'detail': "Invoices have already been raised from this "
                           "structure, so it can't be deleted. Edit it "
                           "instead — bills already issued keep the amounts "
                           "they were raised with."},
                status=status.HTTP_400_BAD_REQUEST)
        structure.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return _save_structure(request, structure)


def _save_structure(request, structure):
    """Create or replace a structure and its line items in one go.

    The items are replaced wholesale rather than diffed: a structure is a
    short list somebody edits as a whole, and 'these are the heads now' is
    both simpler to reason about and impossible to get half-applied.
    """
    data = request.data
    errors = {}
    course_id = data.get('course')
    session_id = data.get('session')
    semester = data.get('semester')
    for field, value in (('course', course_id), ('session', session_id),
                         ('semester', semester)):
        if not value:
            errors[field] = ['This field is required.']
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    course = get_object_or_404(Course, id=course_id)
    session = get_object_or_404(Session, id=session_id)

    clash = FeeStructure.objects.filter(
        course=course, session=session, semester=semester)
    if structure is not None:
        clash = clash.exclude(pk=structure.pk)
    if clash.exists():
        return Response(
            {'detail': "A fee structure already exists for %s, Semester %s in "
                       "%s. Edit that one instead." % (
                           course.short_name, semester, session)},
            status=status.HTTP_400_BAD_REQUEST)

    rows, item_errors = _clean_items(data.get('items') or [])
    if item_errors:
        return Response({'items': item_errors},
                        status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        if structure is None:
            structure = FeeStructure(course=course, session=session,
                                     semester=semester)
        else:
            structure.course, structure.session = course, session
            structure.semester = semester
        structure.due_days = int(data.get('due_days') or 30)
        try:
            structure.late_fine_per_day = _money(
                data.get('late_fine_per_day') or 0)
        except ValueError:
            structure.late_fine_per_day = 0
        structure.note = (data.get('note') or '').strip()
        structure.save()

        structure.items.all().delete()
        FeeStructureItem.objects.bulk_create([
            FeeStructureItem(structure=structure, head_id=head_id,
                             amount=amount)
            for head_id, amount in rows])

    structure = FeeStructure.objects.prefetch_related('items__head').get(
        pk=structure.pk)
    return Response(fee_structure_dict(structure),
                    status=status.HTTP_201_CREATED if request.method == 'POST'
                    else status.HTTP_200_OK)


def _clean_items(rows):
    """Validate the [{head, amount}] list. Returns (cleaned, errors)."""
    cleaned, errors = [], []
    seen = set()
    valid_heads = set(FeeHead.objects.values_list('id', flat=True))
    for index, row in enumerate(rows):
        head_id = row.get('head')
        amount = row.get('amount')
        if not head_id:
            errors.append("Row %d: pick a fee head." % (index + 1))
            continue
        head_id = int(head_id)
        if head_id not in valid_heads:
            errors.append("Row %d: that fee head no longer exists." % (index + 1))
            continue
        if head_id in seen:
            errors.append("Row %d: that fee head is already on this structure."
                          % (index + 1))
            continue
        try:
            amount = _money(amount)
        except ValueError:
            errors.append("Row %d: enter an amount." % (index + 1))
            continue
        if amount < 0:
            errors.append("Row %d: an amount can't be negative. Use a "
                          "scholarship or discount on the student's bill "
                          "instead." % (index + 1))
            continue
        seen.add(head_id)
        cleaned.append((head_id, amount))
    if not cleaned and not errors:
        errors.append("Add at least one fee head.")
    return cleaned, errors


@api_view(['POST'])
@permission_classes([IsAccountant])
def clone_structure(request, structure_id):
    """Copy a structure onto another session (and optionally semester).

    Nobody wants to retype eight heads for six courses every intake, and
    retyping is where the amounts drift.
    """
    source = get_object_or_404(
        FeeStructure.objects.prefetch_related('items'), id=structure_id)
    session = get_object_or_404(Session, id=request.data.get('session'))
    semester = request.data.get('semester') or source.semester

    if FeeStructure.objects.filter(
            course=source.course, session=session, semester=semester).exists():
        return Response(
            {'detail': "A fee structure already exists for %s, Semester %s in "
                       "%s." % (source.course.short_name, semester, session)},
            status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        clone = FeeStructure.objects.create(
            course=source.course, session=session, semester=semester,
            due_days=source.due_days,
            late_fine_per_day=source.late_fine_per_day, note=source.note)
        FeeStructureItem.objects.bulk_create([
            FeeStructureItem(structure=clone, head_id=item.head_id,
                             amount=item.amount)
            for item in source.items.all()])

    clone = FeeStructure.objects.prefetch_related('items__head').get(pk=clone.pk)
    return Response(fee_structure_dict(clone), status=status.HTTP_201_CREATED)


# ----------------------------------------------------------- Invoice runs

@api_view(['GET'])
@permission_classes([IsAccountantOrAdmin])
def invoice_run_preview(request):
    """What billing this class would do, before it does it."""
    course, session, semester, error = _run_target(request.query_params)
    if error:
        return error

    preview = preview_invoice_run(course, session, semester)
    structure = preview['structure']
    return Response({
        'course_name': course.short_name,
        'session_name': str(session),
        'semester': semester,
        'structure': fee_structure_dict(structure) if structure else None,
        'to_bill': [_student_brief(s) for s in preview['to_bill']],
        'already_billed': [_student_brief(s) for s in preview['already_billed']],
    })


@api_view(['POST'])
@permission_classes([IsAccountant])
def invoice_run(request):
    """Raise the bills. Safe to press twice — see fee_billing."""
    course, session, semester, error = _run_target(request.data)
    if error:
        return error

    try:
        result = generate_invoices(
            course, session, semester, issued_by=_accountant(request))
    except NothingToBill as e:
        return Response({'detail': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)

    created, skipped = len(result['created']), result['skipped']
    bits = ["%d invoice%s raised" % (created, '' if created == 1 else 's')]
    if skipped:
        bits.append("%d student%s already billed for this semester" % (
            skipped, ' was' if skipped == 1 else 's were'))
    return Response({
        'created': created,
        'skipped': skipped,
        'detail': "; ".join(bits) + ".",
        'invoices': [fee_invoice_dict(i, for_office=True)
                     for i in result['created']],
    }, status=status.HTTP_201_CREATED)


def _run_target(params):
    """Resolve (course, session, semester) off a query string or body."""
    course_id = params.get('course')
    session_id = params.get('session')
    semester = params.get('semester')
    if not (course_id and session_id and semester):
        return None, None, None, Response(
            {'detail': "Pick a course, session and semester."},
            status=status.HTTP_400_BAD_REQUEST)
    course = get_object_or_404(Course, id=course_id)
    session = get_object_or_404(Session, id=session_id)
    return course, session, int(semester), None


# --------------------------------------------------------------- Invoices

@api_view(['GET'])
@permission_classes([IsAccountantOrAdmin])
def invoice_list(request):
    """The office's invoice register, filterable and searchable."""
    # Pick the base queryset FIRST, then narrow it — overdue()/outstanding()
    # start from the manager, so choosing one after applying the course and
    # semester filters would silently throw those filters away.
    state = request.query_params.get('status')
    if state == FeeInvoice.OVERDUE:
        invoices = FeeInvoice.objects.overdue()
    elif state == 'outstanding':
        invoices = FeeInvoice.objects.outstanding()
    else:
        invoices = FeeInvoice.objects.with_totals()
    invoices = invoices.select_related(
        'student__admin', 'student__course', 'course', 'session')

    for param, field in (('course', 'course_id'), ('session', 'session_id'),
                         ('semester', 'semester'),
                         ('student', 'student_id')):
        value = request.query_params.get(param)
        if value:
            invoices = invoices.filter(**{field: value})

    query = (request.query_params.get('q') or '').strip()
    if query:
        invoices = invoices.filter(
            Q(number__icontains=query)
            | Q(student__admin__first_name__icontains=query)
            | Q(student__admin__last_name__icontains=query)
            | Q(student__roll_number__icontains=query))

    return Response([fee_invoice_dict(i, for_office=True)
                     for i in invoices[:300]])


@api_view(['GET'])
@permission_classes([IsAccountantOrAdmin])
def invoice_item(request, invoice_id):
    invoice = get_object_or_404(
        FeeInvoice.objects.select_related(
            'student__admin', 'course', 'session'
        ).prefetch_related('lines', 'adjustments', 'payments'),
        id=invoice_id)
    return Response(fee_invoice_dict(invoice, detail=True, for_office=True))


@api_view(['POST'])
@permission_classes([IsAccountant])
def cancel_invoice(request, invoice_id):
    """Withdraw a bill that should never have gone out.

    The row stays with its reason attached — a withdrawn charge is a thing
    that happened, not a thing to delete. A bill with money already on it
    can't be cancelled: that money would have nowhere to sit.
    """
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if invoice.is_cancelled:
        return Response({'detail': "This invoice is already cancelled."},
                        status=status.HTTP_400_BAD_REQUEST)
    if invoice.payments.exists():
        return Response(
            {'detail': "Payments have already been taken against this "
                       "invoice, so it can't be cancelled. Write an "
                       "adjustment instead."},
            status=status.HTTP_400_BAD_REQUEST)
    reason = (request.data.get('reason') or '').strip()
    if not reason:
        return Response({'reason': ['Say why this bill is being withdrawn.']},
                        status=status.HTTP_400_BAD_REQUEST)

    invoice.cancelled_at = timezone.now()
    invoice.cancelled_by = _accountant(request)
    invoice.cancel_reason = reason
    invoice.save(update_fields=['cancelled_at', 'cancelled_by',
                                'cancel_reason', 'updated_at'])
    return Response(fee_invoice_dict(invoice, detail=True, for_office=True))


# ------------------------------------------------------------ Adjustments

@api_view(['POST'])
@permission_classes([IsAccountant])
def adjust_invoice(request, invoice_id):
    """Put a scholarship, discount, waiver, late fine or correction on a bill.

    The amount is typed in as a plain positive number and the KIND decides
    which way it moves the bill — see fee_billing.signed_amount.
    """
    invoice = get_object_or_404(FeeInvoice, id=invoice_id)
    if invoice.is_cancelled:
        return Response({'detail': "This invoice has been cancelled."},
                        status=status.HTTP_400_BAD_REQUEST)

    kind = request.data.get('kind')
    if kind not in dict(FeeAdjustment.KIND_CHOICES):
        return Response({'kind': ['Pick what kind of adjustment this is.']},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = _money(request.data.get('amount'))
    except ValueError:
        return Response({'amount': ['Enter an amount.']},
                        status=status.HTTP_400_BAD_REQUEST)
    if amount == 0:
        return Response({'amount': ['An adjustment of zero changes nothing.']},
                        status=status.HTTP_400_BAD_REQUEST)
    reason = (request.data.get('reason') or '').strip()
    if not reason:
        return Response({'reason': ['Say why. This record can never be '
                                    'edited afterwards.']},
                        status=status.HTTP_400_BAD_REQUEST)

    add_adjustment(invoice, kind, amount, reason, _accountant(request))
    invoice = FeeInvoice.objects.prefetch_related(
        'lines', 'adjustments', 'payments').get(pk=invoice.pk)
    return Response(fee_invoice_dict(invoice, detail=True, for_office=True),
                    status=status.HTTP_201_CREATED)


# ------------------------------------------------------------ Student side

def _own_invoices(student):
    """Every bill belonging to this student, newest first.

    Cancelled bills are kept in the list rather than hidden: a student who
    was told they owed something deserves to see that it was withdrawn, not
    to watch it vanish.
    """
    return FeeInvoice.objects.filter(student=student).select_related(
        'course', 'session').prefetch_related(
        'lines', 'adjustments', 'payments')


@api_view(['GET'])
@permission_classes([IsStudent])
def my_fees(request):
    """The student's own fee position: what they owe, and every bill behind it.

    The college decided fees are a WARNING, not a gate — nothing here locks
    a student out of results or promotion. What it does do is make the
    number impossible to miss.
    """
    student = get_object_or_404(Student, admin=request.user)
    invoices = list(_own_invoices(student))

    live = [i for i in invoices if not i.is_cancelled and i.balance > ZERO]
    overdue = [i for i in live if i.days_overdue]
    upcoming = sorted((i for i in live if not i.days_overdue),
                      key=lambda i: i.due_date)

    return Response({
        'outstanding_total': sum((i.balance for i in live), ZERO),
        'overdue_total': sum((i.balance for i in overdue), ZERO),
        'overdue_count': len(overdue),
        'next_due_date': upcoming[0].due_date.isoformat() if upcoming else None,
        'next_due_amount': upcoming[0].balance if upcoming else ZERO,
        'paid_total': sum((i.paid for i in invoices), ZERO),
        'invoices': [fee_invoice_dict(i) for i in invoices],
    })


@api_view(['GET'])
@permission_classes([IsStudent])
def my_invoice(request, invoice_id):
    """One of the student's own bills, itemised.

    Scoped by student rather than looked up by id and checked afterwards, so
    another student's invoice is a 404 and not a 403 — there is no reason to
    confirm that somebody else's bill exists.
    """
    student = get_object_or_404(Student, admin=request.user)
    invoice = get_object_or_404(_own_invoices(student), id=invoice_id)
    return Response(fee_invoice_dict(invoice, detail=True))


@api_view(['GET'])
@permission_classes([IsStudent])
def my_receipts(request):
    """Every receipt this student holds, newest first."""
    student = get_object_or_404(Student, admin=request.user)
    return Response([
        fee_payment_dict(p) for p in student.fee_payments.select_related(
            'invoice')])
