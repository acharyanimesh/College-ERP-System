"""URL routes for the JSON API consumed by the React frontend
(frontend/src/api/*.js). Mounted at /api/v1/."""
from django.urls import path

from . import (academics, accountants, attendance, auth, books, dashboard,
               deposits, fees, leave_feedback, librarians, library,
               notifications, payments, profile, results, staff, students)

urlpatterns = [
    # Auth / session
    path("auth/login/", auth.login_view),
    path("auth/logout/", auth.logout_view),
    path("auth/me/", auth.me),
    path("auth/check-email/", auth.check_email),
    path("auth/verify-email/<str:uidb64>/<str:token>/", auth.verify_email_view),
    path("auth/admin/request-email-verification/",
         auth.request_admin_email_verification),
    path("auth/admin/verify-email/<str:uidb64>/<str:token>/",
         auth.confirm_admin_email_verification),
    path("auth/request-email-change/", auth.request_email_change),
    path("auth/verify-email-change/<str:uidb64>/<str:token>/",
         auth.confirm_admin_email_verification),
    path("auth/admin/email-change-requests/", auth.email_change_requests),
    path("auth/admin/email-change-requests/<int:user_id>/approve/",
         auth.approve_email_change),
    path("auth/admin/email-change-requests/<int:user_id>/reject/",
         auth.reject_email_change),

    # Dashboards
    path("dashboard/admin/", dashboard.admin_home),
    path("dashboard/staff/", dashboard.staff_home),
    path("dashboard/student/", dashboard.student_home),
    path("dashboard/librarian/", dashboard.librarian_home),
    path("dashboard/accountant/", dashboard.accountant_home),

    # Own profile
    path("profile/", profile.profile),

    # Students (admin management)
    path("students/", students.student_list),
    path("students/manage/courses/", students.manage_courses),
    path("students/manage/courses/<int:course_id>/semesters/",
         students.manage_semesters),
    path("students/manage/courses/<int:course_id>/semesters/<int:semester>/shifts/",
         students.manage_shifts),
    path("students/passed-out/", students.passed_out_list),
    path("students/passed-out/courses/", students.passed_out_courses),
    path("students/passed-out/courses/<int:course_id>/sessions/",
         students.passed_out_sessions),
    path("students/<int:student_id>/", students.student_item),
    path("students/<int:student_id>/resend-verification/",
         students.resend_verification),

    # Staff (admin management)
    path("staff/", staff.staff_list),
    path("staff/<int:staff_id>/", staff.staff_item),
    path("staff/<int:staff_id>/subject-assignments/", staff.subject_assignments),
    path("staff/<int:staff_id>/resend-verification/", staff.resend_verification),

    # Librarians (admin management)
    path("librarians/", librarians.librarian_list),
    path("librarians/<int:librarian_id>/", librarians.librarian_item),
    path("librarians/<int:librarian_id>/resend-verification/",
         librarians.resend_verification),

    # Accountants (admin management)
    path("accountants/", accountants.accountant_list),
    path("accountants/<int:accountant_id>/", accountants.accountant_item),
    path("accountants/<int:accountant_id>/resend-verification/",
         accountants.resend_verification),

    # Academics
    path("courses/", academics.course_list),
    path("courses/<int:course_id>/", academics.course_item),
    path("courses/<int:course_id>/promote/", students.promote_class),
    path("courses/<int:course_id>/semesters/<int:semester>/roll-lock/",
         students.roll_number_lock),
    path("subjects/", academics.subject_list),
    path("subjects/manage/courses/<int:course_id>/semesters/",
         academics.subject_semesters),
    path("subjects/<int:subject_id>/", academics.subject_item),
    path("sessions/", academics.session_list),
    path("sessions/<int:session_id>/", academics.session_item),

    # Attendance
    path("attendance/", attendance.attendance_list),
    path("attendance/picker/", attendance.picker),
    path("attendance/students/", attendance.class_students),
    path("attendance/mine/", attendance.my_records),
    path("attendance/admin/courses/", attendance.admin_courses),
    path("attendance/admin/courses/<int:course_id>/students/",
         attendance.admin_students),
    path("attendance/admin/students/<int:student_id>/summary/",
         attendance.student_summary),
    path("attendance/<int:attendance_id>/", attendance.attendance_update),
    path("attendance/<int:attendance_id>/students/",
         attendance.attendance_students),

    # Results
    path("results/classes/", results.classes),
    path("results/class/", results.class_results),
    path("results/class/save/", results.save_class_results),
    path("results/class/finalize/", results.finalize),
    path("results/mine/", results.mine),

    # Leave
    path("leave/<str:role>/", leave_feedback.leave_all),
    path("leave/<str:role>/mine/", leave_feedback.leave_mine),
    path("leave/<str:role>/<int:leave_id>/status/", leave_feedback.leave_status),

    # Feedback
    path("feedback/<str:role>/", leave_feedback.feedback_all),
    path("feedback/<str:role>/mine/", leave_feedback.feedback_mine),
    path("feedback/<str:role>/<int:feedback_id>/reply/",
         leave_feedback.feedback_reply),

    # Notifications
    path("notifications/staff/recipients/", notifications.staff_recipients),
    path("notifications/staff/send/", notifications.send_to_staff),
    path("notifications/student/browse/", notifications.student_browse),
    path("notifications/student/courses/<int:course_id>/semesters/",
         notifications.student_semesters),
    path("notifications/student/recipients/", notifications.student_recipients),
    path("notifications/student/send/", notifications.send_to_student),
    path("notifications/<str:role>/mine/", notifications.mine),

    # Library — catalogue
    path("books/", books.book_list),
    path("books/<int:book_id>/", books.book_item),

    # Library — borrowing
    path("library/requests/", library.request_list),
    path("library/requests/mine/", library.my_requests),
    path("library/requests/<int:request_id>/cancel/", library.cancel),
    path("library/requests/<int:request_id>/approve/", library.approve),
    path("library/requests/<int:request_id>/reject/", library.reject),
    path("library/requests/<int:request_id>/issue/", library.issue),
    path("library/requests/<int:request_id>/return/", library.mark_returned),
    path("library/loans/", library.loans),

    # Library — renewal of a loan (one per loan)
    path("library/requests/<int:request_id>/renew/", library.request_renewal),
    path("library/requests/<int:request_id>/renew/approve/",
         library.approve_renewal),
    path("library/requests/<int:request_id>/renew/reject/",
         library.reject_renewal),

    # Library — fines (cash at the desk; receipts are append-only)
    path("library/fines/", library.fine_records),
    path("library/fines/mine/", library.my_fines),
    path("library/fines/unsettled/", library.unsettled_fines),
    path("library/requests/<int:request_id>/fine/collect/", library.collect_fine),
    path("library/requests/<int:request_id>/fine/waive/", library.waive_fine),

    # Library — due-date reminders (same sweep as the scheduled command)
    path("library/reminders/send/", library.send_reminders),

    # Fees — the chart of fee heads and the structures built from them
    path("fees/heads/", fees.head_list),
    path("fees/heads/<int:head_id>/", fees.head_item),
    path("fees/structures/", fees.structure_list),
    path("fees/structures/<int:structure_id>/", fees.structure_item),
    path("fees/structures/<int:structure_id>/clone/", fees.clone_structure),

    # Fees — raising the bills
    path("fees/invoice-run/preview/", fees.invoice_run_preview),
    path("fees/invoice-run/", fees.invoice_run),

    # Fees — the invoice register
    path("fees/invoices/", fees.invoice_list),
    path("fees/invoices/<int:invoice_id>/", fees.invoice_item),
    path("fees/invoices/<int:invoice_id>/cancel/", fees.cancel_invoice),
    path("fees/invoices/<int:invoice_id>/adjust/", fees.adjust_invoice),

    # Fees — the student's own view. Scoped to the caller, never by id alone.
    path("fees/mine/", fees.my_fees),
    path("fees/mine/receipts/", fees.my_receipts),
    path("fees/mine/slips/", deposits.my_slips),
    path("fees/mine/slips/<int:slip_id>/", deposits.withdraw_slip),
    path("fees/mine/<int:invoice_id>/slips/", deposits.submit_slip),
    path("fees/mine/<int:invoice_id>/", fees.my_invoice),

    # Fees — taking money at the counter (receipts are append-only)
    path("fees/collectable/", payments.collectable),
    path("fees/invoices/<int:invoice_id>/collect/", payments.collect_payment),
    path("fees/payments/", payments.payment_list),
    path("fees/payments/<int:payment_id>/receipt/", payments.receipt),

    # Fees — bank deposit slips: a student's claim, and the office's verdict
    path("fees/slips/", deposits.slip_queue),
    path("fees/slips/<int:slip_id>/verify/", deposits.verify_slip),
    path("fees/slips/<int:slip_id>/reject/", deposits.reject_slip),
]
