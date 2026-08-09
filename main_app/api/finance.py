"""The accountant's finance desk: the per-semester fee price list, each
student's dues against it, and the payment receipts taken at the counter.

The one thing worth stating up front is how a "due" is computed. A student's
bill for the term is the FeeStructure amount for their course at their current
semester; what they have paid is the sum of their FeePayment receipts filed
under that same semester; what they owe is the difference, floored at zero.
Everything the desk shows — a single student's outstanding balance, a course's
collection rate, the dashboard totals — is that one rule applied in bulk.
"""
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (BookRequest, Course, FeePayment, FeeStructure,
                      LibraryFine, Student)
from .permissions import IsAccountant
from .serializers import fee_payment_dict, library_fine_dict


# --------------------------------------------------------------------------
# Shared fee math (also used by the accountant dashboard)
# --------------------------------------------------------------------------

def fee_map():
    """{(course_id, semester): amount} for the whole price list, so a batch of
    students can be priced without a query each."""
    return {
        (fs.course_id, fs.semester): fs.amount
        for fs in FeeStructure.objects.all()
    }


def paid_map():
    """{(student_id, semester): total paid} across every receipt, aggregated in
    one pass rather than one query per student."""
    rows = (FeePayment.objects
            .values('student_id', 'semester')
            .annotate(total=Sum('amount')))
    return {(r['student_id'], r['semester']): r['total'] for r in rows}


def student_fee_view(student, fees=None, paids=None):
    """One active student's bill for their current term: expected, paid,
    outstanding, and a coarse status. `fees`/`paids` are the batch maps above;
    passing them keeps a list view from re-querying per row."""
    fees = fee_map() if fees is None else fees
    paids = paid_map() if paids is None else paids
    semester = student.current_semester
    expected = fees.get((student.course_id, semester), 0)
    paid = paids.get((student.id, semester), 0)
    outstanding = max(expected - paid, 0)
    if expected == 0:
        state = 'unbilled'          # no fee set for this course+semester yet
    elif paid == 0:
        state = 'unpaid'
    elif outstanding > 0:
        state = 'partial'
    else:
        state = 'paid'
    user = student.admin
    return {
        'student_id': student.id,
        'student_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
        'roll_number': student.roll_number or '',
        'course': student.course_id,
        'course_short_name': student.course.short_name if student.course else '—',
        'semester': semester,
        'expected': expected,
        'paid': paid,
        'outstanding': outstanding,
        'status': state,
    }


# --------------------------------------------------------------------------
# Price list — FeeStructure per (course, semester)
# --------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAccountant])
def fee_structures(request):
    """GET: the full price-list grid, every course with a row per semester
    (amount 0 where none is set yet). POST { items: [{course, semester,
    amount}] }: upsert each amount."""
    if request.method == 'POST':
        items = request.data.get('items') or []
        saved = 0
        with transaction.atomic():
            for item in items:
                try:
                    course_id = int(item.get('course'))
                    semester = int(item.get('semester'))
                    amount = int(item.get('amount') or 0)
                except (TypeError, ValueError):
                    continue
                if amount < 0:
                    continue
                FeeStructure.objects.update_or_create(
                    course_id=course_id, semester=semester,
                    defaults={'amount': amount})
                saved += 1
        return Response({'detail': "Saved %d fee amount%s." % (
            saved, '' if saved == 1 else 's')})

    existing = fee_map()
    courses = []
    for course in Course.objects.all().order_by('code'):
        rows = []
        for sem in range(1, (course.semesters or 0) + 1):
            rows.append({
                'semester': sem,
                'amount': existing.get((course.id, sem), 0),
            })
        courses.append({
            'course_id': course.id,
            'course_name': course.name,
            'course_short_name': course.short_name,
            'semesters': rows,
        })
    return Response({'courses': courses})


# --------------------------------------------------------------------------
# Student dues
# --------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAccountant])
def student_fees(request):
    """Active students with their term dues — the collection worklist and the
    picker behind Collect Fee. Filterable by course, semester, status and a
    name/roll search."""
    students = Student.objects.filter(passed_out=False).select_related(
        'admin', 'course')
    course = request.query_params.get('course')
    semester = request.query_params.get('semester')
    if course:
        students = students.filter(course_id=course)
    if semester:
        students = students.filter(current_semester=semester)
    students = students.order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))

    fees, paids = fee_map(), paid_map()
    rows = [student_fee_view(s, fees, paids) for s in students]

    status_filter = request.query_params.get('status')
    if status_filter:
        rows = [r for r in rows if r['status'] == status_filter]
    search = (request.query_params.get('search') or '').lower().strip()
    if search:
        rows = [r for r in rows
                if search in r['student_name'].lower()
                or search in r['roll_number'].lower()]
    return Response(rows)


