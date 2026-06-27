import json
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Q, F
from django.db.models.functions import Lower
from datetime import date as date_cls
from django.shortcuts import (HttpResponse, HttpResponseRedirect,
                              get_object_or_404, redirect, render)
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView

from .forms import *
from .models import *


def admin_home(request):
    total_staff = Staff.objects.all().count()
    total_students = Student.objects.filter(passed_out=False).count()
    subjects = Subject.objects.all()
    total_subject = subjects.count()
    total_course = Course.objects.all().count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name[:7])
        attendance_list.append(attendance_count)

    # Total Subjects and students in Each Course
    course_all = Course.objects.all()
    course_name_list = []
    subject_count_list = []
    student_count_list_in_course = []

    for course in course_all:
        subjects = Subject.objects.filter(courses=course).count()
        students = Student.objects.filter(course_id=course.id, passed_out=False).count()
        course_name_list.append(course.short_name)
        subject_count_list.append(subjects)
        student_count_list_in_course.append(students)
    
    subject_all = Subject.objects.all()
    subject_list = []
    student_count_list_in_subject = []
    for subject in subject_all:
        student_count = Student.objects.filter(course__in=subject.courses.all()).count()
        subject_list.append(subject.name)
        student_count_list_in_subject.append(student_count)


    # For Students
    student_attendance_present_list=[]
    student_attendance_leave_list=[]
    student_name_list=[]

    students = Student.objects.all()
    for student in students:
        
        attendance = AttendanceReport.objects.filter(student_id=student.id, status=True).count()
        absent = AttendanceReport.objects.filter(student_id=student.id, status=False).count()
        leave = LeaveReportStudent.objects.filter(student_id=student.id, status=1).count()
        student_attendance_present_list.append(attendance)
        student_attendance_leave_list.append(leave+absent)
        student_name_list.append(student.admin.first_name)

    context = {
        'page_title': "Administrative Dashboard",
        'total_students': total_students,
        'total_staff': total_staff,
        'total_course': total_course,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'student_attendance_present_list': student_attendance_present_list,
        'student_attendance_leave_list': student_attendance_leave_list,
        "student_name_list": student_name_list,
        "student_count_list_in_subject": student_count_list_in_subject,
        "student_count_list_in_course": student_count_list_in_course,
        "course_name_list": course_name_list,

    }
    return render(request, 'hod_template/home_content.html', context)


def add_staff(request):
    form = StaffForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'page_title': 'Add Staff'}
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password')
            address_line1 = form.cleaned_data.get('address_line1')
            address_line2 = form.cleaned_data.get('address_line2')
            city = form.cleaned_data.get('city')
            province = form.cleaned_data.get('province')
            staff_id = form.cleaned_data.get('staff_id')
            courses = form.cleaned_data.get('courses')
            teaches_morning = form.cleaned_data.get('teaches_morning')
            teaches_day = form.cleaned_data.get('teaches_day')
            phone_number = form.cleaned_data.get('phone_number')
            date_of_birth = form.cleaned_data.get('date_of_birth')
            passport = request.FILES.get('profile_pic')
            passport_url = ''
            if passport:
                fs = FileSystemStorage()
                filename = fs.save(passport.name, passport)
                passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=2, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address_line1 = address_line1
                user.address_line2 = address_line2
                user.city = city
                user.province = province
                user.address = ", ".join(filter(None, [address_line1, address_line2, city, province]))
                user.phone_number = phone_number
                user.date_of_birth = date_of_birth
                user.save()
                staff = user.staff
                staff.staff_id = staff_id
                staff.teaches_morning = teaches_morning
                staff.teaches_day = teaches_day
                staff.courses.set(courses)
                staff.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_staff'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Please fulfil all requirements")

    return render(request, 'hod_template/add_staff_template.html', context)


