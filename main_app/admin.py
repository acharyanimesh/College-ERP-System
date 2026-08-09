from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.


class UserModel(UserAdmin):
    ordering = ('email',)


admin.site.register(CustomUser, UserModel)
admin.site.register(Staff)
admin.site.register(Librarian)
admin.site.register(Accountant)
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


# ------------------------------------------------------------------ Fees

class ReadOnlyLedgerAdmin(admin.ModelAdmin):
    """Base for the append-only fee rows, matching LibraryFineAdmin above:
    the models themselves refuse updates and deletes, and turning the
    permissions off here means the admin never offers the buttons rather than
    letting someone click one and hit an exception."""

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FeeStructureItemInline(admin.TabularInline):
    model = FeeStructureItem
    extra = 1


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('course', 'session', 'semester', 'total', 'due_days',
                    'late_fine_per_day')
    list_filter = ('course', 'session', 'semester')
    inlines = [FeeStructureItemInline]


class FeeInvoiceLineInline(admin.TabularInline):
    model = FeeInvoiceLine
    extra = 0


@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'student', 'course', 'semester', 'issued_date',
                    'due_date', 'payable', 'paid', 'balance', 'status')
    list_filter = ('course', 'session', 'semester')
    search_fields = ('number', 'student__admin__first_name',
                     'student__admin__last_name', 'student__roll_number')
    inlines = [FeeInvoiceLineInline]


@admin.register(FeePayment)
class FeePaymentAdmin(ReadOnlyLedgerAdmin):
    list_display = ('receipt_no', 'student', 'invoice', 'amount', 'mode',
                    'received_on', 'collected_by_name')
    list_filter = ('mode',)
    search_fields = ('receipt_no', 'reference', 'invoice__number',
                     'student__admin__first_name', 'student__admin__last_name')


@admin.register(FeeAdjustment)
class FeeAdjustmentAdmin(ReadOnlyLedgerAdmin):
    list_display = ('invoice', 'kind', 'amount', 'created_by_name',
                    'created_at')
    list_filter = ('kind',)
    search_fields = ('invoice__number', 'reason')


@admin.register(DepositSlip)
class DepositSlipAdmin(admin.ModelAdmin):
    """Evidence, not a ledger entry, so it is editable here — but verifying
    one is what writes the receipt, and that only happens through
    api/deposits.py. Flipping `status` by hand here would leave a slip marked
    verified with no money recorded against the bill."""
    list_display = ('reference', 'student', 'invoice', 'bank_name', 'amount',
                    'deposited_on', 'status', 'reviewed_by_name')
    list_filter = ('status', 'bank_name')
    search_fields = ('reference', 'invoice__number',
                     'student__admin__first_name', 'student__admin__last_name',
                     'student__roll_number')


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    """Not append-only — an attempt is a state machine — but nothing here
    should be edited by hand either: the reconciliation sweep is what moves
    one, so that a status change always comes with a verified payload."""
    list_display = ('reference', 'student', 'invoice', 'gateway', 'amount',
                    'status', 'created_at', 'resolved_at')
    list_filter = ('gateway', 'status')
    search_fields = ('reference', 'gateway_ref', 'invoice__number')

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(FeeHead)
