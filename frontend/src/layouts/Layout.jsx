import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { Link, Outlet } from "react-router-dom";
import Navbar, { homePath } from "./Navbar";
import Sidebar from "./Sidebar";

/* ------------------------------------------------------------------ */
/* Page header + flash messages, replacing the Django template blocks  */
/* ({% block page_title %}, {% block breadcrumb %}, {% if messages %}) */
/* ------------------------------------------------------------------ */

const LayoutContext = createContext(null);

/**
 * Called by each page to fill the layout's header, exactly like the Django
 * blocks did:  usePageHeader({ title, subtitle, breadcrumb: [{text, to?}] })
 */
export function usePageHeader({ title, subtitle = "", breadcrumb = [] }) {
  const ctx = useContext(LayoutContext);
  const setHeader = ctx?.setHeader;
  useEffect(() => {
    if (setHeader) setHeader({ title, subtitle, breadcrumb });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setHeader, title, subtitle, JSON.stringify(breadcrumb)]);
}

/** Flash messages, replacing Django's messages framework in the layout. */
export function useMessages() {
  const ctx = useContext(LayoutContext);
  return { addMessage: ctx?.addMessage || (() => {}) };
}

/* ------------------------------------------------------------------ */

const ROLE_BODY_CLASSES = {
  1: ["admin-bg", "glass-theme"],
  2: ["staff-bg", "glass-theme"],
  3: ["student-bg", "glass-theme"],
};

const MOBILE_BREAKPOINT = 768;

/**
 * Master structural wrapper replicating base.html: navbar + sidebar +
 * <main class="erpnext-main"> with page header, messages and content area.
 * Pages render via <Outlet /> and set their header with usePageHeader().
 */
function Layout({ user, onLogout }) {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");
  const [sidebarOpen, setSidebarOpen] = useState(
    () => localStorage.getItem("sidebarOpen") === "true"
  );
  const [header, setHeader] = useState({ title: "Dashboard", subtitle: "", breadcrumb: [] });
  const [messages, setMessages] = useState([]);
  const nextMessageId = useRef(1);

  /* --- Role background classes on <body> (base.html body class attr) --- */
  useEffect(() => {
    const classes = ROLE_BODY_CLASSES[String(user?.user_type)] || [];
    document.body.classList.add(...classes);
    return () => document.body.classList.remove(...classes);
  }, [user]);

  /* --- Dark mode: body class + localStorage, like the legacy toggle --- */
  useEffect(() => {
    document.body.classList.toggle("dark-mode", theme === "dark");
    localStorage.setItem("theme", theme);
    // Charts and other listeners can restyle themselves on this event.
    window.dispatchEvent(new CustomEvent("themechange", { detail: { theme } }));
  }, [theme]);

  /* --- Sidebar open/collapsed body classes (mobile vs desktop rules) --- */
  useEffect(() => {
    const apply = () => {
      const body = document.body;
      if (window.innerWidth <= MOBILE_BREAKPOINT) {
        // Mobile: open shows the overlay sidebar, closed collapses it.
        body.classList.toggle("sidebar-open", sidebarOpen);
        body.classList.toggle("sidebar-collapsed", !sidebarOpen);
      } else {
        // Desktop: "open" means the user collapsed the sidebar.
        body.classList.toggle("sidebar-collapsed", sidebarOpen);
        body.classList.remove("sidebar-open");
      }
    };
    apply();
    localStorage.setItem("sidebarOpen", String(sidebarOpen));
    window.addEventListener("resize", apply);
    return () => window.removeEventListener("resize", apply);
  }, [sidebarOpen]);

  /* --- Auto-close the sidebar on mobile after navigating (legacy JS) --- */
  const handleSidebarNavigate = useCallback(() => {
    if (window.innerWidth <= MOBILE_BREAKPOINT) setSidebarOpen(false);
  }, []);

  /* --- Flash messages with the 5-second auto-dismiss from base.html --- */
  const addMessage = useCallback((text, tag = "info") => {
    const id = nextMessageId.current++;
    setMessages((msgs) => [...msgs, { id, text, tag }]);
    setTimeout(() => {
      setMessages((msgs) => msgs.filter((m) => m.id !== id));
    }, 5000);
  }, []);

  const dismissMessage = (id) =>
    setMessages((msgs) => msgs.filter((m) => m.id !== id));

  return (
    <LayoutContext.Provider value={{ setHeader, addMessage }}>
      {/* Navigation Bar */}
      <Navbar
        user={user}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        onLogout={onLogout}
      />

      {/* Sidebar */}
      <aside className="erpnext-sidebar">
        <Sidebar user={user} onNavigate={handleSidebarNavigate} />
      </aside>

      {/* Main Content */}
      <main className="erpnext-main" id="main-content">
        {/* Page Header */}
        <div className="page-header">
          <h1 className="page-title">{header.title}</h1>
          {header.subtitle && <p className="page-subtitle">{header.subtitle}</p>}

          {/* Breadcrumb */}
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb">
              <li className="breadcrumb-item">
                <Link to={homePath(user?.user_type)}>
                  <i className="fas fa-home"></i> Home
                </Link>
              </li>
              {header.breadcrumb.map((crumb, i) => (
                <li
                  key={i}
                  className={`breadcrumb-item ${crumb.to ? "" : "active"}`}
                >
                  {crumb.to ? <Link to={crumb.to}>{crumb.text}</Link> : crumb.text}
                </li>
              ))}
            </ol>
          </nav>
        </div>

        {/* Messages */}
        {messages.length > 0 && (
          <div className="messages-container">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`alert alert-${m.tag} alert-dismissible fade show`}
                role="alert"
              >
                {m.text}
                <button
                  type="button"
                  className="btn-close"
                  aria-label="Close"
                  onClick={() => dismissMessage(m.id)}
                ></button>
              </div>
            ))}
          </div>
        )}

        {/* Main Content Area */}
        <div className="content-area fade-in">
          <Outlet />
        </div>
      </main>
    </LayoutContext.Provider>
  );
}

export default Layout;
