"""URL routes for the JSON API consumed by the React frontend
(frontend/src/api/*.js). Mounted at /api/v1/."""
from django.urls import path

from . import (academics, attendance, auth, books, dashboard, leave_feedback,
               notifications, profile, results, staff, students)

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

    # Academics
    path("courses/", academics.course_list),
    path("courses/<int:course_id>/", academics.course_item),
    path("courses/<int:course_id>/promote/", students.promote_class),
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

    # Library
    path("books/", books.book_list),
    path("books/issue/", books.issue),
    path("books/issued/", books.issued),
]
