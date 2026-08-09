/**
 * Sidebar menu definitions, one per user_type — a data version of
 * main_app/templates/main_app/erpnext_sidebar.html. Paths mirror the Django
 * URLs so the two frontends stay mentally interchangeable.
 *
 * `active` (optional): extra substrings of the current path that should also
 * mark the link active (the template's `'edit_course' in request.path` rules).
 * `openWhen` (submenus): substrings that auto-open the submenu on load.
 */

export const ADMIN_MENU = [
  {
    title: "Main",
    items: [
      { text: "Dashboard", icon: "fas fa-tachometer-alt", to: "/admin/home/" },
      { text: "Profile", icon: "fas fa-user-circle", to: "/admin_view_profile", navIcon: false },
    ],
  },
  {
    title: "Academic Management",
    items: [
      {
        text: "Courses",
        icon: "fas fa-graduation-cap",
        openWhen: ["course", "subject"],
        children: [
          { text: "Add Course", to: "/course/add" },
          { text: "Manage Courses", to: "/course/manage/", active: ["edit_course", "subject/manage"] },
          { text: "Add Subject", to: "/subject/add/" },
        ],
      },
      {
        text: "Sessions",
        icon: "fas fa-calendar-alt",
        openWhen: ["session"],
        children: [
          { text: "Add Session", to: "/add_session/" },
          { text: "Manage Sessions", to: "/session/manage/", active: ["edit_session"] },
        ],
      },
    ],
  },
  {
    title: "User Management",
    items: [
      { text: "Add Staff", icon: "fas fa-user-plus", to: "/staff/add" },
      { text: "Manage Staff", icon: "fas fa-users-cog", to: "/staff/manage/", active: ["edit_staff"] },
      { text: "Add Student", icon: "fas fa-user-graduate", to: "/student/add/" },
      { text: "Manage Students", icon: "fas fa-users", to: "/student/manage/", active: ["edit_student"] },
      { text: "Passed Out Students", icon: "fas fa-user-graduate", to: "/student/passed-out/", active: ["passed-out"] },
      { text: "Add Librarian", icon: "fas fa-book-reader", to: "/librarian/add" },
      { text: "Manage Librarians", icon: "fas fa-address-book", to: "/librarian/manage/", active: ["/librarian/edit/", "/librarian/details/"] },
      { text: "Add Accountant", icon: "fas fa-user-tie", to: "/accountant/add" },
      { text: "Manage Accountants", icon: "fas fa-money-check-alt", to: "/accountant/manage/", active: ["/accountant/edit/", "/accountant/details/"] },
    ],
  },
  {
    title: "Communication",
    items: [
      { text: "Notify Staff", icon: "fas fa-bell", to: "/admin_notify_staff" },
      { text: "Notify Students", icon: "fas fa-bullhorn", to: "/admin_notify_student" },
    ],
  },
  {
    title: "Reports & Analytics",
    items: [
      { text: "View Attendance", icon: "fas fa-chart-line", to: "/attendance/view/" },
      { text: "Student Feedback", icon: "fas fa-comments", to: "/student/view/feedback/" },
      { text: "Staff Feedback", icon: "fas fa-comment-dots", to: "/staff/view/feedback/" },
    ],
  },
  {
    title: "Leave Management",
    items: [
      { text: "Staff Leave", icon: "fas fa-calendar-check", to: "/staff/view/leave/" },
      { text: "Student Leave", icon: "fas fa-calendar-times", to: "/student/view/leave/" },
    ],
  },
  {
    title: "Account Requests",
    items: [
      {
        text: "Email Change Requests",
        icon: "fas fa-envelope-open-text",
        to: "/admin/email-change-requests/",
      },
    ],
  },
];

