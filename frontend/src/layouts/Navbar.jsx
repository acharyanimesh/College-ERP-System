import { Link } from "react-router-dom";

/** Home route per user_type — mirrors the url-name switches in base.html. */
export function homePath(userType) {
  if (String(userType) === "1") return "/admin/home/";
  if (String(userType) === "2") return "/staff/home/";
  return "/student/home/";
}

/**
 * Top navigation bar (base.html <nav class="erpnext-navbar">):
 * sidebar toggle, brand link, dark-mode capsule slider, logout button.
 */
function Navbar({ user, theme, onToggleTheme, onToggleSidebar, onLogout }) {
  return (
    <nav className="erpnext-navbar">
      <div className="navbar-left">
        <button className="navbar-toggle" onClick={onToggleSidebar}>
          <i className="fas fa-bars"></i>
        </button>
        <Link to={homePath(user?.user_type)} className="navbar-brand">
          College ERP
        </Link>
      </div>

      <div className="navbar-user">
        {/* Dark Mode Toggle */}
        <label className="theme-toggle" htmlFor="theme-switch">
          <input
            type="checkbox"
            id="theme-switch"
            checked={theme === "dark"}
            onChange={onToggleTheme}
          />
          <span className="slider">
            <i className="fas fa-sun icon-light"></i>
            <i className="fas fa-moon icon-dark"></i>
          </span>
        </label>

        {/* Logout Button */}
        <Link
          to="/logout"
          className="btn btn-outline-primary btn-sm logout-btn"
          onClick={(e) => {
            if (onLogout) {
              e.preventDefault();
              onLogout();
            }
          }}
        >
          <i className="fas fa-sign-out-alt"></i>
          <span className="logout-text">Logout</span>
        </Link>
      </div>
    </nav>
  );
}

export default Navbar;
