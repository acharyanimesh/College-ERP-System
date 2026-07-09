from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..forms import CourseForm, SessionForm, SubjectForm
from ..models import Course, CourseSubject, Session, Subject
from .permissions import IsAdmin
from .serializers import course_dict, form_errors, session_dict, subject_dict


# ---------------------------------------------------------------- Courses

@api_view(['GET', 'POST'])
def course_list(request):
    if request.method == 'GET':
        # Any logged-in role may read the course list (form dropdowns).
        return Response([course_dict(c) for c in Course.objects.all()])
    if not IsAdmin().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    form = CourseForm(request.data)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    course = form.save()
    return Response(course_dict(course), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def course_item(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'GET':
        return Response(course_dict(course))
    if request.method == 'DELETE':
        try:
            course.delete()
        except Exception:
            return Response({'detail':
                "Sorry, some students are assigned to this course already. "
                "Kindly change the affected student course and try again"},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
    form = CourseForm(request.data, instance=course)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    return Response(course_dict(form.save()))


# ---------------------------------------------------------------- Subjects

def _sync_course_semesters(subject, rows):
    """Apply the [{course, semester}] assignment list like edit_subject:
    update_or_create the chosen courses, drop the rest."""
    chosen = {}
    for row in rows:
        course_id = row.get('course')
        semester = row.get('semester')
        if course_id and semester:
            chosen[int(course_id)] = semester
    for course in Course.objects.all():
        if course.id in chosen:
            CourseSubject.objects.update_or_create(
                course=course, subject=subject,
                defaults={'semester': chosen[course.id]})
        else:
            CourseSubject.objects.filter(course=course, subject=subject).delete()
    return chosen


@api_view(['GET', 'POST'])
def subject_list(request):
    if request.method == 'GET':
        subjects = Subject.objects.all()
        if request.query_params.get('mine'):
            # Student role: only the subjects of the student's own course.
            student = getattr(request.user, 'student', None)
            subjects = subjects.filter(courses=student.course) if student else Subject.objects.none()
        course = request.query_params.get('course')
        semester = request.query_params.get('semester')
        if course:
            subjects = subjects.filter(coursesubject__course_id=course)
        if semester:
            subjects = subjects.filter(coursesubject__semester=semester)
        subjects = subjects.distinct().order_by(Lower('name'))
        return Response([subject_dict(s) for s in subjects])

    if not IsAdmin().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    rows = request.data.get('courses') or []
    if not any(r.get('course') and r.get('semester') for r in rows):
        return Response({'detail':
            "Assign the subject to at least one course by entering its semester."},
            status=status.HTTP_400_BAD_REQUEST)
    form = SubjectForm(request.data)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            subject = form.save()
            _sync_course_semesters(subject, rows)
    except Exception as e:
        return Response({'detail': "Could Not Add " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(subject_dict(subject), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def subject_item(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if request.method == 'GET':
        course_semesters = []
        for cs in CourseSubject.objects.filter(subject=subject).select_related(
                'course', 'morning_staff__admin', 'day_staff__admin'):
            course_semesters.append({
                'course_name': cs.course.name,
                'course_short_name': cs.course.short_name,
                'semester': cs.semester,
                'morning_staff_name': str(cs.morning_staff) if cs.morning_staff else None,
                'day_staff_name': str(cs.day_staff) if cs.day_staff else None,
            })
        data = subject_dict(subject)
        data['course_semesters'] = course_semesters
        data['courses'] = [
            {'course': cs.course_id, 'semester': cs.semester}
            for cs in CourseSubject.objects.filter(subject=subject)
        ]
        return Response(data)

    if request.method == 'DELETE':
        subject.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    rows = request.data.get('courses') or []
    if not any(r.get('course') and r.get('semester') for r in rows):
        return Response({'detail':
            "Assign the subject to at least one course by entering its semester."},
            status=status.HTTP_400_BAD_REQUEST)
    form = SubjectForm(request.data, instance=subject)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            subject = form.save()
            _sync_course_semesters(subject, rows)
    except Exception as e:
        return Response({'detail': "Could Not Update " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(subject_dict(subject))


@api_view(['GET'])
@permission_classes([IsAdmin])
def subject_semesters(request, course_id):
    """Manage Subjects semester tiles (manage_subject_by_course)."""
    course = get_object_or_404(Course, id=course_id)
    total_semesters = course.semesters or 0
    semester_data = []
    for sem in range(1, total_semesters + 1):
        semester_data.append({
            'number': sem,
            'subject_count': CourseSubject.objects.filter(
                course=course, semester=sem).count(),
        })
    return Response({
        'course': course_dict(course),
        'semester_data': semester_data,
    })


# ---------------------------------------------------------------- Sessions

@api_view(['GET', 'POST'])
def session_list(request):
    if request.method == 'GET':
        # Staff need sessions for the results pages; admin for student forms.
        return Response([session_dict(s) for s in Session.objects.all()])
    if not IsAdmin().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    form = SessionForm(request.data)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    return Response(session_dict(form.save()), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def session_item(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'GET':
        return Response(session_dict(session))
    if request.method == 'DELETE':
        try:
            session.delete()
        except Exception:
            return Response({'detail':
                "There are students assigned to this session. "
                "Please move them to another session."},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
    form = SessionForm(request.data, instance=session)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    return Response(session_dict(form.save()))
