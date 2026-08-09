import { Link } from "react-router-dom";
import brandIcon from "../assets/image/brand-icon.png";

/** Home route per user_type — mirrors the url-name switches in base.html. */
export function homePath(userType) {
  if (String(userType) === "1") return "/admin/home/";
  if (String(userType) === "2") return "/staff/home/";
  if (String(userType) === "4") return "/librarian/home/";
  if (String(userType) === "5") return "/accountant/home/";
  return "/student/home/";
}

/**
 * Top navigation bar (base.html <nav class="erpnext-navbar">):
 * sidebar toggle, brand link, and logout button.
 */
function Navbar({ user, onToggleSidebar, onLogout }) {
  return (
    <nav className="erpnext-navbar">
      <div className="navbar-left">
        <button className="navbar-toggle" onClick={onToggleSidebar}>
          <i className="fas fa-bars"></i>
        </button>
        <Link to={homePath(user?.user_type)} className="navbar-brand">
          <img src={brandIcon} alt="" className="navbar-brand-icon" />
          <span className="navbar-brand-text">College ERP</span>
        </Link>
      </div>

      <div className="navbar-user">
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
