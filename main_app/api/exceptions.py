from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """DRF returns 403 for unauthenticated session requests (no WWW-Authenticate
    header); the React app's axios interceptor listens for 401 to trigger a
    re-login, so translate NotAuthenticated accordingly."""
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, NotAuthenticated):
        response.status_code = status.HTTP_401_UNAUTHORIZED
    return response
