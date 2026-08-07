from datetime import date as date_cls

from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from django.db.models import F

from ..emails import send_verification_email
from ..forms import StudentForm
from ..idgen import (
    assign_student_numbers, batch_lock_state, lock_batches_for_course,
    resequence_cohort)
from ..models import SHIFT_CHOICES, Course, CustomUser, Session, Student
from .permissions import IsAdmin
from .serializers import course_dict, form_errors, student_detail, student_row


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
    # Roll numbers stay alphabetical only while an intake is still filling up.
    # Leaving Semester 1 is the point of no return: from here the cohort has
    # attendance and results filed under these numbers, so freeze them before
    # anyone moves and let late arrivals be appended instead.
    leaving_sem_one = Student.objects.filter(
        course=course, passed_out=False, current_semester=1,
        current_semester__gte=from_semester).values_list('session', flat=True)
    lock_batches_for_course(course, list(leaving_sem_one))
    # Updating off the OLD value (highest-to-lowest is irrelevant for a single
    # bulk +1) keeps each batch separate, so a lower one never mixes into the next.
    promoted = Student.objects.filter(
        course=course, passed_out=False,
        current_semester__gte=from_semester, current_semester__lt=final
    ).update(current_semester=F('current_semester') + 1)
    return (promoted, graduated)


def _save_profile_pic(files):
    passport = files.get('profile_pic')
    if not passport:
        return None
    fs = FileSystemStorage()
    filename = fs.save(passport.name, passport)
    return fs.url(filename)


