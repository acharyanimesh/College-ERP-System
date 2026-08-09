import math
from datetime import date

from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (Attendance, AttendanceReport, Book, BookRequest, Course,
                      CourseSubject, FeePayment, LeaveReportStaff,
                      LeaveReportStudent, LibraryFine, NotificationStaff,
                      NotificationStudent, Session, Staff, Student, Subject)
from .finance import fee_map, paid_map, student_fee_view
from .permissions import IsAccountant, IsAdmin, IsLibrarian, IsStaff, IsStudent
from .serializers import book_request_dict, course_dict, fee_payment_dict


def _attention_alerts(today):
    """Exceptions list: rows appear only when something needs admin action."""
    alerts = []

    pending_staff_leave = LeaveReportStaff.objects.filter(status=0).count()
    if pending_staff_leave:
        alerts.append({
            'type': 'leave_staff',
            'severity': 'warning',
            'icon': 'fas fa-user-clock',
            'message': "%d staff leave application%s awaiting review" % (
                pending_staff_leave, 's' if pending_staff_leave != 1 else ''),
            'link': '/staff/view/leave/',
        })

    pending_student_leave = LeaveReportStudent.objects.filter(status=0).count()
    if pending_student_leave:
        alerts.append({
            'type': 'leave_student',
            'severity': 'warning',
            'icon': 'fas fa-user-clock',
            'message': "%d student leave application%s awaiting review" % (
                pending_student_leave, 's' if pending_student_leave != 1 else ''),
            'link': '/student/view/leave/',
        })

    unfinalized = Attendance.objects.filter(date=today, locked=False).count()
    if unfinalized:
        alerts.append({
            'type': 'attendance_unfinalized',
            'severity': 'warning',
            'icon': 'fas fa-clipboard-check',
            'message': "%d attendance record%s taken today still awaiting confirmation" % (
                unfinalized, 's' if unfinalized != 1 else ''),
            'link': None,
        })

    missing_photos = Student.objects.filter(
        passed_out=False, admin__profile_pic='').count()
    if missing_photos:
        alerts.append({
            'type': 'missing_photo',
            'severity': 'info',
            'icon': 'fas fa-image',
            'message': "%d active student%s missing a profile photo" % (
                missing_photos, 's are' if missing_photos != 1 else ' is'),
            'link': '/student/manage/',
        })

    active_combos = set(
        Student.objects.filter(passed_out=False)
        .values_list('course_id', 'current_semester', 'shift').distinct())
    coverage_gaps = 0
    for cs in CourseSubject.objects.select_related('course', 'subject'):
        for shift, staff_id in (('morning', cs.morning_staff_id), ('day', cs.day_staff_id)):
            if staff_id is None and (cs.course_id, cs.semester, shift) in active_combos:
                coverage_gaps += 1
    if coverage_gaps:
        alerts.append({
            'type': 'coverage_gap',
            'severity': 'danger',
            'icon': 'fas fa-user-slash',
            'message': "%d active class%s missing an assigned teacher" % (
                coverage_gaps, 'es' if coverage_gaps != 1 else ''),
            'link': None,
        })

    for course in Course.objects.all():
        if not course.semesters:
            continue
        if Student.objects.filter(
                course=course, current_semester=course.semesters, passed_out=False).exists():
            alerts.append({
                'type': 'promotion_due',
                'severity': 'info',
                'icon': 'fas fa-user-graduate',
                'message': "%s: Semester %d cohort is ready for graduation" % (
                    course.short_name, course.semesters),
                'link': '/student/manage/course/%d/' % course.id,
            })

    return alerts


