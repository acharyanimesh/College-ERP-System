import json

import requests
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..emails import send_admin_verification_email, send_email_change_verification
from ..models import CustomUser
from ..tokens import email_verification_token
from .permissions import (ACCOUNTANT, ADMIN, IsAdmin, LIBRARIAN, STAFF,
                          STUDENT)
from .serializers import user_dict

# Admin/HOD shares the college's institutional domain with Staff.
ADMIN_ALLOWED_EMAIL_DOMAINS = settings.STAFF_ALLOWED_EMAIL_DOMAINS
ROLE_EMAIL_DOMAINS = {
    STAFF: settings.STAFF_ALLOWED_EMAIL_DOMAINS,
    STUDENT: settings.STUDENT_ALLOWED_EMAIL_DOMAINS,
    LIBRARIAN: settings.LIBRARIAN_ALLOWED_EMAIL_DOMAINS,
    ACCOUNTANT: settings.ACCOUNTANT_ALLOWED_EMAIL_DOMAINS,
}
# Roles whose email change an admin has to approve before the verification
# link goes out (Admin/HOD's own changes skip the gate).
APPROVAL_REQUIRED_ROLES = (STAFF, STUDENT, LIBRARIAN, ACCOUNTANT)
ROLE_LABELS = {STAFF: 'Staff', STUDENT: 'Student', LIBRARIAN: 'Librarian',
               ACCOUNTANT: 'Accountant'}

# Same domain-bound key doLogin used.
CAPTCHA_SECRET = "6LfTGD4qAAAAALtlli02bIM2MGi_V0cUYrmzGEGd"


