from django.core.files.storage import FileSystemStorage
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET', 'PUT'])
def profile(request):
    """Own profile for whichever role is logged in (admin/staff/student
    view_profile pages all edited the same CustomUser fields)."""
    user = request.user
    if request.method == 'GET':
        return Response({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'gender': user.gender,
            'address': user.address,
            'profile_pic': user.profile_pic.url if user.profile_pic else '',
            'pending_email': user.pending_email,
            'pending_email_approved': user.pending_email_approved,
        })

    # Email is intentionally NOT editable here — changing it goes through a
    # verification flow instead (Admin: instant emailed link; Staff/Student:
    # admin approval before the link is sent). See auth.py's
    # request_admin_email_verification / request_email_change.
    data = request.data
    errors = {}
    for field in ('first_name', 'last_name'):
        if not (data.get(field) or '').strip():
            errors[field] = ['This field is required.']
    if errors:
        return Response(errors, status=400)

    user.first_name = data.get('first_name')
    user.last_name = data.get('last_name')
    if data.get('gender'):
        user.gender = data.get('gender')
    if 'address' in data:
        user.address = data.get('address') or ''
    password = data.get('password') or None
    if password is not None:
        user.set_password(password)  # logs the session out, as the UI warns
    passport = request.FILES.get('profile_pic')
    if passport is not None:
        fs = FileSystemStorage()
        filename = fs.save(passport.name, passport)
        user.profile_pic = fs.url(filename)
    user.save()
    return Response({'detail': 'Profile Updated!'})