def _recent_activity(limit=10):
    """Chronological feed synthesized from timestamps already on Attendance,
    LeaveReport*, Notification*, and new-student records (no audit-log model
    exists in this app, so this is the closest real signal available)."""
    events = []

    for a in Attendance.objects.select_related('subject', 'course').order_by('-created_at')[:limit]:
        events.append((a.created_at, 'fas fa-clipboard-check',
                       "Attendance recorded for %s%s" % (
                           a.subject.name,
                           " (%s)" % a.course.short_name if a.course else '')))

    for l in LeaveReportStaff.objects.exclude(status=0).select_related(
            'staff__admin').order_by('-updated_at')[:limit]:
        verb = 'approved' if l.status == 1 else 'rejected'
        events.append((l.updated_at, 'fas fa-user-clock', "Leave %s for %s %s (Staff)" % (
            verb, l.staff.admin.first_name, l.staff.admin.last_name)))

    for l in LeaveReportStudent.objects.exclude(status=0).select_related(
            'student__admin').order_by('-updated_at')[:limit]:
        verb = 'approved' if l.status == 1 else 'rejected'
        events.append((l.updated_at, 'fas fa-user-graduate', "Leave %s for %s %s (Student)" % (
            verb, l.student.admin.first_name, l.student.admin.last_name)))

    for n in NotificationStaff.objects.select_related('staff__admin').order_by('-created_at')[:limit]:
        events.append((n.created_at, 'fas fa-bell', "Notification sent to %s %s (Staff)" % (
            n.staff.admin.first_name, n.staff.admin.last_name)))

    for n in NotificationStudent.objects.select_related('student__admin').order_by('-created_at')[:limit]:
        events.append((n.created_at, 'fas fa-bell', "Notification sent to %s %s (Student)" % (
            n.student.admin.first_name, n.student.admin.last_name)))

    for s in Student.objects.select_related('admin').order_by('-admin__created_at')[:limit]:
        events.append((s.admin.created_at, 'fas fa-user-plus', "New student registered: %s %s" % (
            s.admin.first_name, s.admin.last_name)))

    events.sort(key=lambda e: e[0], reverse=True)
    return [{
        'time': time.strftime('%I:%M %p'),
        'date': time.strftime('%b. %d, %Y'),
        'icon': icon,
        'text': text,
    } for time, icon, text in events[:limit]]


def _academic_progress():
    """Per-course semester occupancy (Cascade Promotion Monitor) + a small
    calendar of near-term academic milestones."""
    courses = []
    for course in Course.objects.all():
        total_semesters = course.semesters or 0
        semesters = []
        for sem in range(1, total_semesters + 1):
            count = Student.objects.filter(
                course=course, current_semester=sem, passed_out=False).count()
            if count:
                semesters.append({'number': sem, 'student_count': count})
        ready_to_pass_out = bool(total_semesters) and Student.objects.filter(
            course=course, current_semester=total_semesters, passed_out=False).exists()
        courses.append({
            'course': course_dict(course),
            'semesters': semesters,
            'ready_to_pass_out': ready_to_pass_out,
        })

    calendar = []
    for session in Session.objects.filter(
            student__passed_out=False).distinct().order_by('end_year'):
        days_left = (session.end_year - date.today()).days
        if 0 <= days_left <= 120:
            calendar.append({
                'label': "Session %d-%d intake ends" % (
                    session.start_year.year, session.end_year.year),
                'days_left': days_left,
            })
    for course in Course.objects.all():
        if course.semesters and Student.objects.filter(
                course=course, current_semester=course.semesters, passed_out=False).exists():
            calendar.append({
                'label': "%s - Semester %d ready to pass out" % (
                    course.short_name, course.semesters),
                'days_left': None,
            })
    calendar.sort(key=lambda c: (c['days_left'] is None, c['days_left']))

    return {'courses': courses, 'calendar': calendar}


