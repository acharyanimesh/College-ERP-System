import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout, { usePageHeader } from "./layouts/Layout";

/**
 * Temporary layout preview while pages are converted (Phase 5 replaces this
 * with the real routes + auth). Change PREVIEW_USER.user_type to '1' / '2' /
 * '3' to preview the admin, staff, or student chrome.
 */
const PREVIEW_USER = {
  user_type: "1",
  full_name: "Layout Preview",
  email: "preview@example.com",
  profile_pic: "",
};

function PlaceholderPage() {
  usePageHeader({ title: "Dashboard" });
  return (
    <div className="card">
      <div className="card-body">
        <h5 className="card-title">Layout preview</h5>
        <p className="text-muted mb-0">
          Navbar, sidebar, dark mode and the Vanta background are live. Pages
          are converted here one-by-one during the migration.
        </p>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout user={PREVIEW_USER} />}>
          <Route path="*" element={<PlaceholderPage />} />
        </Route>
        <Route path="/" element={<Navigate to="/admin/home/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
