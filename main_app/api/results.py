from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (Course, CourseSubject, ResultFinalization, Staff,
                      Student, StudentResult, Subject)
from .permissions import IsStaff, IsStudent

NUMERIC_FIELDS = ('unit_test', 'internal', 'pre_board')


def _teaches_class(staff, subject, course, semester):
    """Whether `staff` teaches `subject` in `course` at `semester`, in
    either shift — results cover the whole class, so either shift's
    assignment is enough."""
    return CourseSubject.objects.filter(
        subject=subject, course=course, semester=semester
    ).filter(Q(morning_staff=staff) | Q(day_staff=staff)).exists()


def _roster(course, semester):
    return Student.objects.filter(
        course=course, current_semester=semester, passed_out=False
    ).select_related('admin').order_by('roll_number')


@api_view(['GET'])
@permission_classes([IsStaff])
def classes(request):
    """Subject -> distinct (course, semester) classes this staff teaches,
    ignoring shift — a result set covers both shifts of a class together."""
    staff = get_object_or_404(Staff, admin=request.user)
    cs_qs = CourseSubject.objects.filter(
        Q(morning_staff=staff) | Q(day_staff=staff)
    ).select_related('subject', 'course').order_by('subject__name')
    subj_map = {}
    for cs in cs_qs:
        entry = subj_map.setdefault(cs.subject_id, {
            'id': cs.subject_id, 'name': cs.subject.name, 'classes': []})
        entry['classes'].append({
            'course': cs.course_id,
            'course_name': cs.course.short_name,
            'semester': cs.semester,
        })
    return Response({'subjects': list(subj_map.values())})


@api_view(['GET'])
@permission_classes([IsStaff])
def class_results(request):
    """Roster + existing marks + finalized flag for one (subject, course,
    semester) — backs both the entry table and the read-only view."""
    staff = get_object_or_404(Staff, admin=request.user)
    params = request.query_params
    subject = get_object_or_404(Subject, id=params.get('subject'))
    course = get_object_or_404(Course, id=params.get('course'))
    try:
        semester = int(params.get('semester'))
    except (TypeError, ValueError):
        return Response({'detail': 'semester is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not _teaches_class(staff, subject, course, semester):
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)

    students = _roster(course, semester)
    result_map = {r.student_id: r for r in StudentResult.objects.filter(
        subject=subject, course=course, semester=semester)}
    finalized = ResultFinalization.objects.filter(
        course=course, subject=subject, semester=semester).exists()

    rows = []
    for s in students:
        r = result_map.get(s.id)
        rows.append({
            'student': s.id,
            'roll_number': s.roll_number or '',
            'name': s.admin.first_name + " " + s.admin.last_name,
            'unit_test': r.unit_test if r else None,
            'internal': r.internal if r else None,
            'pre_board': r.pre_board if r else None,
            'final_grade': r.final_grade if r else '',
        })
    return Response({'finalized': finalized, 'rows': rows})


@api_view(['POST'])
@permission_classes([IsStaff])
def save_class_results(request):
    """Bulk upsert every student's marks for one (subject, course,
    semester) — { subject, course, semester, rows: [{student, unit_test,
    internal, pre_board, final_grade}] }."""
    staff = get_object_or_404(Staff, admin=request.user)
    data = request.data
    subject = get_object_or_404(Subject, id=data.get('subject'))
    course = get_object_or_404(Course, id=data.get('course'))
    try:
        semester = int(data.get('semester'))
    except (TypeError, ValueError):
        return Response({'detail': 'semester is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not _teaches_class(staff, subject, course, semester):
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)
    if ResultFinalization.objects.filter(
            course=course, subject=subject, semester=semester).exists():
        return Response({'code': 'FINALIZED'}, status=status.HTTP_400_BAD_REQUEST)

    roster_ids = set(_roster(course, semester).values_list('id', flat=True))
    with transaction.atomic():
        for row in (data.get('rows') or []):
            student_id = row.get('student')
            if student_id not in roster_ids:
                continue
            defaults = {f: row.get(f) for f in NUMERIC_FIELDS}
            defaults['final_grade'] = row.get('final_grade') or ''
            StudentResult.objects.update_or_create(
                student_id=student_id, subject=subject, course=course,
                semester=semester, defaults=defaults)
    return Response({'detail': 'Results saved'})


@api_view(['POST'])
@permission_classes([IsStaff])
def finalize(request):
    """Lock a (subject, course, semester) result set — only once every
    student on the roster has all three marks and a final grade."""
    staff = get_object_or_404(Staff, admin=request.user)
    data = request.data
    subject = get_object_or_404(Subject, id=data.get('subject'))
    course = get_object_or_404(Course, id=data.get('course'))
    try:
        semester = int(data.get('semester'))
    except (TypeError, ValueError):
        return Response({'detail': 'semester is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not _teaches_class(staff, subject, course, semester):
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)

    students = _roster(course, semester)
    if not students.exists():
        return Response({'code': 'NO_STUDENTS'}, status=status.HTTP_400_BAD_REQUEST)
    result_map = {r.student_id: r for r in StudentResult.objects.filter(
        subject=subject, course=course, semester=semester)}
    incomplete = 0
    for s in students:
        r = result_map.get(s.id)
        if (not r or r.unit_test is None or r.internal is None
                or r.pre_board is None or not r.final_grade):
            incomplete += 1
    if incomplete:
        return Response(
            {'code': 'INCOMPLETE', 'incomplete_count': incomplete},
            status=status.HTTP_400_BAD_REQUEST)

    ResultFinalization.objects.get_or_create(
        course=course, subject=subject, semester=semester)
    return Response({'detail': 'Result finalized'})


@api_view(['GET'])
@permission_classes([IsStudent])
def mine(request):
    """Own results by semester (student_views.student_view_result)."""
    student = get_object_or_404(Student, admin=request.user)
    course = student.course
    semesters = list(CourseSubject.objects.filter(course=course)
                     .exclude(semester__isnull=True)
                     .values_list('semester', flat=True).distinct().order_by('semester'))
    try:
        selected = int(request.query_params.get('semester'))
    except (TypeError, ValueError):
        selected = semesters[0] if semesters else None

    rows = []
    if selected is not None:
        cs_list = CourseSubject.objects.filter(
            course=course, semester=selected).select_related('subject').order_by(
            'subject__name')
        result_map = {r.subject_id: r for r in StudentResult.objects.filter(
            student=student, course=course, semester=selected,
            subject_id__in=[cs.subject_id for cs in cs_list])}
        finalized_subjects = set(ResultFinalization.objects.filter(
            course=course, semester=selected).values_list('subject_id', flat=True))
        for cs in cs_list:
            result = result_map.get(cs.subject_id)
            rows.append({
                'subject_name': cs.subject.name,
                'finalized': cs.subject_id in finalized_subjects,
                'result': {
                    'unit_test': result.unit_test,
                    'internal': result.internal,
                    'pre_board': result.pre_board,
                    'final_grade': result.final_grade,
                } if result else None,
            })
    return Response({'semesters': semesters, 'selected': selected, 'rows': rows})