@ensure_csrf_cookie
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Session login (mirrors views.doLogin). Body: { email, password,
    remember, captcha }. Returns the same profile payload as /auth/me/."""
    # Google reCAPTCHA (skipped in local DEBUG mode where the domain-bound
    # key can't verify).
    if not settings.DEBUG:
        data = {
            'secret': CAPTCHA_SECRET,
            'response': request.data.get('captcha'),
        }
        try:
            captcha_server = requests.post(
                url="https://www.google.com/recaptcha/api/siteverify", data=data)
            response = json.loads(captcha_server.text)
            if response['success'] is False:
                return Response({'detail': 'Invalid Captcha. Try Again'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'detail': 'Captcha could not be verified. Try Again'},
                            status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(
        request,
        username=request.data.get('email'),
        password=request.data.get('password'))
    if user is None:
        # A newly-created Staff/Student account has no usable password at
        # all, so it can never "correctly" authenticate before verification
        # — check email existence + is_active directly to give a clearer
        # message than "Invalid details" (the /auth/check-email/ endpoint
        # already reveals whether an email is registered, so this isn't a
        # new leak).
        try:
            candidate = CustomUser.objects.get(email=request.data.get('email'))
        except CustomUser.DoesNotExist:
            candidate = None
        if candidate is not None and not candidate.is_active:
            return Response(
                {'detail': 'Please verify your email before logging in. '
                           'Check your inbox for the verification link.'},
                status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Invalid details'},
                        status=status.HTTP_400_BAD_REQUEST)

    login(request, user)
    if request.data.get('remember'):
        request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
    else:
        request.session.set_expiry(0)  # browser close
    return Response(user_dict(user))


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({'detail': 'Logged out'})


@ensure_csrf_cookie
@api_view(['GET'])
def me(request):
    """Current user for app bootstrap; also plants the csrftoken cookie."""
    return Response(user_dict(request.user))


@api_view(['POST'])
@permission_classes([AllowAny])
def check_email(request):
    """Live email-availability check (check_email_availability)."""
    email = request.data.get('email')
    return Response({'exists': CustomUser.objects.filter(email=email).exists()})


def _user_from_uidb64(uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return None


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_view(request, uidb64, token):
    """Confirm a newly-created Staff/Student's emailed verification link and
    let them set their first password. Body: { password }."""
    user = _user_from_uidb64(uidb64)

    if user is None or not email_verification_token.check_token(user, token):
        return Response({'code': 'INVALID_OR_EXPIRED',
                         'detail': 'This verification link is invalid or has expired.'},
                        status=status.HTTP_400_BAD_REQUEST)

    password = request.data.get('password') or ''
    try:
        validate_password(password, user=user)
    except ValidationError as e:
        return Response({'password': e.messages}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.is_active = True
    user.email_verified = True
    user.save()
    return Response({'detail': 'Email verified. You can now log in.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_admin_email_verification(request):
    """Admin/HOD first-login step, also reused by the profile page's "change
    email" flow: submit the college/uni email address to confirm. Body:
    { email }. Doesn't touch `email` yet — the address is held in
    `pending_email` until the link is actually clicked, so an abandoned or
    mistyped attempt can never lock the admin out of their original login.
    Unlike Staff/Student (see request_email_change below), Admin doesn't need
    approval — the verification link goes out immediately."""
    user = request.user
    if str(user.user_type) != ADMIN:
        return Response({'detail': 'Only Admin accounts use this.'},
                        status=status.HTTP_403_FORBIDDEN)

    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return Response({'email': ['This field is required.']},
                        status=status.HTTP_400_BAD_REQUEST)

    domain = email.rsplit('@', 1)[-1]
    if domain not in ADMIN_ALLOWED_EMAIL_DOMAINS:
        return Response(
            {'email': ["Email must be one of these domains: %s" % ", ".join(
                '@' + d for d in ADMIN_ALLOWED_EMAIL_DOMAINS)]},
            status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.exclude(pk=user.pk).filter(email=email).exists():
        return Response({'email': ['The given email is already registered']},
                        status=status.HTTP_400_BAD_REQUEST)

    user.pending_email = email
    user.save()
    try:
        send_admin_verification_email(user)
    except Exception as e:
        return Response({'detail': "Could not send the email: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': 'Verification email sent.', 'pending_email': email})


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_admin_email_verification(request, uidb64, token):
    """Confirm the link emailed by request_admin_email_verification (Admin)
    or send_email_change_verification (Staff/Student, once admin-approved —
    see approve_email_change below). Applying `pending_email` this way is
    identical for every role, so this one view backs both URLs."""
    user = _user_from_uidb64(uidb64)

    if user is None or not email_verification_token.check_token(user, token):
        return Response({'code': 'INVALID_OR_EXPIRED',
                         'detail': 'This verification link is invalid or has expired.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not user.pending_email:
        return Response({'code': 'NO_PENDING_EMAIL',
                         'detail': 'There is no pending email verification for this account.'},
                        status=status.HTTP_400_BAD_REQUEST)

    user.email = user.pending_email
    user.pending_email = ''
    user.pending_email_approved = False
    user.email_verified = True
    user.save()
    return Response({'detail': 'Email verified.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_email_change(request):
    """Non-admin profile step: submit a new email address. Unlike Admin's flow
    above, this does NOT email a verification link yet — it only records the
    request (`pending_email`) for an admin to review at
    /auth/admin/email-change-requests/. Approving is what actually sends the
    verification email — see approve_email_change below."""
    user = request.user
    role = str(user.user_type)
    if role not in APPROVAL_REQUIRED_ROLES:
        return Response({'detail': 'This account type does not use this flow.'},
                        status=status.HTTP_403_FORBIDDEN)

    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return Response({'email': ['This field is required.']},
                        status=status.HTTP_400_BAD_REQUEST)

    allowed_domains = ROLE_EMAIL_DOMAINS[role]
    domain = email.rsplit('@', 1)[-1]
    if domain not in allowed_domains:
        return Response(
            {'email': ["Email must be one of these domains: %s" % ", ".join(
                '@' + d for d in allowed_domains)]},
            status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.exclude(pk=user.pk).filter(email=email).exists():
        return Response({'email': ['The given email is already registered']},
                        status=status.HTTP_400_BAD_REQUEST)

    user.pending_email = email
    user.pending_email_approved = False
    user.save()
    return Response({'detail': 'Your request has been sent to the admin for approval.',
                     'pending_email': email})


@api_view(['GET'])
@permission_classes([IsAdmin])
def email_change_requests(request):
    """Pending Staff/Student/Librarian email-change requests awaiting admin
    approval (request_email_change above sets these up)."""
    pending = CustomUser.objects.filter(
        user_type__in=APPROVAL_REQUIRED_ROLES, pending_email_approved=False,
    ).exclude(pending_email='')
    return Response([
        {
            'id': u.id,
            'full_name': ("%s %s" % (u.first_name, u.last_name)).strip(),
            'email': u.email,
            'pending_email': u.pending_email,
            'role': ROLE_LABELS.get(str(u.user_type), ''),
        }
        for u in pending
    ])


@api_view(['POST'])
@permission_classes([IsAdmin])
def approve_email_change(request, user_id):
    """Admin approves a Staff/Student/Librarian email-change request: only
    now does the verification link actually go out, to `pending_email`."""
    user = get_object_or_404(CustomUser, pk=user_id)
    if str(user.user_type) not in APPROVAL_REQUIRED_ROLES or not user.pending_email \
            or user.pending_email_approved:
        return Response({'detail': 'No pending email change request for this user.'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        send_email_change_verification(user)
    except Exception as e:
        return Response({'detail': "Could not send the email: " + str(e)},
                        status=status.HTTP_400_BAD_REQUEST)

    user.pending_email_approved = True
    user.save()
    return Response({'detail': 'Approved. Verification email sent.'})


@api_view(['POST'])
@permission_classes([IsAdmin])
def reject_email_change(request, user_id):
    """Admin declines an email-change request; no email is
    ever sent and the account keeps its current address."""
    user = get_object_or_404(CustomUser, pk=user_id)
    user.pending_email = ''
    user.pending_email_approved = False
    user.save()
    return Response({'detail': 'Email change request rejected.'})
