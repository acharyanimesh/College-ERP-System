import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *
from . import forms, models
from datetime import date

def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    staff_courses = staff.courses.all()
    course_names = ', '.join(c.name for c in staff_courses) or 'No course'
    total_students = Student.objects.filter(course__in=staff_courses, passed_out=False).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(
        Q(coursesubject__morning_staff=staff) | Q(coursesubject__day_staff=staff)).distinct()
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    context = {
        'page_title': 'Staff Panel - ' + str(staff.admin.first_name) + ' ' + str(staff.admin.last_name[0]) + '' + ' (' + course_names + ')',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'assigned_subjects': subjects,
    }
    return render(request, "staff_template/erpnext_staff_home.html", context)


def _attendance_picker_context(staff):
    """Shared options for the take/update attendance pickers: the courses, shifts,
    subjects (as clickable buttons) this staff teaches and the semesters those
    subjects sit at. Each subject carries its per-course/shift assignments so the
    UI can auto-select the semester it is taught at."""
    # Only courses where this staff is assigned to teach a subject.
    courses = Course.objects.filter(
        Q(coursesubject__morning_staff=staff) | Q(coursesubject__day_staff=staff)).distinct()
    # Limit the shift selector to the shift(s) this staff is assigned to.
    shifts = [(v, l) for v, l in SHIFT_CHOICES if v in staff.shifts]
    cs_qs = CourseSubject.objects.filter(
        Q(morning_staff=staff) | Q(day_staff=staff)).select_related('subject')
    subj_map = {}
    semesters_set = set()
    for cs in cs_qs:
        entry = subj_map.setdefault(cs.subject_id, {
            'id': cs.subject_id, 'name': cs.subject.name,
            'morning': False, 'day': False, 'assignments': []})
        teaches_morning = cs.morning_staff_id == staff.id
        teaches_day = cs.day_staff_id == staff.id
        if teaches_morning:
            entry['morning'] = True
        if teaches_day:
            entry['day'] = True
        cs_shifts = []
        if teaches_morning:
            cs_shifts.append('morning')
        if teaches_day:
            cs_shifts.append('day')
        entry['assignments'].append(
            {'course': cs.course_id, 'semester': cs.semester, 'shifts': cs_shifts})
        if cs.semester is not None:
            semesters_set.add(cs.semester)
    subjects = sorted(subj_map.values(), key=lambda s: s['name'].lower())
    for s in subjects:
        s['assignments_json'] = json.dumps(s['assignments'])
    return {
        'subjects': subjects,
        'semesters': sorted(semesters_set),
        'courses': courses,
        'shifts': shifts,
    }


def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    context = _attendance_picker_context(staff)
    context['page_title'] = 'Take Attendance'
    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_students(request):
    course_id = request.POST.get('course')
    semester = request.POST.get('semester')
    shift = request.POST.get('shift')
    try:
        course = get_object_or_404(Course, id=course_id)
        # Fetch the cohort CURRENTLY in this semester — a subject is taught at one
        # semester per course, so students promoted past it are correctly excluded.
        students = Student.objects.filter(
            course_id=course.id, current_semester=semester, shift=shift,
            passed_out=False).order_by(
            Lower('admin__first_name'), Lower('admin__last_name'))
        student_data = []
        for student in students:
            data = {
                    "id": student.id,
                    "name": student.admin.first_name + " " + student.admin.last_name,
                    "roll_number": student.roll_number or ""
                    }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return JsonResponse(json.dumps([]), content_type='application/json', safe=False)