export const STAFF_MENU = [
  {
    title: "Main",
    items: [
      { text: "Dashboard", icon: "fas fa-tachometer-alt", to: "/staff/home/" },
      { text: "Profile", icon: "fas fa-user-circle", to: "/staff/view/profile/", navIcon: false },
    ],
  },
  {
    title: "Academic Management",
    items: [
      { text: "Manage Result", icon: "fas fa-clipboard-list", to: "/staff/result/manage/" },
    ],
  },
  {
    title: "Attendance",
    items: [
      { text: "Take Attendance", icon: "fas fa-check-circle", to: "/staff/attendance/take/" },
      { text: "Update Attendance", icon: "fas fa-calendar-edit", to: "/staff/attendance/update/" },
      { text: "View Attendance", icon: "fas fa-clipboard-list", to: "/staff/attendance/view/" },
    ],
  },
  {
    title: "Communication",
    items: [
      { text: "Notifications", icon: "fas fa-bell", to: "/staff/view/notification/" },
      { text: "Apply for Leave", icon: "fas fa-calendar-plus", to: "/staff/apply/leave/" },
      { text: "Feedback", icon: "fas fa-comment-alt", to: "/staff/feedback/" },
    ],
  },
];

export const STUDENT_MENU = [
  {
    title: "Main",
    items: [
      { text: "Dashboard", icon: "fas fa-tachometer-alt", to: "/student/home/" },
      { text: "Profile", icon: "fas fa-user-circle", to: "/student/view/profile/", navIcon: false },
    ],
  },
  {
    title: "Academic",
    items: [
      { text: "View Attendance", icon: "fas fa-calendar-check", to: "/student/view/attendance/" },
      { text: "View Results", icon: "fas fa-chart-bar", to: "/student/view/result/" },
    ],
  },
  {
    title: "Library & Resources",
    items: [
      { text: "Library Books", icon: "fas fa-book", to: "/student/viewbooks/" },
      { text: "My Borrowings", icon: "fas fa-bookmark", to: "/student/borrowings/" },
    ],
  },
  {
    title: "Communication",
    items: [
      { text: "Notifications", icon: "fas fa-bell", to: "/student/view/notification/" },
      { text: "Apply for Leave", icon: "fas fa-calendar-plus", to: "/student/apply/leave/" },
      { text: "Feedback", icon: "fas fa-comment-alt", to: "/student/feedback/" },
    ],
  },
];

export const LIBRARIAN_MENU = [
  {
    title: "Main",
    items: [
      { text: "Dashboard", icon: "fas fa-tachometer-alt", to: "/librarian/home/" },
      { text: "Profile", icon: "fas fa-user-circle", to: "/librarian/view/profile/", navIcon: false },
    ],
  },
  {
    title: "Circulation",
    items: [
      { text: "Borrow Requests", icon: "fas fa-inbox", to: "/librarian/requests/" },
      { text: "Issued Books", icon: "fas fa-hand-holding", to: "/librarian/issued/" },
      { text: "Fines", icon: "fas fa-money-bill-wave", to: "/librarian/fines/" },
    ],
  },
  {
    title: "Catalogue",
    items: [
      { text: "Add Book", icon: "fas fa-book-medical", to: "/librarian/books/add/" },
      { text: "Manage Books", icon: "fas fa-book-open", to: "/librarian/books/", active: ["/librarian/books/edit/"] },
    ],
  },
];

export const ACCOUNTANT_MENU = [
  {
    title: "Main",
    items: [
      { text: "Dashboard", icon: "fas fa-tachometer-alt", to: "/accountant/home/" },
      { text: "Profile", icon: "fas fa-user-circle", to: "/accountant/view/profile/", navIcon: false },
    ],
  },
  {
    title: "Fee Collection",
    items: [
      { text: "Collect Fee", icon: "fas fa-cash-register", to: "/accountant/collect/" },
      { text: "Payments", icon: "fas fa-receipt", to: "/accountant/payments/" },
    ],
  },
  {
    title: "Configuration",
    items: [
      { text: "Fee Structure", icon: "fas fa-list-ol", to: "/accountant/fees/" },
      { text: "Library Fines", icon: "fas fa-book", to: "/accountant/library-fines/" },
    ],
  },
];

export function menuForUserType(userType) {
  const t = String(userType);
  if (t === "1") return ADMIN_MENU;
  if (t === "2") return STAFF_MENU;
  if (t === "4") return LIBRARIAN_MENU;
  if (t === "5") return ACCOUNTANT_MENU;
  return STUDENT_MENU;
}
