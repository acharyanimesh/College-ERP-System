"""Notifications: admin sends, staff/students read their own. The FCM push
the old views fired is deliberately not ported (the React app doesn't
register service workers); notifications are stored and shown in-app."""
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (Course, NotificationStaff, NotificationStudent, Staff,
                      Student)
from .permissions import ADMIN, IsAdmin, STAFF, STUDENT
from .serializers import course_dict, student_row


def _notification_dict(n):
    return {
        'id': n.id,
        'message': n.message,
        'created_at': n.created_at.strftime('%b. %d, %Y'),
    }


@api_view(['GET'])
def mine(request, role):
    if role == 'staff' and str(request.user.user_type) == STAFF:
        staff = get_object_or_404(Staff, admin=request.user)
        notifications = NotificationStaff.objects.filter(staff=staff)
    elif role == 'student' and str(request.user.user_type) == STUDENT:
        student = get_object_or_404(Student, admin=request.user)
        notifications = NotificationStudent.objects.filter(student=student)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    return Response([_notification_dict(n) for n in notifications])


@api_view(['GET'])
@permission_classes([IsAdmin])
def staff_recipients(request):
    """Staff table for Send Notifications (admin_notify_staff). ids are
    CustomUser ids — what the send endpoint expects."""
    staff_users = Staff.objects.select_related('admin').order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    return Response([{
        'id': s.admin_id,
        'first_name': s.admin.first_name,
        'last_name': s.admin.last_name,
        'email': s.admin.email,
        'gender': s.admin.get_gender_display(),
        'profile_pic': s.admin.profile_pic.url if s.admin.profile_pic else '',
    } for s in staff_users])


@api_view(['GET'])
@permission_classes([IsAdmin])
def student_browse(request):
    """Landing data for notify-students (admin_notify_student): course tiles
    + the flat search list."""
    course_data = []
    for course in Course.objects.all():
        course_data.append({
            'course': course_dict(course),
            'student_count': Student.objects.filter(
                course=course, passed_out=False).count(),
        })
    search_students = []
    for s in Student.objects.filter(passed_out=False).select_related(
            'admin', 'course').order_by(
            Lower('admin__first_name'), Lower('admin__last_name')):
        search_students.append({
            'id': s.admin_id,
            'name': "%s %s" % (s.admin.first_name, s.admin.last_name),
            'roll': s.roll_number or '',
            'course': s.course.short_name if s.course else '—',
            'course_full': s.course.name if s.course else '',
            'semester': s.current_semester,
        })
    return Response({
        'course_data': course_data,
        'search_students': search_students,
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def student_semesters(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    total_semesters = course.semesters or 0
    semester_data = []
    for sem in range(1, total_semesters + 1):
        semester_data.append({
            'number': sem,
            'student_count': Student.objects.filter(
                course=course, current_semester=sem, passed_out=False).count(),
        })
    return Response({
        'course': course_dict(course),
        'semester_data': semester_data,
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def student_recipients(request):
    """Students of course+semester, both shifts (notify_student_by_semester)."""
    students = Student.objects.filter(passed_out=False).select_related(
        'admin', 'course', 'session')
    course = request.query_params.get('course')
    semester = request.query_params.get('semester')
    if course:
        students = students.filter(course_id=course)
    if semester:
        students = students.filter(current_semester=semester)
    students = students.order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    return Response([student_row(s) for s in students])


@api_view(['POST'])
@permission_classes([IsAdmin])
def send_to_staff(request):
    staff = get_object_or_404(Staff, admin_id=request.data.get('id'))
    NotificationStaff.objects.create(
        staff=staff, message=request.data.get('message'))
    return Response({'detail': 'Notification sent'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdmin])
def send_to_student(request):
    student = get_object_or_404(Student, admin_id=request.data.get('id'))
    NotificationStudent.objects.create(
        student=student, message=request.data.get('message'))
    return Response({'detail': 'Notification sent'}, status=status.HTTP_201_CREATED)
