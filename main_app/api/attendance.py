from datetime import datetime

from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (SHIFT_CHOICES, Attendance, AttendanceReport, Course,
                      CourseSubject, CustomUser, Staff, Student, Subject)
from .permissions import IsAdmin, IsStaff, IsStudent
from .serializers import course_dict, student_row


def picker_context(staff):
    """Shift → Subject → Class picker data, mirroring
    staff_views._attendance_picker_context (minus the template-only JSON)."""
    shifts = [{'value': v, 'label': l}
              for v, l in SHIFT_CHOICES if v in staff.shifts]
    active = set(
        Student.objects.filter(passed_out=False)
        .values_list('course_id', 'current_semester', 'shift').distinct())
    cs_qs = CourseSubject.objects.filter(
        Q(morning_staff=staff) | Q(day_staff=staff)).select_related('subject', 'course')
    subj_map = {}
    for cs in cs_qs:
        entry = subj_map.setdefault(cs.subject_id, {
            'id': cs.subject_id, 'name': cs.subject.name,
            'morning': False, 'day': False, 'classes': []})
        for shift in ('morning', 'day'):
            staff_id = cs.morning_staff_id if shift == 'morning' else cs.day_staff_id
            if staff_id != staff.id:
                continue
            entry[shift] = True
            entry['classes'].append({
                'course': cs.course_id,
                'course_name': cs.course.short_name,
                'semester': cs.semester,
                'shift': shift,
                'active': (cs.course_id, cs.semester, shift) in active,
            })
    subjects = sorted(subj_map.values(), key=lambda s: s['name'].lower())
    return {'subjects': subjects, 'shifts': shifts}


@api_view(['GET'])
@permission_classes([IsStaff])
def picker(request):
    staff = get_object_or_404(Staff, admin=request.user)
    return Response(picker_context(staff))


@api_view(['GET'])
@permission_classes([IsStaff])
def class_students(request, ):
    """Students of one class (staff_views.get_students)."""
    params = request.query_params
    students = Student.objects.filter(
        course_id=params.get('course'),
        current_semester=params.get('semester'),
        shift=params.get('shift'),
        passed_out=False).order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    return Response([{
        'id': s.id,
        'name': s.admin.first_name + " " + s.admin.last_name,
        'roll_number': s.roll_number or "",
    } for s in students])


@api_view(['GET', 'POST'])
@permission_classes([IsStaff])
def attendance_list(request):
    if request.method == 'GET':
        # Existing attendance dates of a class (views.get_attendance).
        params = request.query_params
        subject = get_object_or_404(Subject, id=params.get('subject'))
        attendance = Attendance.objects.filter(
            subject=subject, shift=params.get('shift'),
            course_id=params.get('course'), semester=params.get('semester'))
        if params.get('include_locked') != '1':
            attendance = attendance.filter(locked=False)
        result = []
        for attd in attendance.order_by('-date'):
            label = "%s (%s)" % (attd.date, attd.get_shift_display())
            if attd.locked:
                label += " — confirmed"
            result.append({
                'id': attd.id,
                'attendance_date': label,
                'locked': attd.locked,
                'session': attd.session_id,
            })
        return Response(result)

    # POST — save new attendance (staff_views.save_attendance).
    data = request.data
    staff = get_object_or_404(Staff, admin=request.user)
    subject = get_object_or_404(Subject, id=data.get('subject'))
    course_id = data.get('course')
    semester = data.get('semester')
    shift = data.get('shift')
    students = data.get('student_ids') or []

    shift_field = 'morning_staff' if shift == 'morning' else 'day_staff'
    if not CourseSubject.objects.filter(
            subject=subject, course_id=course_id, semester=semester,
            **{shift_field: staff}).exists():
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)

    cohort = Student.objects.filter(id__in=[s.get('id') for s in students])
    first_student = cohort.first()
    session = first_student.session if first_student else None
    if session is None:
        return Response({'code': 'NO_SESSION'}, status=status.HTTP_400_BAD_REQUEST)

    attendance = Attendance(
        session=session, subject=subject, course_id=course_id,
        semester=semester, shift=shift, date=data.get('date'))
    attendance.save()
    for student_dict in students:
        student = get_object_or_404(Student, id=student_dict.get('id'))
        AttendanceReport.objects.create(
            student=student, attendance=attendance,
            status=student_dict.get('status'),
            late=student_dict.get('late', 0))
    return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsStaff])
