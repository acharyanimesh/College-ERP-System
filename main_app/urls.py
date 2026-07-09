"""main_app URLs.

The Django template pages were retired in the React migration: the JSON API
under /api/v1/ (main_app/api/) does the work, and every remaining page route
serves the built React app. Only the password-reset flow stays server-side
(django.contrib.auth views + the registration/ templates), which is why the
'login_page' URL name lives on — those templates link back to it.
"""
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.react_app, name='login_page'),
    # Everything except api/django-admin/accounts/static/media belongs to
    # React Router — including /admin/*, which is the app's own admin ROLE
    # pages, not Django's admin site (that's at /django-admin/).
    re_path(r'^(?!api/|django-admin/|accounts/|static/|media/).*$',
            views.react_app, name='react_app'),
]
