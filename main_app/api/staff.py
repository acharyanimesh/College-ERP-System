from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from django.db import transaction

from ..emails import send_verification_email
from ..forms import StaffForm
from ..idgen import next_staff_id
from ..models import CourseSubject, CustomUser, Staff
from .permissions import IsAdmin
from .serializers import form_errors, staff_detail, staff_row


def _save_profile_pic(files):
    passport = files.get('profile_pic')
    if not passport:
        return None
    fs = FileSystemStorage()
    filename = fs.save(passport.name, passport)
    return fs.url(filename)


def _apply_user_fields(user, form):
    get = form.cleaned_data.get
    user.first_name = get('first_name')
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


def _apply_staff_fields(staff, form):
    """Note staff_id is not touched here — it is issued once at creation and
    is not editable afterwards, so an edit must leave it exactly as it is."""
    get = form.cleaned_data.get
    staff.teaches_morning = get('teaches_morning')
    staff.teaches_day = get('teaches_day')


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def staff_list(request):
    if request.method == 'GET':
        staff_members = Staff.objects.select_related('admin').order_by(
            Lower('admin__first_name'), Lower('admin__last_name'))
        return Response([staff_row(s) for s in staff_members])

    # POST — mirrors hod_views.add_staff. The account is created inactive
    # with no usable password; the owner sets their own password (and
    # activates the account) via the emailed verification link.
    form = StaffForm(request.data, request.FILES)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    passport_url = _save_profile_pic(request.FILES) or ''
    try:
        with transaction.atomic():
            user = CustomUser.objects.create_user(
                email=get('email'), user_type=2, is_active=False,
                first_name=get('first_name'), last_name=get('last_name'),
                profile_pic=passport_url)
            _apply_user_fields(user, form)
            user.save()
            staff = user.staff
            _apply_staff_fields(staff, form)
            staff.staff_id = next_staff_id()
            staff.save()
    except Exception as e:
        return Response({'detail': "Could Not Add " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)

    data = staff_detail(staff)
    try:
        send_verification_email(user)
    except Exception:
        data['detail'] = ("Staff account created, but the verification email "
                          "could not be sent. Use \"Resend verification email\" "
                          "from the staff list once email delivery is fixed.")
    return Response(data, status=status.HTTP_201_CREATED)


def _assignments_for(staff):
    """Teaching assignments like hod_views.staff_details builds them."""
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
        assignments.append({
            'subject_code': cs.subject.code,
            'subject_name': cs.subject.name,
            'course_name': cs.course.name,
            'course_short_name': cs.course.short_name,
            'semester': cs.semester,
            'shifts': ", ".join(shifts),
        })
    return assignments, cs_qs.values('subject').distinct().count()


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def staff_item(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    if request.method == 'GET':
        assignments, subject_count = _assignments_for(staff)
        return Response(staff_detail(staff, assignments, subject_count))

    if request.method == 'DELETE':
        staff.admin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT — mirrors hod_views.edit_staff.
    form = StaffForm(request.data, request.FILES, instance=staff)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    try:
        user = staff.admin
        user.email = get('email')
        password = get('password') or None
        if password is not None:
            user.set_password(password)
        passport_url = _save_profile_pic(request.FILES)
        if passport_url is not None:
            user.profile_pic = passport_url
        _apply_user_fields(user, form)
        _apply_staff_fields(staff, form)
        user.save()
        staff.save()
    except Exception as e:
        return Response({'detail': "Could Not Update " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(staff_detail(staff))


@api_view(['POST'])
@permission_classes([IsAdmin])
def resend_verification(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    user = staff.admin
    if user.is_active:
        return Response({'detail': 'This account is already verified.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        send_verification_email(user)
    except Exception as e:
        return Response({'detail': "Could not send the email: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': 'Verification email sent.'})


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def subject_assignments(request, staff_id):
    """Assign Subjects page data + save (hod_views.assign_staff_subjects)."""
    staff = get_object_or_404(Staff, id=staff_id)
    if request.method == 'POST':
        # A teacher may only claim a FREE slot (or one already theirs); a slot
        # held by another teacher stays untouched.
        selected_morning = set(str(i) for i in request.data.get('morning', []))
        selected_day = set(str(i) for i in request.data.get('day', []))
        for cs in CourseSubject.objects.all():
            sid = str(cs.id)
            changed = False
            if sid in selected_morning:
                if cs.morning_staff_id in (None, staff.id):
                    cs.morning_staff = staff
                    changed = True
            elif cs.morning_staff_id == staff.id:
                cs.morning_staff = None
                changed = True
            if sid in selected_day:
                if cs.day_staff_id in (None, staff.id):
                    cs.day_staff = staff
                    changed = True
            elif cs.day_staff_id == staff.id:
                cs.day_staff = None
                changed = True
            if changed:
                cs.save()
        return Response({'detail': 'Teaching assignments updated successfully'})

    rows = []
    for cs in CourseSubject.objects.select_related(
            'subject', 'course', 'morning_staff__admin', 'day_staff__admin').order_by(
            Lower('course__name'), 'semester', Lower('subject__name')):
        rows.append({
            'cs_id': cs.id,
            'subject_code': cs.subject.code,
            'subject_name': cs.subject.name,
            'course_name': cs.course.name,
            'course_short_name': cs.course.short_name,
            'semester': cs.semester,
            'morning_mine': cs.morning_staff_id == staff.id,
            'morning_other': str(cs.morning_staff) if (
                cs.morning_staff_id and cs.morning_staff_id != staff.id) else None,
            'day_mine': cs.day_staff_id == staff.id,
            'day_other': str(cs.day_staff) if (
                cs.day_staff_id and cs.day_staff_id != staff.id) else None,
        })
    return Response({
        'staff_name': "%s %s" % (staff.admin.first_name, staff.admin.last_name),
        'rows': rows,
    })
