from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def _uidb64(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


ROLE_NAMES = {"2": "Staff", "3": "Student", "4": "Librarian",
              "5": "Accountant"}


def send_verification_email(user):
    """Email a newly-created (inactive) Staff/Student/Librarian account owner
    a link to verify their address and set their own password. Raises on send
    failure so the caller can decide how to surface that to the admin."""
    role = ROLE_NAMES.get(str(user.user_type), "Student")
    token = email_verification_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email/{_uidb64(user)}/{token}/"
    send_mail(
        subject="Verify your College ERP account",
        message=(
            f"Hello {user.first_name},\n\n"
            f"An account has been created for you as {role} on the College ERP System.\n"
            f"Please verify your email address and set your password using the link below:\n\n"
            f"{link}\n\n"
            f"This link can only be used once. If you did not expect this email, "
            f"you can safely ignore it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_email_change_verification(user):
    """Email a Staff/Student/Librarian's admin-approved new address (held in
    `user.pending_email`) a link to confirm it. Only called once an admin
    has approved the change — see api/auth.py's approve_email_change.
    Raises on send failure so the caller can surface it."""
    token = email_verification_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email-change/{_uidb64(user)}/{token}/"
    send_mail(
        subject="Confirm your new College ERP email address",
        message=(
            f"Hello {user.first_name},\n\n"
            f"Your request to change your College ERP account email has been "
            f"approved. Please confirm this address by following the link "
            f"below:\n\n"
            f"{link}\n\n"
            f"This link can only be used once. If you did not request this, "
            f"you can safely ignore it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.pending_email],
        fail_silently=False,
    )


def send_admin_verification_email(user):
    """Email the institutional address an Admin/HOD entered on their
    first-login setup screen (held in `user.pending_email` until confirmed).
    Raises on send failure so the caller can surface it."""
    token = email_verification_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/verify-admin-email/{_uidb64(user)}/{token}/"
    send_mail(
        subject="Confirm your College ERP admin email",
        message=(
            f"Hello {user.first_name},\n\n"
            f"Please confirm this address as your College ERP admin login by "
            f"following the link below:\n\n"
            f"{link}\n\n"
            f"This link can only be used once. If you did not request this, "
            f"you can safely ignore it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.pending_email],
        fail_silently=False,
    )