def _health_trends(today):
    """Aggregate percentages + small trend series (replaces the old per-slice
    donut/bar charts, which stopped being readable once real data volume hit
    the app)."""
    today_reports = AttendanceReport.objects.filter(attendance__date=today)
    total_today = today_reports.count()
    present_today = today_reports.filter(status=True, late=False).count()
    late_today = today_reports.filter(status=True, late=True).count()
    absent_today = today_reports.filter(status=False).count()

    def pct(n):
        return round((n / total_today) * 100) if total_today else 0

    classes_today_qs = Attendance.objects.filter(date=today)
    classes_total = classes_today_qs.count()
    classes_completed = classes_today_qs.filter(locked=True).count()

    total_staff = Staff.objects.count()
    total_students = Student.objects.filter(passed_out=False).count()
    student_staff_ratio = round(total_students / total_staff, 1) if total_staff else 0

    active_combos = Student.objects.filter(passed_out=False).values(
        'course_id', 'current_semester', 'shift').distinct().count()
    avg_cohort_size = round(total_students / active_combos, 1) if active_combos else 0

    intake_trend = []
    for session in Session.objects.filter(
            student__passed_out=False).distinct().order_by('-start_year')[:3]:
        count = Student.objects.filter(session=session, passed_out=False).count()
        intake_trend.append({'label': str(session.start_year.year), 'count': count})
    intake_trend.reverse()

    # Last 5 dates that actually had attendance taken (not just the last 5
    # calendar days, which would show false zero dips on weekends).
    recent_dates = list(
        Attendance.objects.filter(date__lte=today).order_by('-date')
        .values_list('date', flat=True).distinct()[:5])
    recent_dates.reverse()
    weekly_attendance = []
    for day in recent_dates:
        day_reports = AttendanceReport.objects.filter(attendance__date=day)
        total = day_reports.count()
        present = day_reports.filter(status=True).count()
        weekly_attendance.append({
            'label': day.strftime('%a %b %d'),
            'present_pct': round((present / total) * 100) if total else 0,
        })

    return {
        'today_attendance': {
            'present_pct': pct(present_today),
            'absent_pct': pct(absent_today),
            'late_pct': pct(late_today),
            'total_records': total_today,
        },
        'classes_completed': {'done': classes_completed, 'total': classes_total},
        'student_staff_ratio': student_staff_ratio,
        'avg_cohort_size': avg_cohort_size,
        'intake_trend': intake_trend,
        'weekly_attendance': weekly_attendance,
    }


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_home(request):
    """Operational dashboard: KPI tiles, exceptions needing attention, a
    recent-activity feed, academic progress, and health trends — a single
    round trip shaped for the React dashboard to render with zero
    client-side calculation."""
    today = date.today()

    kpi_metrics = {
        'total_students': Student.objects.filter(passed_out=False).count(),
        'total_staff': Staff.objects.count(),
        'total_subjects': Subject.objects.count(),
        'total_courses': Course.objects.count(),
        'active_sessions': Session.objects.filter(
            student__passed_out=False).distinct().count(),
        'pending_leave': (LeaveReportStaff.objects.filter(status=0).count()
                          + LeaveReportStudent.objects.filter(status=0).count()),
        'classes_today': Attendance.objects.filter(date=today).count(),
        'notifications_today': (
            NotificationStaff.objects.filter(created_at__date=today).count()
            + NotificationStudent.objects.filter(created_at__date=today).count()),
    }

    return Response({
        'kpi_metrics': kpi_metrics,
        'attention_alerts': _attention_alerts(today),
        'recent_activity': _recent_activity(),
        'academic_progress': _academic_progress(),
        'health_trends': _health_trends(today),
    })


@api_view(['GET'])
@permission_classes([IsStaff])
def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    staff_courses = staff.taught_courses
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
@permission_classes([IsLibrarian])
def librarian_home(request):
    """Circulation desk at a glance: what needs deciding, what is out, what is
    late, plus the shape of the catalogue behind it."""
    books = list(Book.objects.all())
    total_copies = sum(b.total_copies for b in books)

    by_category = {}
    for book in books:
        label = (book.category or '').strip() or 'Uncategorised'
        by_category[label] = by_category.get(label, 0) + 1

    issued = BookRequest.objects.filter(
        status=BookRequest.ISSUED).select_related('book', 'student__admin')
    overdue = [r for r in issued if r.days_overdue]

    pending = BookRequest.objects.filter(
        status=BookRequest.PENDING).select_related(
        'book', 'student__admin', 'student__course')

    return Response({
        'total_titles': len(books),
        'total_copies': total_copies,
        'copies_out': sum(b.copies_out for b in books),
        'pending_requests': pending.count(),
        'awaiting_pickup': BookRequest.objects.filter(
            status=BookRequest.APPROVED).count(),
        'books_on_loan': issued.count(),
        'overdue_count': len(overdue),
        'fines_outstanding': sum(r.fine for r in overdue),
        'category_breakdown': sorted(
            ({'label': k, 'count': v} for k, v in by_category.items()),
            key=lambda c: -c['count']),
        'recent_requests': [
            book_request_dict(r, for_librarian=True) for r in pending[:8]],
        'overdue_loans': [
            book_request_dict(r, for_librarian=True) for r in sorted(
                overdue, key=lambda r: -r.days_overdue)[:8]],
    })