@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    subject_id = request.POST.get('subject')
    course_id = request.POST.get('course')
    semester = request.POST.get('semester')
    shift = request.POST.get('shift')
    students = json.loads(student_data)
    try:
        staff = get_object_or_404(Staff, admin=request.user)
        subject = get_object_or_404(Subject, id=subject_id)
        # The teacher may only take attendance for a subject they are assigned to,
        # in this shift, at the semester it is actually taught for this course.
        shift_field = 'morning_staff' if shift == 'morning' else 'day_staff'
        if not CourseSubject.objects.filter(
                subject=subject, course_id=course_id, semester=semester,
                **{shift_field: staff}).exists():
            return HttpResponse("NOT_ASSIGNED")
        # Derive the session from the cohort being marked (they share one intake);
        # this keeps attendance history separated by session without asking for it.
        cohort = Student.objects.filter(id__in=[s.get('id') for s in students])
        first_student = cohort.first()
        session = first_student.session if first_student else None
        if session is None:
            return HttpResponse("NO_SESSION")
        attendance = Attendance(session=session, subject=subject, shift=shift, date=date)
        attendance.save()

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))
            attendance_report = AttendanceReport(
                student=student, attendance=attendance,
                status=student_dict.get('status'),
                late=student_dict.get('late', 0))
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    context = _attendance_picker_context(staff)
    context['page_title'] = 'Update Attendance'

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date).order_by(
            Lower('student__admin__first_name'), Lower('student__admin__last_name'))
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.first_name + " " + attendance.student.admin.last_name,
                    "roll_number": attendance.student.roll_number or "",
                    "status": attendance.status,
                    "late": attendance.late,
                    "locked": date.locked}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return JsonResponse(json.dumps([]), content_type='application/json', safe=False)


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        staff = get_object_or_404(Staff, admin=request.user)
        attendance = get_object_or_404(Attendance, id=date)
        # Confirmed attendance is permanent and cannot be edited again.
        if attendance.locked:
            return HttpResponse("LOCKED")
        # Only the assigned teacher for this subject in the attendance's shift
        # may update it.
        shift_field = 'morning_staff' if attendance.shift == 'morning' else 'day_staff'
        if not CourseSubject.objects.filter(subject=attendance.subject, **{shift_field: staff}).exists():
            return HttpResponse("NOT_ASSIGNED")

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.late = student_dict.get('late', 0)
            attendance_report.save()
        # Lock it: this update is the final, confirmed record.
        attendance.locked = True
        attendance.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_view_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    context = _attendance_picker_context(staff)
    context['page_title'] = 'View Attendance'
    return render(request, 'staff_template/staff_view_attendance.html', context)


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)


def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.all()
    sessions = Session.objects.all()
    context = {
        'page_title': 'Result Upload',
        'subjects': subjects,
        'sessions': sessions
    }
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_list')
            subject_id = request.POST.get('subject')
            test = request.POST.get('test')
            exam = request.POST.get('exam')
            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)
            try:
                data = StudentResult.objects.get(
                    student=student, subject=subject)
                data.exam = exam
                data.test = test
                data.save()
                messages.success(request, "Scores Updated")
            except:
                result = StudentResult(student=student, subject=subject, test=test, exam=exam)
                result.save()
                messages.success(request, "Scores Saved")
        except Exception as e:
            messages.warning(request, "Error Occured While Processing Form")
    return render(request, "staff_template/staff_add_result.html", context)


@csrf_exempt
def fetch_student_result(request):
    try:
        subject_id = request.POST.get('subject')
        student_id = request.POST.get('student')
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id)
        result = StudentResult.objects.get(student=student, subject=subject)
        result_data = {
            'exam': result.exam,
            'test': result.test
        }
        return HttpResponse(json.dumps(result_data))
    except Exception as e:
        return HttpResponse('False')

#library
def add_book(request):
    if request.method == "POST":
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']


        books = Book.objects.create(name=name, author=author, isbn=isbn, category=category )
        books.save()
        alert = True
        return render(request, "staff_template/add_book.html", {'alert':alert})
    context = {
        'page_title': "Add Book"
    }
    return render(request, "staff_template/add_book.html",context)

#issue book


def issue_book(request):
    form = forms.IssueBookForm()
    if request.method == "POST":
        form = forms.IssueBookForm(request.POST)
        if form.is_valid():
            obj = models.IssuedBook()
            obj.student_id = request.POST['name2']
            obj.isbn = request.POST['isbn2']
            obj.save()
            alert = True
            return render(request, "staff_template/issue_book.html", {'obj':obj, 'alert':alert})
    return render(request, "staff_template/issue_book.html", {'form':form})

def view_issued_book(request):
    issuedBooks = IssuedBook.objects.all()
    details = []
    for i in issuedBooks:
        days = (date.today()-i.issued_date)
        d=days.days
        fine=0
        if d>14:
            day=d-14
            fine=day*5
        books = list(models.Book.objects.filter(isbn=i.isbn))
        # students = list(models.Student.objects.filter(admin=i.admin))
        i=0
        for l in books:
            t=(books[i].name,books[i].isbn,issuedBooks[0].issued_date,issuedBooks[0].expiry_date,fine)
            i=i+1
            details.append(t)
    return render(request, "staff_template/view_issued_book.html", {'issuedBooks':issuedBooks, 'details':details})