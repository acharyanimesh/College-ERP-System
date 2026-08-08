"""Admin management of librarian accounts.

Deliberately the same shape as staff.py — same creation flow (inactive
account, no usable password, owner activates it from the emailed link), same
never-editable generated ID — minus everything about teaching.
"""
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..emails import send_verification_email
from ..forms import LibrarianForm
from ..idgen import next_employee_id
from ..models import CustomUser, Librarian
from .people import apply_user_fields, save_profile_pic
from .permissions import IsAdmin
from .serializers import form_errors, librarian_detail, librarian_row


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def librarian_list(request):
    if request.method == 'GET':
        librarians = Librarian.objects.select_related('admin').order_by(
            Lower('admin__first_name'), Lower('admin__last_name'))
        return Response([librarian_row(l) for l in librarians])

    form = LibrarianForm(request.data, request.FILES)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    passport_url = save_profile_pic(request.FILES) or ''
    try:
        with transaction.atomic():
            user = CustomUser.objects.create_user(
                email=get('email'), user_type=4, is_active=False,
                first_name=get('first_name'), last_name=get('last_name'),
                profile_pic=passport_url)
            apply_user_fields(user, form)
            user.save()
            librarian = user.librarian
            librarian.librarian_id = next_employee_id()
            librarian.save()
    except Exception as e:
        return Response({'detail': "Could Not Add " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)

    data = librarian_detail(librarian)
    try:
        send_verification_email(user)
    except Exception:
        data['detail'] = ("Librarian account created, but the verification email "
                          "could not be sent. Use \"Resend verification email\" "
                          "from the librarian list once email delivery is fixed.")
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def librarian_item(request, librarian_id):
    librarian = get_object_or_404(Librarian, id=librarian_id)
    if request.method == 'GET':
        return Response(librarian_detail(librarian))

    if request.method == 'DELETE':
        librarian.admin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    form = LibrarianForm(request.data, request.FILES, instance=librarian)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    get = form.cleaned_data.get
    try:
        user = librarian.admin
        user.email = get('email')
        password = get('password') or None
        if password is not None:
            user.set_password(password)
        passport_url = save_profile_pic(request.FILES)
        if passport_url is not None:
            user.profile_pic = passport_url
        apply_user_fields(user, form)
        user.save()
        librarian.save()
    except Exception as e:
        return Response({'detail': "Could Not Update " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(librarian_detail(librarian))


@api_view(['POST'])
@permission_classes([IsAdmin])
def resend_verification(request, librarian_id):
    librarian = get_object_or_404(Librarian, id=librarian_id)
    user = librarian.admin
    if user.is_active:
        return Response({'detail': 'This account is already verified.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        send_verification_email(user)
    except Exception as e:
        return Response({'detail': "Could not send the email: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': 'Verification email sent.'})