def _apply_user_fields(user, form):
    """Copy the shared CustomUser fields out of a valid StudentForm."""
    get = form.cleaned_data.get
    user.first_name = get('first_name')
    user.middle_name = get('middle_name')
    user.last_name = get('last_name')
    user.gender = get('gender')
    user.address_line1 = get('address_line1')
    user.address_line2 = get('address_line2')
    user.city = get('city')
    user.province = get('province')
    user.address = ", ".join(filter(None, [
        get('address_line1'), get('address_line2'), get('city'), get('province')]))
    user.phone_number = get('phone_number')
    user.date_of_birth = get('date_of_birth')


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def student_list(request):
    if request.method == 'GET':
        students = Student.objects.filter(passed_out=False).select_related(
            'admin', 'course', 'session')
        for param in ('course', 'semester', 'shift'):
            value = request.query_params.get(param)
            if value:
                field = 'current_semester' if param == 'semester' else param
                students = students.filter(**{field: value})
        students = students.order_by(
            Lower('admin__first_name'), Lower('admin__last_name'))
        return Response([student_row(s) for s in students])

    # POST — mirrors hod_views.add_student, including the closed-Semester-1
    # cohort rule and the new-intake cascade promotion.
    form = StudentForm(request.data, request.FILES)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    course = get('course')
    session = get('session')
    new_sem = get('current_semester') or 1

    if new_sem == 1 and course is not None and session is not None:
        cohort = Student.objects.filter(
            course=course, session=session, passed_out=False)
        if cohort.exists() and not cohort.filter(current_semester=1).exists():
            cohort_sem = cohort.order_by('current_semester').first().current_semester
            return Response({'detail':
                "The %s batch of %s has already progressed to Semester %d. "
                "New students for this session can't be added to Semester 1 — "
                "set Current Semester to %d instead."
                % (session, course.short_name, cohort_sem, cohort_sem)},
                status=status.HTTP_400_BAD_REQUEST)

    passport_url = _save_profile_pic(request.FILES) or ''
    try:
        promo_msg = None
        with transaction.atomic():
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
                        promo_msg = "New intake for %s — %s." % (
                            course.short_name, "; ".join(bits))

            user = CustomUser.objects.create_user(
                email=get('email'), user_type=3, is_active=False,
                first_name=get('first_name'), last_name=get('last_name'),
                profile_pic=passport_url)
            _apply_user_fields(user, form)
            user.save()
            student = user.student
            student.session = session
            student.course = course
            student.shift = get('shift')
            student.current_semester = new_sem
            student.parent_full_name = get('parent_full_name')
            student.parent_phone_number = get('parent_phone_number')
            student.parent_relationship = get('parent_relationship')
            student.save()
            # Registration + roll number are derived from session/course, so
            # they can only be issued once those are on the saved row.
            shifted = assign_student_numbers(student)
            if shifted:
                roll_msg = (
                    "Roll numbers are alphabetical, so adding this student "
                    "renumbered %d other%s in the same batch."
                    % (shifted, "" if shifted == 1 else "s"))
                promo_msg = (promo_msg + " " if promo_msg else "") + roll_msg
    except Exception as e:
        return Response({'detail': "Could Not Add: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    data = student_detail(student)
    try:
        send_verification_email(user)
    except Exception:
        promo_msg = (promo_msg + " " if promo_msg else "") + (
            "Student account created, but the verification email could not be "
            "sent. Use \"Resend verification email\" from the student list "
            "once email delivery is fixed.")
    if promo_msg:
        data['detail'] = promo_msg
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def student_item(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'GET':
        return Response(student_detail(student))

    if request.method == 'DELETE':
        session, course = student.session, student.course
        with transaction.atomic():
            student.admin.delete()      # cascades to the Student row
            # Close the hole in an open cohort's alphabetical run. A locked one
            # keeps its gap: those numbers are already on record elsewhere.
            resequence_cohort(session, course)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT — mirrors hod_views.edit_student.
    form = StudentForm(request.data, request.FILES, instance=student)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    try:
        user = student.admin
        # Both identifiers are derived, so an edit has to notice everything
        # they are derived from: the session (registration number), the course
        # and shift (roll number), and the name (position within it).
        old_session, old_course = student.session, student.course
        old_shift = student.shift
        old_name = (user.last_name, user.first_name, user.middle_name)

        user.email = get('email')
        password = get('password') or None
        if password is not None:
            user.set_password(password)
        passport_url = _save_profile_pic(request.FILES)
        if passport_url is not None:
            user.profile_pic = passport_url
        _apply_user_fields(user, form)
        student.session = get('session')
        student.course = get('course')
        student.shift = get('shift')
        student.current_semester = get('current_semester') or 1
        student.parent_full_name = get('parent_full_name')
        student.parent_phone_number = get('parent_phone_number')
        student.parent_relationship = get('parent_relationship')

        session_changed = old_session != student.session
        course_changed = old_course != student.course
        shift_changed = old_shift != student.shift
        renamed = old_name != (
            user.last_name, user.first_name, user.middle_name)

        with transaction.atomic():
            user.save()
            student.save()
            if session_changed or course_changed or shift_changed:
                # Close the gap they left behind, then issue fresh numbers
                # where they landed. A shift move stays inside the same intake,
                # so one resequence covers both runs. The old registration
                # number belongs to the old intake's series, so it only
                # survives a course or shift move.
                resequence_cohort(old_session, old_course)
                assign_student_numbers(
                    student, reissue_registration=session_changed)
            elif renamed:
                resequence_cohort(student.session, student.course)
                student.refresh_from_db(fields=['roll_number'])
    except Exception as e:
        return Response({'detail': "Could Not Update " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(student_detail(student))


@api_view(['POST'])
@permission_classes([IsAdmin])
def resend_verification(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    user = student.admin
    if user.is_active:
        return Response({'detail': 'This account is already verified.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        send_verification_email(user)
    except Exception as e:
        return Response({'detail': "Could not send the email: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': 'Verification email sent.'})


@api_view(['POST'])
@permission_classes([IsAdmin])
def promote_class(request, course_id):
    """Cascading promotion (hod_views.promote_class): semester N and above
    move up one; final-semester students pass out."""
    course = get_object_or_404(Course, id=course_id)
    if not course.semesters:
        return Response({'detail': "Set the number of semesters for %s first."
                         % course.short_name}, status=status.HTTP_400_BAD_REQUEST)
    try:
        semester = int(request.data.get('from_semester'))
    except (TypeError, ValueError):
        return Response({'detail': 'from_semester is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        promoted, graduated = _cascade_promote_course(course, semester)

    parts = []
    if promoted:
        parts.append("promoted %d student(s) (Semester %d and above moved up one)"
                     % (promoted, semester))
    if graduated:
        parts.append("marked %d final-semester student(s) as passed out" % graduated)
    if parts:
        detail = ("In %s: " % course.short_name) + "; ".join(parts) + "."
    else:
        detail = ("No students to promote from Semester %d upward in %s."
                  % (semester, course.short_name))
    return Response({'detail': detail})


@api_view(['GET'])
@permission_classes([IsAdmin])
def manage_courses(request):
    course_data = []
    for course in Course.objects.all():
        course_data.append({
            'course': course_dict(course),
            'student_count': Student.objects.filter(
                course=course, passed_out=False).count(),
        })
    return Response(course_data)


def _sessions_at(course, semester):
    """Session ids of `course`'s active students in `semester`."""
    return list(Student.objects.filter(
        course=course, current_semester=semester, passed_out=False
    ).values_list('session', flat=True).distinct())


@api_view(['GET'])
@permission_classes([IsAdmin])
def manage_semesters(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    total_semesters = course.semesters or 0
    semester_data = []
    for sem in range(1, total_semesters + 1):
        semester_data.append({
            'number': sem,
            'student_count': Student.objects.filter(
                course=course, current_semester=sem, passed_out=False).count(),
            # Whether this semester's intake(s) still renumber alphabetically.
            'roll_lock': batch_lock_state(course, _sessions_at(course, sem)),
        })
    return Response({
        'course': course_dict(course),
        'total_semesters': total_semesters,
        'semester_data': semester_data,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def roll_number_lock(request, course_id, semester):
    """Freeze alphabetical renumbering for a semester's intakes.

    Locking is what the admin does when admissions close: from then on a late
    arrival is appended at the end of the batch instead of pushing everyone who
    sorts after them down one. Promotion out of Semester 1 does this
    automatically too — this is the manual control for closing earlier.

    There is no unlock. Once an intake's numbers are frozen they are on
    attendance sheets and marksheets, so the admin re-enters their own password
    here to confirm they mean a one-way change.
    """
    password = request.data.get('password') or ''
    if not request.user.check_password(password):
        return Response(
            {'detail': "That password is not correct. Roll numbers were not "
                       "locked."},
            status=status.HTTP_403_FORBIDDEN)

    course = get_object_or_404(Course, id=course_id)
    session_ids = _sessions_at(course, semester)
    if not session_ids:
        return Response({'detail': "No students in Semester %d of %s."
                         % (semester, course.short_name)},
                        status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        changed = lock_batches_for_course(course, session_ids)

    if not changed:
        detail = ("Roll numbers for Semester %d of %s were already locked."
                  % (semester, course.short_name))
    else:
        detail = ("Roll numbers locked for %d intake(s) in Semester %d of %s. "
                  "New students are now added at the end of the batch, and "
                  "this cannot be undone."
                  % (changed, semester, course.short_name))
    return Response({
        'detail': detail,
        'roll_lock': batch_lock_state(course, session_ids),
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def manage_shifts(request, course_id, semester):
    course = get_object_or_404(Course, id=course_id)
    shift_data = []
    for value, label in SHIFT_CHOICES:
        shift_data.append({
            'value': value,
            'label': label,
            'student_count': Student.objects.filter(
                course=course, current_semester=semester, shift=value,
                passed_out=False).count(),
        })
    return Response({
        'course': course_dict(course),
        'shift_data': shift_data,
        'is_final_semester': bool(course.semesters) and semester >= course.semesters,
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def passed_out_courses(request):
    course_data = []
    for course in Course.objects.all():
        course_data.append({
            'course': course_dict(course),
            'student_count': Student.objects.filter(
                course=course, passed_out=True).count(),
        })
    return Response(course_data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def passed_out_sessions(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    grads = Student.objects.filter(course=course, passed_out=True)
    session_ids = grads.values_list('session', flat=True).distinct()
    session_data = []
    for session in Session.objects.filter(id__in=session_ids).order_by('start_year'):
        session_data.append({
            'session': {'id': session.id, 'label': str(session)},
            'student_count': grads.filter(session=session).count(),
        })
    return Response({
        'course': course_dict(course),
        'session_data': session_data,
        'no_session_count': grads.filter(session__isnull=True).count(),
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def passed_out_list(request):
    students = Student.objects.filter(passed_out=True).select_related(
        'admin', 'course', 'session')
    course = request.query_params.get('course')
    session = request.query_params.get('session')
    if course:
        students = students.filter(course_id=course)
    if session:
        students = students.filter(session_id=session)
    students = students.order_by(
        Lower('admin__first_name'), Lower('admin__last_name'))
    return Response([student_row(s) for s in students])