def attendance_students(request, attendance_id):
    """Per-student records of one date (staff_views.get_student_attendance).
    ids are CustomUser ids, matching the old endpoint's contract."""
    attendance = get_object_or_404(Attendance, id=attendance_id)
    reports = AttendanceReport.objects.filter(attendance=attendance).order_by(
        Lower('student__admin__first_name'), Lower('student__admin__last_name'))
    return Response([{
        'id': r.student.admin_id,
        'name': r.student.admin.first_name + " " + r.student.admin.last_name,
        'roll_number': r.student.roll_number or "",
        'status': r.status,
        'late': r.late,
        'locked': attendance.locked,
    } for r in reports])


@api_view(['PUT'])
@permission_classes([IsStaff])
def attendance_update(request, attendance_id):
    """Update-and-lock (staff_views.update_attendance)."""
    staff = get_object_or_404(Staff, admin=request.user)
    attendance = get_object_or_404(Attendance, id=attendance_id)
    if attendance.locked:
        return Response({'code': 'LOCKED'}, status=status.HTTP_400_BAD_REQUEST)
    shift_field = 'morning_staff' if attendance.shift == 'morning' else 'day_staff'
    assigned = CourseSubject.objects.filter(
        subject=attendance.subject, **{shift_field: staff})
    if attendance.course_id is not None:
        assigned = assigned.filter(
            course_id=attendance.course_id, semester=attendance.semester)
    if not assigned.exists():
        return Response({'code': 'NOT_ASSIGNED'}, status=status.HTTP_400_BAD_REQUEST)

    for student_dict in request.data.get('student_ids') or []:
        student = get_object_or_404(Student, admin_id=student_dict.get('id'))
        report = get_object_or_404(
            AttendanceReport, student=student, attendance=attendance)
        report.status = student_dict.get('status')
        report.late = student_dict.get('late', 0)
        report.save()
    attendance.locked = True
    attendance.save()
    return Response({'detail': 'OK'})


@api_view(['GET'])
@permission_classes([IsStudent])
def my_records(request):
    """Student's own records for a subject + date range
    (student_views.student_view_attendance POST)."""
    student = get_object_or_404(Student, admin=request.user)
    params = request.query_params
    subject = get_object_or_404(Subject, id=params.get('subject'))
    try:
        start_date = datetime.strptime(params.get('start_date'), "%Y-%m-%d")
        end_date = datetime.strptime(params.get('end_date'), "%Y-%m-%d")
    except (TypeError, ValueError):
        return Response({'detail': 'start_date and end_date are required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    attendance = Attendance.objects.filter(
        date__range=(start_date, end_date), subject=subject)
    reports = AttendanceReport.objects.filter(
        attendance__in=attendance, student=student)
    return Response([{
        'date': str(r.attendance.date),
        'status': r.status,
    } for r in reports])


# ------------------------------------------- Admin "Fetch Attendance"

@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_courses(request):
    course_data = []
    for course in Course.objects.all():
        course_data.append({
            'course': course_dict(course),
            'student_count': Student.objects.filter(course=course).count(),
        })
    return Response(course_data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    students = Student.objects.filter(course=course).select_related(
        'admin', 'course', 'session').order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    return Response({
        'course': course_dict(course),
        'students': [student_row(s) for s in students],
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def student_summary(request, student_id):
    """Per-subject attendance summary (hod_views.admin_student_attendance)."""
    student = get_object_or_404(Student, id=student_id)
    reports = AttendanceReport.objects.filter(student=student).select_related(
        'attendance', 'attendance__subject')
    summary = {}
    for r in reports:
        subject = r.attendance.subject
        entry = summary.setdefault(
            subject.id, {'subject': subject.name, 'total': 0, 'present': 0})
        entry['total'] += 1
        if r.status:
            entry['present'] += 1
    attendance_summary = []
    for entry in summary.values():
        total = entry['total']
        present = entry['present']
        attendance_summary.append({
            'subject': entry['subject'],
            'total': total,
            'present': present,
            'absent': total - present,
            'percentage': round((present / total) * 100) if total else 0,
        })
    attendance_summary.sort(key=lambda x: x['subject'].lower())
    return Response({
        'student': student_row(student),
        'attendance_summary': attendance_summary,
    })
