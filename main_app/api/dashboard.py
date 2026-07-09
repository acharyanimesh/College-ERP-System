import math

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (Attendance, AttendanceReport, Course, CourseSubject,
                      LeaveReportStaff, LeaveReportStudent, Staff, Student,
                      Subject)
from .permissions import IsAdmin, IsStaff, IsStudent


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_home(request):
    """Counters + chart series with the exact field names hod_views.admin_home
    passed as template context (including its quirks, for pixel parity)."""
    total_staff = Staff.objects.all().count()
    total_students = Student.objects.filter(passed_out=False).count()
    subjects = Subject.objects.all()
    total_subject = subjects.count()
    total_course = Course.objects.all().count()
    attendance_list = []
    for subject in subjects:
        attendance_list.append(Attendance.objects.filter(subject=subject).count())

    course_name_list = []
    subject_count_list = []
    student_count_list_in_course = []
    for course in Course.objects.all():
        subject_count_list.append(Subject.objects.filter(courses=course).count())
        student_count_list_in_course.append(
            Student.objects.filter(course_id=course.id, passed_out=False).count())
        course_name_list.append(course.short_name)

    subject_list = []
    student_count_list_in_subject = []
    for subject in Subject.objects.all():
        student_count = Student.objects.filter(course__in=subject.courses.all()).count()
        subject_list.append(subject.name)
        student_count_list_in_subject.append(student_count)

    student_attendance_present_list = []
    student_attendance_leave_list = []
    student_name_list = []
    for student in Student.objects.all():
        attendance = AttendanceReport.objects.filter(
            student_id=student.id, status=True).count()
        absent = AttendanceReport.objects.filter(
            student_id=student.id, status=False).count()
        leave = LeaveReportStudent.objects.filter(
            student_id=student.id, status=1).count()
        student_attendance_present_list.append(attendance)
        student_attendance_leave_list.append(leave + absent)
        student_name_list.append(student.admin.first_name)

    return Response({
        'total_students': total_students,
        'total_staff': total_staff,
        'total_course': total_course,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'student_attendance_present_list': student_attendance_present_list,
        'student_attendance_leave_list': student_attendance_leave_list,
        'student_name_list': student_name_list,
        'student_count_list_in_subject': student_count_list_in_subject,
        'student_count_list_in_course': student_count_list_in_course,
        'course_name_list': course_name_list,
    })


@api_view(['GET'])
@permission_classes([IsStaff])
def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    staff_courses = staff.courses.all()
    total_students = Student.objects.filter(
        course__in=staff_courses, passed_out=False).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(
        Q(coursesubject__morning_staff=staff) | Q(coursesubject__day_staff=staff)).distinct()
    total_subject = subjects.count()
    total_attendance = Attendance.objects.filter(subject__in=subjects).count()
    subject_list = []
    attendance_list = []
    assigned_subjects = []
    for subject in subjects:
        subject_list.append(subject.name)
        attendance_list.append(Attendance.objects.filter(subject=subject).count())
        assigned_subjects.append({
            'id': subject.id,
            'name': subject.name,
            'courses': [
                {'name': c.name, 'short_name': c.short_name}
                for c in subject.courses.all()
            ],
        })
    return Response({
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'assigned_subjects': assigned_subjects,
    })


@api_view(['GET'])
@permission_classes([IsStudent])
def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    total_subject = Subject.objects.filter(courses=student.course).count()
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(
        student=student, status=True).count()
    if total_attendance == 0:
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present / total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    subject_name = []
    data_present = []
    data_absent = []
    for subject in Subject.objects.filter(courses=student.course):
        attendance = Attendance.objects.filter(subject=subject)
        data_present.append(AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count())
        data_absent.append(AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count())
        subject_name.append(subject.name)
    course_subjects = []
    for cs in CourseSubject.objects.filter(course=student.course).select_related(
            'subject', 'morning_staff__admin', 'day_staff__admin').order_by(
            'semester', 'subject__name'):
        teacher = cs.staff_for_shift(student.shift)
        course_subjects.append({
            'subject_name': cs.subject.name,
            'teacher_name': str(teacher) if teacher else None,
        })
    return Response({
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': total_subject,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'course_subjects': course_subjects,
    })
