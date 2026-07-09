import json

import requests
from django.conf import settings
from django.contrib.auth import login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..EmailBackend import EmailBackend
from ..models import CustomUser
from .serializers import user_dict

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

    user = EmailBackend.authenticate(
        request,
        username=request.data.get('email'),
        password=request.data.get('password'))
    if user is None:
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
