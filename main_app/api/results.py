from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import CourseSubject, Staff, Student, StudentResult, Subject
from .attendance import picker_context
from .permissions import IsStaff, IsStudent


def _teaches(staff, subject):
    """Whether `staff` is assigned to teach `subject` in any class/shift —
    results can only be entered for subjects a teacher actually teaches."""
    return CourseSubject.objects.filter(subject=subject).filter(
        Q(morning_staff=staff) | Q(day_staff=staff)).exists()


@api_view(['GET'])
@permission_classes([IsStaff])
def classes(request):
    """Class picker for result pages (same data as the attendance picker)."""
    staff = get_object_or_404(Staff, admin=request.user)
    return Response(picker_context(staff))


@api_view(['GET'])
@permission_classes([IsStaff])
def class_students(request):
    """Students for the result dropdowns. The pages pass subject + session
    (like the old staff_add_result template's ajax did)."""
    staff = get_object_or_404(Staff, admin=request.user)
    params = request.query_params
    subject = get_object_or_404(Subject, id=params.get('subject'))
    if not _teaches(staff, subject):
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)
    students = Student.objects.filter(
        course__in=subject.courses.all(), passed_out=False)
    if params.get('session'):
        students = students.filter(session_id=params.get('session'))
    students = students.order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    return Response([{
        'id': s.id,
        'name': s.admin.first_name + " " + s.admin.last_name,
        'roll_number': s.roll_number or "",
    } for s in students])


@api_view(['GET'])
@permission_classes([IsStaff])
def fetch(request):
    """Existing scores of one student for a subject (fetch_student_result)."""
    staff = get_object_or_404(Staff, admin=request.user)
    params = request.query_params
    student = get_object_or_404(Student, id=params.get('student'))
    subject = get_object_or_404(Subject, id=params.get('subject'))
    if not _teaches(staff, subject):
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)
    result = get_object_or_404(StudentResult, student=student, subject=subject)
    return Response({'test': result.test, 'exam': result.exam})


@api_view(['POST', 'PUT'])
@permission_classes([IsStaff])
def save(request):
    """POST upserts like staff_add_result; PUT updates like EditResultView
    (404 when no existing result)."""
    staff = get_object_or_404(Staff, admin=request.user)
    data = request.data
    student = get_object_or_404(Student, id=data.get('student'))
    subject = get_object_or_404(Subject, id=data.get('subject'))
    if not _teaches(staff, subject):
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)
    test = data.get('test')
    exam = data.get('exam')
    if request.method == 'PUT':
        result = get_object_or_404(StudentResult, student=student, subject=subject)
        result.test = test
        result.exam = exam
        result.save()
        return Response({'detail': 'Result Updated'})
    result, created = StudentResult.objects.update_or_create(
        student=student, subject=subject,
        defaults={'test': test, 'exam': exam})
    return Response({'updated': not created},
                    status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


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
            student=student, subject_id__in=[cs.subject_id for cs in cs_list])}
        for cs in cs_list:
            result = result_map.get(cs.subject_id)
            rows.append({
                'subject_name': cs.subject.name,
                'result': {'test': result.test, 'exam': result.exam} if result else None,
            })
    return Response({'semesters': semesters, 'selected': selected, 'rows': rows})
