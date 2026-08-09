"""Admin management of accountant accounts.

Deliberately the same shape as librarians.py — same creation flow (inactive
account, no usable password, owner activates it from the emailed link), same
never-editable generated ID — an accountant is a finance-desk role, not a
teacher.
"""
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..emails import send_verification_email
from ..forms import AccountantForm
from ..idgen import next_employee_id
from ..models import Accountant, CustomUser
from .people import apply_user_fields, save_profile_pic
from .permissions import IsAdmin
from .serializers import accountant_detail, accountant_row, form_errors


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def accountant_list(request):
    if request.method == 'GET':
        accountants = Accountant.objects.select_related('admin').order_by(
            Lower('admin__first_name'), Lower('admin__last_name'))
        return Response([accountant_row(a) for a in accountants])

    form = AccountantForm(request.data, request.FILES)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    passport_url = save_profile_pic(request.FILES) or ''
    try:
        with transaction.atomic():
            user = CustomUser.objects.create_user(
                email=get('email'), user_type=5, is_active=False,
                first_name=get('first_name'), last_name=get('last_name'),
                profile_pic=passport_url)
            apply_user_fields(user, form)
            user.save()
            accountant = user.accountant
            accountant.accountant_id = next_employee_id()
            accountant.save()
    except Exception as e:
        return Response({'detail': "Could Not Add " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)

    data = accountant_detail(accountant)
    try:
        send_verification_email(user)
    except Exception:
        data['detail'] = ("Accountant account created, but the verification "
                          "email could not be sent. Use \"Resend verification "
                          "email\" from the accountant list once email delivery "
                          "is fixed.")
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def accountant_item(request, accountant_id):
    accountant = get_object_or_404(Accountant, id=accountant_id)
    if request.method == 'GET':
        return Response(accountant_detail(accountant))

    if request.method == 'DELETE':
        accountant.admin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    form = AccountantForm(request.data, request.FILES, instance=accountant)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    try:
        user = accountant.admin
        user.email = get('email')
        password = get('password') or None
        if password is not None:
            user.set_password(password)
        passport_url = save_profile_pic(request.FILES)
        if passport_url is not None:
            user.profile_pic = passport_url
        apply_user_fields(user, form)
        user.save()
        accountant.save()
    except Exception as e:
        return Response({'detail': "Could Not Update " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(accountant_detail(accountant))


@api_view(['POST'])
@permission_classes([IsAdmin])
def resend_verification(request, accountant_id):
    accountant = get_object_or_404(Accountant, id=accountant_id)
    user = accountant.admin
    if user.is_active:
        return Response({'detail': 'This account is already verified.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        send_verification_email(user)
    except Exception as e:
        return Response({'detail': "Could not send the email: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': 'Verification email sent.'})