def add_student(request):
    student_form = StudentForm(request.POST or None, request.FILES or None)
    context = {'form': student_form, 'page_title': 'Add Student'}
    if request.method == 'POST':
        if student_form.is_valid():
            first_name = student_form.cleaned_data.get('first_name')
            last_name = student_form.cleaned_data.get('last_name')
            email = student_form.cleaned_data.get('email')
            gender = student_form.cleaned_data.get('gender')
            password = student_form.cleaned_data.get('password')
            address_line1 = student_form.cleaned_data.get('address_line1')
            address_line2 = student_form.cleaned_data.get('address_line2')
            city = student_form.cleaned_data.get('city')
            province = student_form.cleaned_data.get('province')
            phone_number = student_form.cleaned_data.get('phone_number')
            date_of_birth = student_form.cleaned_data.get('date_of_birth')
            registration_number = student_form.cleaned_data.get('registration_number')
            roll_number = student_form.cleaned_data.get('roll_number')
            course = student_form.cleaned_data.get('course')
            session = student_form.cleaned_data.get('session')
            shift = student_form.cleaned_data.get('shift')
            new_sem = student_form.cleaned_data.get('current_semester') or 1

            # Once a (course, session) batch has progressed past Semester 1, that
            # session's Semester 1 is closed: new students of this session can only
            # join the batch at its CURRENT semester, not back in Sem 1. (Sem 1 is
            # still open while the batch is actually running in Sem 1.)
            if new_sem == 1 and course is not None and session is not None:
                cohort = Student.objects.filter(
                    course=course, session=session, passed_out=False)
                if cohort.exists() and not cohort.filter(current_semester=1).exists():
                    cohort_sem = cohort.order_by('current_semester').first().current_semester
                    messages.error(
                        request,
                        "The %s batch of %s has already progressed to Semester %d. "
                        "New students for this session can't be added to Semester 1 — "
                        "set Current Semester to %d instead."
                        % (session, course.short_name, cohort_sem, cohort_sem))
                    return render(request, 'hod_template/add_student_template.html', context)

            passport = request.FILES.get('profile_pic')
            passport_url = ''
            if passport:
                fs = FileSystemStorage()
                filename = fs.save(passport.name, passport)
                passport_url = fs.url(filename)
            try:
                promo_msg = None
                with transaction.atomic():
                    # New-session intake: when the FIRST first-year of a brand-new
                    # (newer) session is added to a course that already has older
                    # batches, roll the whole course up one first (cascade, final
                    # sem passes out) so the new intake starts in an empty Sem 1.
                    # Keyed off the session being new to the course — NOT off Sem 1
                    # being occupied — so it still fires once Sem 1 has been vacated.
                    if (new_sem == 1 and course is not None
                            and session is not None and session.start_year):
                        already_this_session = Student.objects.filter(
                            course=course, session=session, passed_out=False).exists()
                        older_exists = Student.objects.filter(
                            course=course, passed_out=False,
                            session__start_year__lt=session.start_year).exists()
                        if older_exists and not already_this_session:
                            promoted, graduated = _cascade_promote_course(course, 1)
                            bits = []
                            if promoted:
                                bits.append("%d existing student(s) promoted up one semester" % promoted)
                            if graduated:
                                bits.append("%d final-semester student(s) passed out" % graduated)
                            if bits:
                                promo_msg = "New intake for %s — %s." % (course.short_name, "; ".join(bits))

                    user = CustomUser.objects.create_user(
                        email=email, password=password, user_type=3, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                    user.gender = gender
                    user.address_line1 = address_line1
                    user.address_line2 = address_line2
                    user.city = city
                    user.province = province
                    user.address = ", ".join(filter(None, [address_line1, address_line2, city, province]))
                    user.phone_number = phone_number
                    user.date_of_birth = date_of_birth
                    user.save()
                    student = user.student
                    student.registration_number = registration_number
                    student.roll_number = roll_number
                    student.session = session
                    student.course = course
                    student.shift = shift
                    student.current_semester = new_sem
                    student.save()
                messages.success(request, "Successfully Added")
                if promo_msg:
                    messages.info(request, promo_msg)
                return redirect(reverse('add_student'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'hod_template/add_student_template.html', context)


def add_course(request):
    form = CourseForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Course'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                course = Course()
                course.name = name
                course.abbreviation = form.cleaned_data.get('abbreviation') or ''
                course.semesters = form.cleaned_data.get('semesters')
                course.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_course'))
            except:
                messages.error(request, "Could Not Add")
        else:
            messages.error(request, "Could Not Add")
    return render(request, 'hod_template/add_course_template.html', context)


def add_subject(request):
    form = AddSubjectForm(request.POST or None)
    courses = Course.objects.all().order_by('name')
    # course_id -> submitted semester (empty string means "not in this course")
    if request.method == 'POST':
        submitted = {c.id: (request.POST.get('semester_%s' % c.id) or '').strip() for c in courses}
    else:
        submitted = {c.id: '' for c in courses}
    course_rows = [{'course': c, 'semester': submitted.get(c.id, '')} for c in courses]
    context = {
        'form': form,
        'course_rows': course_rows,
        'page_title': 'Add Subject'
    }
    if request.method == 'POST':
        chosen = {c: submitted[c.id] for c in courses if submitted[c.id]}
        if not form.is_valid():
            messages.error(request, "Fill Form Properly")
        elif not chosen:
            messages.error(request, "Assign the subject to at least one course by entering its semester.")
        else:
            try:
                with transaction.atomic():
                    subject = form.save()
                    for course, sem in chosen.items():
                        CourseSubject.objects.create(course=course, subject=subject, semester=sem)
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_subject'))
            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
    return render(request, 'hod_template/add_subject_template.html', context)


def manage_staff(request):
    allStaff = CustomUser.objects.filter(user_type=2).order_by(
        Lower('first_name'), Lower('last_name'))
    context = {
        'allStaff': allStaff,
        'page_title': 'Manage Staff'
    }
    return render(request, "hod_template/manage_staff.html", context)


def staff_details(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    # Teaching assignments: subject + course + semester + which shift(s) this
    # staff teaches it in.
    cs_qs = CourseSubject.objects.filter(
        Q(morning_staff=staff) | Q(day_staff=staff)).select_related(
        'subject', 'course').order_by(Lower('subject__name'))
    assignments = []
    for cs in cs_qs:
        shifts = []
        if cs.morning_staff_id == staff.id:
            shifts.append('Morning')
        if cs.day_staff_id == staff.id:
            shifts.append('Day')
        assignments.append({'cs': cs, 'shifts': ", ".join(shifts)})
    courses = Course.objects.filter(
        Q(coursesubject__morning_staff=staff) | Q(coursesubject__day_staff=staff)).distinct()
    context = {
        'staff': staff,
        'courses': courses,
        'assignments': assignments,
        'subject_count': cs_qs.values('subject').distinct().count(),
        'page_title': 'Staff Details - ' + staff.admin.first_name + ' ' + staff.admin.last_name
    }
    return render(request, "hod_template/staff_details.html", context)


def manage_student(request):
    courses = Course.objects.all()
    course_data = []
    for course in courses:
        student_count = Student.objects.filter(course=course, passed_out=False).count()
        course_data.append({'course': course, 'student_count': student_count})
    context = {
        'course_data': course_data,
        'page_title': 'Manage Students - Select Course'
    }
    return render(request, "hod_template/manage_student.html", context)


def manage_student_by_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Pick a semester before drilling into shifts. Show every configured semester
    # plus a catch-all for any students whose semester is beyond that range.
    total_semesters = course.semesters or 0
    semester_data = []
    for sem in range(1, total_semesters + 1):
        count = Student.objects.filter(
            course=course, current_semester=sem, passed_out=False).count()
        semester_data.append({'number': sem, 'student_count': count})
    context = {
        'course': course,
        'total_semesters': total_semesters,
        'semester_data': semester_data,
        'page_title': 'Manage Students - ' + course.short_name + ' (Select Semester)'
    }
    return render(request, "hod_template/student_semester_list.html", context)


def manage_student_by_course_semester(request, course_id, semester):
    course = get_object_or_404(Course, id=course_id)
    # Every course runs both shifts — let the HOD pick one before listing students.
    shift_data = []
    for value, label in SHIFT_CHOICES:
        count = Student.objects.filter(
            course=course, current_semester=semester, shift=value, passed_out=False).count()
        shift_data.append({'value': value, 'label': label, 'student_count': count})
    context = {
        'course': course,
        'semester': semester,
        'shift_data': shift_data,
        'is_final_semester': bool(course.semesters) and semester >= course.semesters,
        'page_title': 'Manage Students - %s - Semester %s (Select Shift)' % (course.short_name, semester)
    }
    return render(request, "hod_template/student_shift_list.html", context)


def manage_student_by_course_semester_shift(request, course_id, semester, shift):
    course = get_object_or_404(Course, id=course_id)
    shift_label = dict(SHIFT_CHOICES).get(shift, shift)
    students = CustomUser.objects.filter(
        user_type=3, student__course=course, student__current_semester=semester,
        student__shift=shift, student__passed_out=False).order_by(
        Lower('first_name'), Lower('last_name'))
    context = {
        'students': students,
        'course': course,
        'semester': semester,
        'shift': shift,
        'shift_label': shift_label,
        'is_final_semester': bool(course.semesters) and semester >= course.semesters,
        'page_title': 'Manage Students - %s - Semester %s (%s)' % (course.short_name, semester, shift_label)
    }
    return render(request, "hod_template/student_list_by_course.html", context)


def _cascade_promote_course(course, from_semester):
    """Promote every active student of `course` whose semester >= from_semester up
    by one; final-semester students are marked passed out (kept on record).
    Returns (promoted_count, graduated_count). Caller wraps this in a transaction."""
    final = course.semesters
    if not final:
        return (0, 0)
    grads = Student.objects.filter(
        course=course, current_semester=final, passed_out=False)
    graduated = grads.count()
    if graduated:
        grads.update(passed_out=True, passed_out_date=date_cls.today())
    # Updating off the OLD value (highest-to-lowest is irrelevant for a single
    # bulk +1) keeps each batch separate, so a lower one never mixes into the next.
    promoted = Student.objects.filter(
        course=course, passed_out=False,
        current_semester__gte=from_semester, current_semester__lt=final
    ).update(current_semester=F('current_semester') + 1)
    return (promoted, graduated)


def promote_class(request, course_id, semester):
    """Cascading promotion: promoting semester N advances EVERY semester >= N in
    this course (both shifts) by one, so a lower batch never mixes into the batch
    above it. Students finishing the final semester are marked as passed out
    instead of moving to a non-existent next semester."""
    course = get_object_or_404(Course, id=course_id)
    if request.method != 'POST':
        return redirect(reverse('manage_student_by_course', args=[course.id]))

    if not course.semesters:
        messages.error(request, "Set the number of semesters for %s first." % course.short_name)
        return redirect(reverse('manage_student_by_course', args=[course.id]))

    with transaction.atomic():
        promoted, graduated = _cascade_promote_course(course, semester)

    parts = []
    if promoted:
        parts.append("promoted %d student(s) (Semester %d and above moved up one)" % (promoted, semester))
    if graduated:
        parts.append("marked %d final-semester student(s) as passed out" % graduated)
    if parts:
        messages.success(request, ("In %s: " % course.short_name) + "; ".join(parts) + ".")
    else:
        messages.info(request, "No students to promote from Semester %d upward in %s." % (semester, course.short_name))
    return redirect(reverse('manage_student_by_course', args=[course.id]))


def passed_out_students(request):
    """Courses that have passed-out (graduated) students, with counts."""
    course_data = []
    for course in Course.objects.all():
        count = Student.objects.filter(course=course, passed_out=True).count()
        course_data.append({'course': course, 'student_count': count})
    context = {
        'course_data': course_data,
        'page_title': 'Passed Out Students - Select Course'
    }
    return render(request, "hod_template/passed_out_course_list.html", context)


def passed_out_by_course(request, course_id):
    """Sessions (intakes) under which this course has passed-out students."""
    course = get_object_or_404(Course, id=course_id)
    grads = Student.objects.filter(course=course, passed_out=True)
    session_ids = grads.values_list('session', flat=True).distinct()
    session_data = []
    for session in Session.objects.filter(id__in=session_ids).order_by('start_year'):
        count = grads.filter(session=session).count()
        session_data.append({'session': session, 'student_count': count})
    # Students with no session recorded still need a home.
    no_session_count = grads.filter(session__isnull=True).count()
    context = {
        'course': course,
        'session_data': session_data,
        'no_session_count': no_session_count,
        'page_title': 'Passed Out Students - ' + course.short_name + ' (Select Session)'
    }
    return render(request, "hod_template/passed_out_session_list.html", context)


def passed_out_by_session(request, course_id, session_id):
    """Passed-out students of a course in one session — both shifts in one table."""
    course = get_object_or_404(Course, id=course_id)
    session = get_object_or_404(Session, id=session_id)
    students = Student.objects.filter(
        course=course, session=session, passed_out=True).select_related('admin').order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    context = {
        'course': course,
        'session': session,
        'students': students,
        'page_title': 'Passed Out Students - %s (%s)' % (course.short_name, session)
    }
    return render(request, "hod_template/passed_out_student_list.html", context)


def student_details(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    context = {
        'student': student,
        'page_title': 'Student Details - ' + student.admin.first_name + ' ' + student.admin.last_name
    }
    return render(request, "hod_template/student_details.html", context)


def manage_course(request):
    courses = Course.objects.all()
    context = {
        'courses': courses,
        'page_title': 'Manage Courses'
    }
    return render(request, "hod_template/manage_course.html", context)



def manage_subject_by_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    total_semesters = course.semesters or 0
    semester_data = []
    for sem in range(1, total_semesters + 1):
        subject_count = CourseSubject.objects.filter(course=course, semester=sem).count()
        semester_data.append({'number': sem, 'subject_count': subject_count})
    context = {
        'course': course,
        'semester_data': semester_data,
        'page_title': 'Manage Subjects - ' + course.short_name + ' (Select Semester)'
    }
    return render(request, "hod_template/course_semester_list.html", context)


def manage_subject_by_semester(request, course_id, semester):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        code = format_subject_code(request.POST.get('code'))
        credit_hours = (request.POST.get('credit_hours') or '').strip()
        if not name:
            messages.error(request, "Please enter a subject name.")
        else:
            try:
                subject = Subject.objects.create(
                    name=name,
                    code=code,
                    credit_hours=credit_hours or None)
                CourseSubject.objects.create(
                    course=course, subject=subject, semester=semester)
                messages.success(request, "Subject '%s' added to %s - Semester %s." % (name, course.short_name, semester))
            except Exception as e:
                messages.error(request, "Could not add subject: " + str(e))
        return redirect(reverse('manage_subject_by_semester', args=[course.id, semester]))
    subjects = Subject.objects.filter(
        coursesubject__course=course, coursesubject__semester=semester).order_by(Lower('name'))
    context = {
        'subjects': subjects,
        'course': course,
        'semester': semester,
        'page_title': 'Manage Subjects - ' + course.short_name + ' - Semester ' + str(semester)
    }
    return render(request, "hod_template/subject_list_by_course.html", context)


def subject_details(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    # Per-course rows, each carrying its semester and the morning/day teacher.
    course_semesters = CourseSubject.objects.filter(subject=subject).select_related(
        'course', 'morning_staff__admin', 'day_staff__admin')
    context = {
        'subject': subject,
        'course_semesters': course_semesters,
        'page_title': 'Subject Details - ' + subject.name
    }
    return render(request, "hod_template/subject_details.html", context)


def edit_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    form = StaffForm(request.POST or None, instance=staff)
    context = {
        'form': form,
        'staff_id': staff_id,
        'page_title': 'Edit Staff'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            address_line1 = form.cleaned_data.get('address_line1')
            address_line2 = form.cleaned_data.get('address_line2')
            city = form.cleaned_data.get('city')
            province = form.cleaned_data.get('province')
            staff_id = form.cleaned_data.get('staff_id')
            courses = form.cleaned_data.get('courses')
            teaches_morning = form.cleaned_data.get('teaches_morning')
            teaches_day = form.cleaned_data.get('teaches_day')
            phone_number = form.cleaned_data.get('phone_number')
            date_of_birth = form.cleaned_data.get('date_of_birth')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=staff.admin.id)
                user.email = email
                if password != None:
                    user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address_line1 = address_line1
                user.address_line2 = address_line2
                user.city = city
                user.province = province
                user.address = ", ".join(filter(None, [address_line1, address_line2, city, province]))
                user.phone_number = phone_number
                user.date_of_birth = date_of_birth
                staff.staff_id = staff_id
                staff.teaches_morning = teaches_morning
                staff.teaches_day = teaches_day
                staff.courses.set(courses)
                user.save()
                staff.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_staff', args=[staff.id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please fil form properly")
    return render(request, "hod_template/edit_staff_template.html", context)


def assign_staff_subjects(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    if request.method == 'POST':
        # Per-shift assignment: a teacher may only claim a FREE slot (or one
        # already theirs). A slot held by another teacher stays untouched —
        # enforcing one teacher per (course, subject, shift).
        selected_morning = set(request.POST.getlist('morning'))
        selected_day = set(request.POST.getlist('day'))
        for cs in CourseSubject.objects.all():
            sid = str(cs.id)
            changed = False
            # Morning slot
            if sid in selected_morning:
                if cs.morning_staff_id in (None, staff.id):
                    cs.morning_staff = staff; changed = True
            elif cs.morning_staff_id == staff.id:
                cs.morning_staff = None; changed = True
            # Day slot
            if sid in selected_day:
                if cs.day_staff_id in (None, staff.id):
                    cs.day_staff = staff; changed = True
            elif cs.day_staff_id == staff.id:
                cs.day_staff = None; changed = True
            if changed:
                cs.save()
        messages.success(request, "Teaching assignments updated successfully")
        return redirect(reverse('assign_staff_subjects', args=[staff_id]))
    rows = []
    for cs in CourseSubject.objects.select_related(
            'subject', 'course', 'morning_staff__admin', 'day_staff__admin').order_by(
            Lower('course__name'), 'semester', Lower('subject__name')):
        rows.append({
            'cs': cs,
            'morning_mine': cs.morning_staff_id == staff.id,
            'morning_other': cs.morning_staff if (cs.morning_staff_id and cs.morning_staff_id != staff.id) else None,
            'day_mine': cs.day_staff_id == staff.id,
            'day_other': cs.day_staff if (cs.day_staff_id and cs.day_staff_id != staff.id) else None,
        })
    context = {
        'staff': staff,
        'rows': rows,
        'page_title': 'Assign Subjects - ' + staff.admin.first_name + ' ' + staff.admin.last_name,
    }
    return render(request, "hod_template/assign_staff_subjects.html", context)


def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    form = StudentForm(request.POST or None, instance=student)
    context = {
        'form': form,
        'student_id': student_id,
        'page_title': 'Edit Student'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            address_line1 = form.cleaned_data.get('address_line1')
            address_line2 = form.cleaned_data.get('address_line2')
            city = form.cleaned_data.get('city')
            province = form.cleaned_data.get('province')
            phone_number = form.cleaned_data.get('phone_number')
            date_of_birth = form.cleaned_data.get('date_of_birth')
            registration_number = form.cleaned_data.get('registration_number')
            roll_number = form.cleaned_data.get('roll_number')
            course = form.cleaned_data.get('course')
            session = form.cleaned_data.get('session')
            shift = form.cleaned_data.get('shift')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=student.admin.id)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.email = email
                if password != None:
                    user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address_line1 = address_line1
                user.address_line2 = address_line2
                user.city = city
                user.province = province
                user.address = ", ".join(filter(None, [address_line1, address_line2, city, province]))
                user.phone_number = phone_number
                user.date_of_birth = date_of_birth
                student.registration_number = registration_number
                student.roll_number = roll_number
                student.session = session
                student.course = course
                student.shift = shift
                student.current_semester = form.cleaned_data.get('current_semester') or 1
                user.save()
                student.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_student', args=[student_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please Fill Form Properly!")
    else:
        return render(request, "hod_template/edit_student_template.html", context)


def edit_course(request, course_id):
    instance = get_object_or_404(Course, id=course_id)
    form = CourseForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'course_id': course_id,
        'page_title': 'Edit Course'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                course = Course.objects.get(id=course_id)
                course.name = name
                course.abbreviation = form.cleaned_data.get('abbreviation') or ''
                course.semesters = form.cleaned_data.get('semesters')
                course.save()
                messages.success(request, "Successfully Updated")
            except:
                messages.error(request, "Could Not Update")
        else:
            messages.error(request, "Could Not Update")

    return render(request, 'hod_template/edit_course_template.html', context)


def edit_subject(request, subject_id):
    instance = get_object_or_404(Subject, id=subject_id)
    form = SubjectForm(request.POST or None, instance=instance)
    courses = Course.objects.all().order_by('name')
    existing = {cs.course_id: cs.semester for cs in CourseSubject.objects.filter(subject=instance)}
    if request.method == 'POST':
        submitted = {c.id: (request.POST.get('semester_%s' % c.id) or '').strip() for c in courses}
    else:
        submitted = {c.id: (str(existing[c.id]) if existing.get(c.id) is not None else '') for c in courses}
    course_rows = [{'course': c, 'semester': submitted.get(c.id, '')} for c in courses]
    context = {
        'form': form,
        'subject_id': subject_id,
        'course_rows': course_rows,
        'page_title': 'Edit Subject'
    }
    if request.method == 'POST':
        chosen = {c.id: submitted[c.id] for c in courses if submitted[c.id]}
        if not form.is_valid():
            messages.error(request, "Fill Form Properly")
        elif not chosen:
            messages.error(request, "Assign the subject to at least one course by entering its semester.")
        else:
            try:
                with transaction.atomic():
                    subject = form.save()
                    for c in courses:
                        sem = submitted[c.id]
                        if sem:
                            CourseSubject.objects.update_or_create(
                                course=c, subject=subject, defaults={'semester': sem})
                        else:
                            CourseSubject.objects.filter(course=c, subject=subject).delete()
                messages.success(request, "Successfully Updated")
                next_url = request.GET.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(reverse('edit_subject', args=[subject_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
    return render(request, 'hod_template/edit_subject_template.html', context)


def add_session(request):
    form = SessionForm(request.POST or None)
    context = {'form': form, 'page_title': 'Add Session'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Session Created")
                return redirect(reverse('add_session'))
            except Exception as e:
                messages.error(request, 'Could Not Add ' + str(e))
        else:
            messages.error(request, 'Fill Form Properly ')
    return render(request, "hod_template/add_session_template.html", context)


def manage_session(request):
    sessions = Session.objects.all()
    context = {'sessions': sessions, 'page_title': 'Manage Sessions'}
    return render(request, "hod_template/manage_session.html", context)


def edit_session(request, session_id):
    instance = get_object_or_404(Session, id=session_id)
    form = SessionForm(request.POST or None, instance=instance)
    context = {'form': form, 'session_id': session_id,
               'page_title': 'Edit Session'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Session Updated")
                return redirect(reverse('edit_session', args=[session_id]))
            except Exception as e:
                messages.error(
                    request, "Session Could Not Be Updated " + str(e))
                return render(request, "hod_template/edit_session_template.html", context)
        else:
            messages.error(request, "Invalid Form Submitted ")
            return render(request, "hod_template/edit_session_template.html", context)

    else:
        return render(request, "hod_template/edit_session_template.html", context)


@csrf_exempt
def check_email_availability(request):
    email = request.POST.get("email")
    try:
        user = CustomUser.objects.filter(email=email).exists()
        if user:
            return HttpResponse(True)
        return HttpResponse(False)
    except Exception as e:
        return HttpResponse(False)


@csrf_exempt
def student_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackStudent.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Student Feedback Messages'
        }
        return render(request, 'hod_template/student_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackStudent, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def staff_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackStaff.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Staff Feedback Messages'
        }
        return render(request, 'hod_template/staff_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackStaff, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def view_staff_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportStaff.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Staff'
        }
        return render(request, "hod_template/staff_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportStaff, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


@csrf_exempt
def view_student_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportStudent.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Students'
        }
        return render(request, "hod_template/student_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportStudent, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


def admin_view_attendance(request):
    courses = Course.objects.all()
    course_data = []
    for course in courses:
        student_count = Student.objects.filter(course=course).count()
        course_data.append({'course': course, 'student_count': student_count})
    context = {
        'course_data': course_data,
        'page_title': 'Fetch Attendance - Select Course'
    }
    return render(request, "hod_template/admin_view_attendance.html", context)


def admin_attendance_by_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    students = CustomUser.objects.filter(user_type=3, student__course=course).order_by(
        Lower('first_name'), Lower('last_name'))
    context = {
        'students': students,
        'course': course,
        'page_title': 'Fetch Attendance - ' + course.short_name
    }
    return render(request, "hod_template/attendance_student_list.html", context)


def admin_student_attendance(request, student_id):
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
    context = {
        'student': student,
        'attendance_summary': attendance_summary,
        'page_title': 'Attendance - ' + student.admin.first_name + ' ' + student.admin.last_name
    }
    return render(request, "hod_template/student_attendance_detail.html", context)


@csrf_exempt
def get_admin_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = get_object_or_404(
            Attendance, id=attendance_date_id, session=session)
        attendance_reports = AttendanceReport.objects.filter(
            attendance=attendance)
        json_data = []
        for report in attendance_reports:
            data = {
                "status":  str(report.status),
                "name": str(report.student)
            }
            json_data.append(data)
        return JsonResponse(json.dumps(json_data), safe=False)
    except Exception as e:
        return None


def admin_view_profile(request):
    admin = get_object_or_404(Admin, admin=request.user)
    form = AdminForm(request.POST or None, request.FILES or None,
                     instance=admin)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                passport = request.FILES.get('profile_pic') or None
                custom_user = admin.admin
                if password != None:
                    custom_user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    custom_user.profile_pic = passport_url
                custom_user.first_name = first_name
                custom_user.last_name = last_name
                custom_user.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('admin_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
    return render(request, "hod_template/admin_view_profile.html", context)


def admin_notify_staff(request):
    staff = CustomUser.objects.filter(user_type=2).order_by(
        Lower('first_name'), Lower('last_name'))
    context = {
        'page_title': "Send Notifications To Staff",
        'allStaff': staff
    }
    return render(request, "hod_template/staff_notification.html", context)


def admin_notify_student(request):
    # Landing page: pick a course (like Manage Students), or search for any
    # active student directly via the search box.
    course_data = []
    for course in Course.objects.all():
        count = Student.objects.filter(course=course, passed_out=False).count()
        course_data.append({'course': course, 'student_count': count})
    # Flat list of every active student, for the client-side "search any student" box.
    search_students = []
    for s in Student.objects.filter(passed_out=False).select_related('admin', 'course').order_by(
            Lower('admin__first_name'), Lower('admin__last_name')):
        search_students.append({
            'id': s.admin_id,
            'name': "%s %s" % (s.admin.first_name, s.admin.last_name),
            'roll': s.roll_number or '',
            'course': s.course.short_name if s.course else '—',
            'course_full': s.course.name if s.course else '',
            'semester': s.current_semester,
        })
    context = {
        'page_title': "Send Notifications To Students",
        'course_data': course_data,
        'search_students': search_students,
    }
    return render(request, "hod_template/student_notification.html", context)


def notify_student_by_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    total_semesters = course.semesters or 0
    semester_data = []
    for sem in range(1, total_semesters + 1):
        count = Student.objects.filter(
            course=course, current_semester=sem, passed_out=False).count()
        semester_data.append({'number': sem, 'student_count': count})
    context = {
        'course': course,
        'semester_data': semester_data,
        'page_title': 'Notify Students - %s (Select Semester)' % course.short_name,
    }
    return render(request, "hod_template/notify_student_semester_list.html", context)


def notify_student_by_semester(request, course_id, semester):
    # Both shifts of this course+semester together (no shift split here).
    course = get_object_or_404(Course, id=course_id)
    students = CustomUser.objects.filter(
        user_type=3, student__course=course, student__current_semester=semester,
        student__passed_out=False).order_by(Lower('first_name'), Lower('last_name'))
    context = {
        'course': course,
        'semester': semester,
        'students': students,
        'page_title': 'Notify Students - %s - Semester %s' % (course.short_name, semester),
    }
    return render(request, "hod_template/notify_student_list.html", context)


@csrf_exempt
def send_student_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    student = get_object_or_404(Student, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Student Management System",
                'body': message,
                'click_action': reverse('student_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': student.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationStudent(student=student, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


@csrf_exempt
def send_staff_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    staff = get_object_or_404(Staff, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Student Management System",
                'body': message,
                'click_action': reverse('staff_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': staff.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationStaff(staff=staff, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def delete_staff(request, staff_id):
    staff = get_object_or_404(CustomUser, staff__id=staff_id)
    staff.delete()
    messages.success(request, "Staff deleted successfully!")
    return redirect(reverse('manage_staff'))


def delete_student(request, student_id):
    student = get_object_or_404(CustomUser, student__id=student_id)
    student.delete()
    messages.success(request, "Student deleted successfully!")
    return redirect(reverse('manage_student'))


def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    try:
        course.delete()
        messages.success(request, "Course deleted successfully!")
    except Exception:
        messages.error(
            request, "Sorry, some students are assigned to this course already. Kindly change the affected student course and try again")
    return redirect(reverse('manage_course'))


def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    link = CourseSubject.objects.filter(subject=subject).first()
    course = link.course if link else None
    semester = link.semester if link else None
    subject.delete()
    messages.success(request, "Subject deleted successfully!")
    if course and semester:
        return redirect(reverse('manage_subject_by_semester', args=[course.id, semester]))
    if course:
        return redirect(reverse('manage_subject_by_course', args=[course.id]))
    return redirect(reverse('manage_course'))


def delete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    try:
        session.delete()
        messages.success(request, "Session deleted successfully!")
    except Exception:
        messages.error(
            request, "There are students assigned to this session. Please move them to another session.")
    return redirect(reverse('manage_session'))
