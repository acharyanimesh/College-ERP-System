import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout, { usePageHeader } from "./layouts/Layout";
import Login from "./pages/Login";
import AdminDashboard from "./pages/admin/AdminDashboard";
import StaffDashboard from "./pages/staff/StaffDashboard";
import StudentDashboard from "./pages/student/StudentDashboard";
import StudentFormPage from "./pages/admin/students/StudentFormPage";
import ManageStudents from "./pages/admin/students/ManageStudents";
import StudentSemesters from "./pages/admin/students/StudentSemesters";
import StudentShifts from "./pages/admin/students/StudentShifts";
import StudentList from "./pages/admin/students/StudentList";
import StudentDetails from "./pages/admin/students/StudentDetails";
import {
  PassedOutCourses,
  PassedOutSessions,
  PassedOutStudentList,
} from "./pages/admin/students/PassedOutStudents";
import StaffFormPage from "./pages/admin/staff/StaffFormPage";
import ManageStaff from "./pages/admin/staff/ManageStaff";
import StaffDetails from "./pages/admin/staff/StaffDetails";
import AssignStaffSubjects from "./pages/admin/staff/AssignStaffSubjects";
import CourseFormPage from "./pages/admin/academics/CourseFormPage";
import ManageCourses from "./pages/admin/academics/ManageCourses";
import CourseSemesterList from "./pages/admin/academics/CourseSemesterList";
import SubjectListByCourse from "./pages/admin/academics/SubjectListByCourse";
import SubjectFormPage from "./pages/admin/academics/SubjectFormPage";
import SubjectDetails from "./pages/admin/academics/SubjectDetails";
import { SessionFormPage, ManageSessions } from "./pages/admin/academics/SessionPages";
import {
  AdminViewAttendance,
  AttendanceStudentList,
  StudentAttendanceDetail,
} from "./pages/admin/attendance/AdminAttendancePages";
import NotifyStaff from "./pages/admin/notify/NotifyStaff";
import {
  NotifyStudent,
  NotifyStudentSemesters,
  NotifyStudentList,
} from "./pages/admin/notify/NotifyStudentPages";
import LeaveView from "./pages/admin/review/LeaveView";
import FeedbackView from "./pages/admin/review/FeedbackView";
import ProfilePage from "./pages/shared/ProfilePage";
import ApplyLeave from "./pages/shared/ApplyLeave";
import FeedbackPage from "./pages/shared/FeedbackPage";
import NotificationsPage from "./pages/shared/NotificationsPage";
import StaffTakeAttendance from "./pages/staff/StaffTakeAttendance";
import StaffUpdateAttendance from "./pages/staff/StaffUpdateAttendance";
import StaffViewAttendance from "./pages/staff/StaffViewAttendance";
import StaffAddResult from "./pages/staff/StaffAddResult";
import EditStudentResult from "./pages/staff/EditStudentResult";
import AddBook from "./pages/staff/AddBook";

/** Stand-in until each dashboard/page is converted in Phase 5. */
function PlaceholderPage() {
  usePageHeader({ title: "Dashboard" });
  return (
    <div className="card">
      <div className="card-body">
        <h5 className="card-title">Page not converted yet</h5>
        <p className="text-muted mb-0">
          This screen is still served by the Django templates; it will be
          migrated here page-by-page.
        </p>
      </div>
    </div>
  );
}

/**
 * Auth gate around the app chrome, replacing Django's @login_required:
 * waits for the session check, then either shows the layout or bounces to
 * the login screen.
 */
function ProtectedLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  if (loading) return null;
  if (!user) return <Navigate to="/" replace />;

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return <Layout user={user} onLogout={handleLogout} />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Login (redirects home when already authenticated) */}
          <Route path="/" element={<Login />} />

          {/* Everything behind the session, mirroring Django's URL paths */}
          <Route element={<ProtectedLayout />}>
            <Route path="/admin/home/" element={<AdminDashboard />} />

            {/* Students (admin) */}
            <Route path="/student/add/" element={<StudentFormPage />} />
            <Route path="/student/edit/:studentId" element={<StudentFormPage edit />} />
            <Route path="/student/manage/" element={<ManageStudents />} />
            <Route path="/student/manage/course/:courseId/" element={<StudentSemesters />} />
            <Route
              path="/student/manage/course/:courseId/semester/:semester/"
              element={<StudentShifts />}
            />
            <Route
              path="/student/manage/course/:courseId/semester/:semester/shift/:shift/"
              element={<StudentList />}
            />
            <Route path="/student/details/:studentId" element={<StudentDetails />} />
            <Route path="/student/passed-out/" element={<PassedOutCourses />} />

            {/* Staff (admin) */}
            <Route path="/staff/add" element={<StaffFormPage />} />
            <Route path="/staff/edit/:staffId" element={<StaffFormPage edit />} />
            <Route path="/staff/manage/" element={<ManageStaff />} />
            <Route path="/staff/view/:staffId" element={<StaffDetails />} />
            <Route path="/staff/assign-subjects/:staffId" element={<AssignStaffSubjects />} />

            {/* Courses / Subjects / Sessions (admin) */}
            <Route path="/course/add" element={<CourseFormPage />} />
            <Route path="/course/edit/:courseId" element={<CourseFormPage edit />} />
            <Route path="/course/manage/" element={<ManageCourses />} />
            <Route path="/subject/manage/course/:courseId/" element={<CourseSemesterList />} />
            <Route
              path="/subject/manage/course/:courseId/semester/:semester/"
              element={<SubjectListByCourse />}
            />
            <Route path="/subject/add/" element={<SubjectFormPage />} />
            <Route path="/subject/edit/:subjectId" element={<SubjectFormPage edit />} />
            <Route path="/subject/view/:subjectId" element={<SubjectDetails />} />
            <Route path="/add_session/" element={<SessionFormPage />} />
            <Route path="/session/edit/:sessionId" element={<SessionFormPage edit />} />
            <Route path="/session/manage/" element={<ManageSessions />} />

            {/* Attendance / communication / review (admin) */}
            <Route path="/attendance/view/" element={<AdminViewAttendance />} />
            <Route path="/attendance/view/course/:courseId/" element={<AttendanceStudentList />} />
            <Route
              path="/attendance/view/student/:studentId/"
              element={<StudentAttendanceDetail />}
            />
            <Route path="/admin_notify_staff" element={<NotifyStaff />} />
            <Route path="/admin_notify_student" element={<NotifyStudent />} />
            <Route
              path="/admin_notify_student/course/:courseId/"
              element={<NotifyStudentSemesters />}
            />
            <Route
              path="/admin_notify_student/course/:courseId/semester/:semester/"
              element={<NotifyStudentList />}
            />
            <Route path="/staff/view/leave/" element={<LeaveView role="staff" />} />
            <Route path="/student/view/leave/" element={<LeaveView role="student" />} />
            <Route path="/staff/view/feedback/" element={<FeedbackView role="staff" />} />
            <Route path="/student/view/feedback/" element={<FeedbackView role="student" />} />
            <Route path="/admin_view_profile" element={<ProfilePage />} />

            {/* Staff role pages */}
            <Route path="/staff/attendance/take/" element={<StaffTakeAttendance />} />
            <Route path="/staff/attendance/update/" element={<StaffUpdateAttendance />} />
            <Route path="/staff/attendance/view/" element={<StaffViewAttendance />} />
            <Route path="/staff/apply/leave/" element={<ApplyLeave role="staff" />} />
            <Route path="/staff/feedback/" element={<FeedbackPage role="staff" />} />
            <Route path="/staff/result/add/" element={<StaffAddResult />} />
            <Route path="/staff/result/edit/" element={<EditStudentResult />} />
            <Route path="/staff/addbook/" element={<AddBook />} />
            <Route
              path="/staff/view/notification/"
              element={<NotificationsPage role="staff" />}
            />
            <Route path="/staff/view/profile/" element={<ProfilePage />} />
            <Route path="/student/passed-out/course/:courseId/" element={<PassedOutSessions />} />
            <Route
              path="/student/passed-out/course/:courseId/session/:sessionId/"
              element={<PassedOutStudentList />}
            />
            <Route path="/staff/home/" element={<StaffDashboard />} />
            <Route path="/student/home/" element={<StudentDashboard />} />
            <Route path="*" element={<PlaceholderPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
