"""Bits every person-shaped admin endpoint needs.

Students, staff and librarians are all a CustomUser plus a role profile, and
their add/edit views do the same two chores: stash an uploaded photo, and copy
the shared CustomUser fields off a validated CustomUserForm subclass. Those
lived twice before the librarian role arrived; they live here now.
"""
from django.core.files.storage import FileSystemStorage


def save_profile_pic(files):
    """Store an uploaded `profile_pic` and return its URL, or None if the
    request didn't carry one (which an edit reads as "leave it alone")."""
    passport = files.get('profile_pic')
    if not passport:
        return None
    fs = FileSystemStorage()
    filename = fs.save(passport.name, passport)
    return fs.url(filename)


def apply_user_fields(user, form):
    """Copy the shared CustomUser fields out of a valid CustomUserForm.

    `middle_name` is only on the student form, so it is applied only when the
    form actually carries it — the other roles keep whatever they had.
    """
    get = form.cleaned_data.get
    user.first_name = get('first_name')
    user.last_name = get('last_name')
    if 'middle_name' in form.cleaned_data:
        user.middle_name = get('middle_name')
    user.gender = get('gender')
    user.address_line1 = get('address_line1')
    user.address_line2 = get('address_line2')
    user.city = get('city')
    user.province = get('province')
    user.address = ", ".join(filter(None, [
        get('address_line1'), get('address_line2'), get('city'), get('province')]))
    user.phone_number = get('phone_number')
    user.date_of_birth = get('date_of_birth')
