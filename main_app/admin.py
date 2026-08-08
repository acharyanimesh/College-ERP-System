from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.


class UserModel(UserAdmin):
    ordering = ('email',)


admin.site.register(CustomUser, UserModel)
admin.site.register(Staff)
admin.site.register(Librarian)
admin.site.register(Student)
admin.site.register(Course)
admin.site.register(Book)
admin.site.register(BookRequest)


@admin.register(LibraryFine)
class LibraryFineAdmin(admin.ModelAdmin):
    """Cash receipts, viewable but not touchable.

    The model itself refuses updates and deletes; turning the permissions off
    here as well means the admin never offers the buttons in the first place,
    rather than letting someone click one and hit an exception.
    """
    list_display = ('receipt_no', 'student', 'amount', 'kind',
                    'collected_by_name', 'created_at')
    list_filter = ('kind',)
    search_fields = ('receipt_no', 'student__admin__first_name',
                     'student__admin__last_name')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
admin.site.register(Subject)
admin.site.register(Session)
