import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout, { usePageHeader } from "./layouts/Layout";
import Login from "./pages/Login";
import AdminDashboard from "./pages/admin/AdminDashboard";

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
            <Route path="/staff/home/" element={<PlaceholderPage />} />
            <Route path="/student/home/" element={<PlaceholderPage />} />
            <Route path="*" element={<PlaceholderPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