@api_view(['GET'])
@permission_classes([IsAccountant])
def student_fee_detail(request, student_id):
    """One student's dues plus their receipt history — the Collect Fee screen
    and the student's own ledger."""
    student = get_object_or_404(
        Student.objects.select_related('admin', 'course'), id=student_id)
    view = student_fee_view(student)
    payments = FeePayment.objects.filter(student=student).select_related(
        'student__admin', 'student__course')
    view['payments'] = [fee_payment_dict(p, for_accountant=True) for p in payments]
    view['total_paid_all_time'] = sum(p.amount for p in payments)
    return Response(view)


# --------------------------------------------------------------------------
# Payments — the receipts taken at the desk
# --------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAccountant])
def payments(request):
    """GET: every receipt (filter by course / student / search). POST
    { student, amount, semester?, method?, note? }: take a payment and file a
    receipt for it."""
    if request.method == 'POST':
        student = get_object_or_404(Student, id=request.data.get('student'))
        try:
            amount = int(request.data.get('amount'))
        except (TypeError, ValueError):
            return Response({'amount': ['Enter a whole rupee amount.']},
                            status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'amount': ['Amount must be greater than zero.']},
                            status=status.HTTP_400_BAD_REQUEST)
        semester = request.data.get('semester') or student.current_semester
        try:
            semester = int(semester)
        except (TypeError, ValueError):
            semester = student.current_semester
        method = request.data.get('method') or FeePayment.CASH
        if method not in dict(FeePayment.METHOD_CHOICES):
            method = FeePayment.CASH
        accountant = request.user.accountant
        try:
            with transaction.atomic():
                payment = FeePayment.objects.create(
                    student=student,
                    semester=semester,
                    amount=amount,
                    method=method,
                    note=request.data.get('note') or '',
                    receipt_no=FeePayment.next_receipt_no(),
                    collected_by=accountant,
                    collected_by_name=str(accountant))
        except Exception as e:
            return Response({'detail': "Could not record the payment: " + str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        data = fee_payment_dict(payment, for_accountant=True)
        data['detail'] = "Receipt %s recorded — Rs. %d from %s." % (
            payment.receipt_no, payment.amount, data['student_name'])
        return Response(data, status=status.HTTP_201_CREATED)

    qs = FeePayment.objects.select_related('student__admin', 'student__course')
    course = request.query_params.get('course')
    student_id = request.query_params.get('student')
    if course:
        qs = qs.filter(student__course_id=course)
    if student_id:
        qs = qs.filter(student_id=student_id)
    rows = [fee_payment_dict(p, for_accountant=True) for p in qs]
    search = (request.query_params.get('search') or '').lower().strip()
    if search:
        rows = [r for r in rows
                if search in r['student_name'].lower()
                or search in r['receipt_no'].lower()
                or search in r['student_roll'].lower()]
    return Response(rows)


# --------------------------------------------------------------------------
# Library fines — the desk's read-only view of the college's other money
# --------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAccountant])
def library_fines(request):
    """Every library fine receipt, plus what is still owed on overdue loans —
    read only. The librarian collects these at their own desk; the accountant
    only needs to see them to keep the books straight."""
    receipts = LibraryFine.objects.select_related(
        'student__admin', 'student__course', 'request__book')
    issued = BookRequest.objects.filter(
        status=BookRequest.ISSUED).select_related('book', 'student__admin')
    outstanding = [r for r in issued if r.fine_outstanding]
    return Response({
        'receipts': [library_fine_dict(f, for_librarian=True) for f in receipts],
        'total_collected': sum(
            f.amount for f in receipts if f.kind == LibraryFine.PAID),
        'total_outstanding': sum(r.fine_outstanding for r in outstanding),
        'outstanding_loans': [{
            'student_name': ("%s %s" % (
                r.student.admin.first_name, r.student.admin.last_name)).strip(),
            'book_name': r.book.name,
            'days_overdue': r.days_overdue,
            'fine': r.fine,
        } for r in sorted(outstanding, key=lambda r: -r.days_overdue)],
    })
