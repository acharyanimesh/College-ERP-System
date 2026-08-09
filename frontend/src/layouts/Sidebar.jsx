import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { menuForUserType } from "./sidebarMenu";

const ROLE_LABELS = {
  1: "Administrator",
  2: "Staff Member",
  3: "Student",
  4: "Librarian",
  5: "Accountant",
};

/** Replicates the template's active rule: exact path match OR any extra substring. */
function isActive(pathname, item) {
  if (item.to === pathname) return true;
  return (item.active || []).some((frag) => pathname.includes(frag));
}

function MenuLink({ item, onNavigate }) {
  const { pathname } = useLocation();
  return (
    <div className="nav-item">
      <Link
        to={item.to}
        className={`nav-link ${isActive(pathname, item) ? "active" : ""}`}
        onClick={onNavigate}
      >
        {item.icon && (
          <i className={`${item.navIcon === false ? "" : "nav-icon "}${item.icon}`}></i>
        )}
        <span className="nav-text">{item.text}</span>
      </Link>
    </div>
  );
}

function SubMenu({ item, isOpen, onToggle, onNavigate }) {
  return (
    <div className={`nav-item has-submenu ${isOpen ? "open" : ""}`}>
      <a
        href="#"
        className="nav-link"
        onClick={(e) => {
          e.preventDefault();
          onToggle();
        }}
      >
        <i className={`nav-icon ${item.icon}`}></i>
        <span className="nav-text">{item.text}</span>
        <i className="nav-arrow fas fa-chevron-right"></i>
      </a>
      <div className="nav-submenu">
        {item.children.map((child) => (
          <MenuLink key={child.text} item={child} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}

/**
 * Sidebar content (erpnext_sidebar.html): user header + role-based menu.
 * Submenus behave like the template: clicking one toggles it and closes the
 * others; submenus whose `openWhen` fragments match the URL start open.
 *
 * `onNavigate` is called when any real link is clicked (the layout uses it to
 * auto-close the sidebar on mobile, like the legacy script).
 */
function Sidebar({ user, onNavigate }) {
  const { pathname } = useLocation();
  const menu = menuForUserType(user?.user_type);
  const [avatarBroken, setAvatarBroken] = useState(false);
  // Which submenu is open (by item text); initialised from the current path.
  const [openSubmenu, setOpenSubmenu] = useState(() => {
    for (const section of menu) {
      for (const item of section.items) {
        if (item.children && (item.openWhen || []).some((f) => pathname.includes(f))) {
          return item.text;
        }
      }
    }
    return null;
  });

  const showDefaultAvatar = avatarBroken || !user?.profile_pic;

  return (
    <>
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <div className="sidebar-user">
          {!showDefaultAvatar && (
            <img
              src={user.profile_pic}
              alt="User Avatar"
              className="sidebar-user-avatar"
              onError={() => setAvatarBroken(true)}
            />
          )}
          {showDefaultAvatar && (
            <i className="fas fa-user-circle sidebar-default-avatar" style={{ display: "inline-block" }}></i>
          )}
          <div className="sidebar-user-info">
            <h6>{user?.full_name || user?.email}</h6>
            <small>{ROLE_LABELS[String(user?.user_type)] || "Student"}</small>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <div className="nav-section">
        {menu.map((section) => (
          <div key={section.title}>
            <h6 className="nav-section-title">{section.title}</h6>
            {section.items.map((item) =>
              item.children ? (
                <SubMenu
                  key={item.text}
                  item={item}
                  isOpen={openSubmenu === item.text}
                  onToggle={() =>
                    setOpenSubmenu((open) => (open === item.text ? null : item.text))
                  }
                  onNavigate={onNavigate}
                />
              ) : (
                <MenuLink key={item.text} item={item} onNavigate={onNavigate} />
              )
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export default Sidebar;