@api_view(['GET'])
@permission_classes([IsStudent])
def student_home(request):
    """Everything the student dashboard shows is scoped to the semester the
    student is currently enrolled in — a 6th-semester student has no use for
    the subjects and attendance bars of the five semesters behind them."""
    student = get_object_or_404(Student, admin=request.user)
    current_semester = student.current_semester
    # Subjects of the student's course *at their current semester*, with the
    # teacher assigned for their shift — one pass, reused for both the
    # subject-wise attendance chart and the "My Subjects" table.
    semester_subjects = CourseSubject.objects.filter(
        course=student.course, semester=current_semester).select_related(
        'subject', 'morning_staff__admin', 'day_staff__admin').order_by(
        'subject__name')

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
    course_subjects = []
    for cs in semester_subjects:
        attendance = Attendance.objects.filter(subject=cs.subject)
        data_present.append(AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count())
        data_absent.append(AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count())
        subject_name.append(cs.subject.name)
        teacher = cs.staff_for_shift(student.shift)
        course_subjects.append({
            'subject_name': cs.subject.name,
            'teacher_name': str(teacher) if teacher else None,
        })

    return Response({
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': len(course_subjects),
        'current_semester': current_semester,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'course_subjects': course_subjects,
    })


@api_view(['GET'])
@permission_classes([IsAccountant])
def accountant_home(request):
    """The finance desk at a glance: what the term should bring in, what has
    come in, what is still owed — plus the shape of it per course and a read on
    the library fines the desk also has visibility of."""
    today = date.today()
    fees, paids = fee_map(), paid_map()

    students = Student.objects.filter(passed_out=False).select_related(
        'admin', 'course')
    rows = [student_fee_view(s, fees, paids) for s in students]

    term_expected = sum(r['expected'] for r in rows)
    term_collected = sum(r['paid'] for r in rows)
    term_outstanding = sum(r['outstanding'] for r in rows)
    status_counts = {'paid': 0, 'partial': 0, 'unpaid': 0, 'unbilled': 0}
    for r in rows:
        status_counts[r['status']] += 1

    # Per-course roll-up of the same term figures.
    by_course = {}
    for r in rows:
        c = by_course.setdefault(r['course_short_name'], {
            'course': r['course_short_name'], 'students': 0,
            'expected': 0, 'collected': 0, 'outstanding': 0})
        c['students'] += 1
        c['expected'] += r['expected']
        c['collected'] += r['paid']
        c['outstanding'] += r['outstanding']

    all_time = FeePayment.objects.aggregate(total=Sum('amount'))['total'] or 0
    collected_today = FeePayment.objects.filter(
        created_at__date=today).aggregate(total=Sum('amount'))['total'] or 0

    recent = FeePayment.objects.select_related(
        'student__admin', 'student__course')[:8]

    # Library fines the desk also has an eye on: what has been receipted, and
    # what is still owed on loans currently out and overdue.
    lib_fines_collected = LibraryFine.objects.filter(
        kind=LibraryFine.PAID).aggregate(total=Sum('amount'))['total'] or 0
    issued = BookRequest.objects.filter(status=BookRequest.ISSUED)
    lib_fines_outstanding = sum(r.fine_outstanding for r in issued)

    return Response({
        'total_students': len(rows),
        'term_expected': term_expected,
        'term_collected': term_collected,
        'term_outstanding': term_outstanding,
        'collection_rate': round((term_collected / term_expected) * 100)
                           if term_expected else 0,
        'collected_all_time': all_time,
        'collected_today': collected_today,
        'status_counts': status_counts,
        'by_course': sorted(by_course.values(), key=lambda c: -c['outstanding']),
        'recent_payments': [
            fee_payment_dict(p, for_accountant=True) for p in recent],
        'library_fines_collected': lib_fines_collected,
        'library_fines_outstanding': lib_fines_outstanding,
    })
