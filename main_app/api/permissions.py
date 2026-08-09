from rest_framework.permissions import BasePermission

# user_type codes from CustomUser.USER_TYPE.
ADMIN, STAFF, STUDENT, LIBRARIAN, ACCOUNTANT = '1', '2', '3', '4', '5'


def _has_type(request, *types):
    return (
        request.user
        and request.user.is_authenticated
        and str(request.user.user_type) in types
    )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return _has_type(request, ADMIN)


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return _has_type(request, STAFF)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return _has_type(request, STUDENT)


class IsLibrarian(BasePermission):
    def has_permission(self, request, view):
        return _has_type(request, LIBRARIAN)


class IsLibrarianOrAdmin(BasePermission):
    """Library management, plus the admin's read-only oversight of it."""

    def has_permission(self, request, view):
        return _has_type(request, LIBRARIAN, ADMIN)


class IsAccountant(BasePermission):
    def has_permission(self, request, view):
        return _has_type(request, ACCOUNTANT)


class IsAccountantOrAdmin(BasePermission):
    """The accounts office, plus the admin's READ-ONLY oversight of it.

    The admin half is for looking only: the whole point of splitting the role
    out is that whoever can delete a student cannot also move money around.
    This class cannot enforce that on its own, so use it only on endpoints
    that read — anything that writes belongs behind IsAccountant.
    """

    def has_permission(self, request, view):
        return _has_type(request, ACCOUNTANT, ADMIN)
