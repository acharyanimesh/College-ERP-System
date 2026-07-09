import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { homePath } from "../layouts/Navbar";

const RECAPTCHA_SITE_KEY = "6LfTGD4qAAAAAJLKy1TGJY7uuTh_T1cB5VikRWjF";

// Django keeps serving the password-reset flow during the migration; link to
// it on the backend origin (VITE_API_URL is `<backend>/api/v1`).
const BACKEND_ORIGIN = new URL(import.meta.env.VITE_API_URL, window.location.origin).origin;

/** Load Google reCAPTCHA once and render the widget into `container`. */
function useRecaptcha(container) {
  const widgetIdRef = useRef(null);

  useEffect(() => {
    const el = container.current;
    if (!el) return undefined;

    const renderWidget = () => {
      if (window.grecaptcha?.render && el.childNodes.length === 0) {
        widgetIdRef.current = window.grecaptcha.render(el, {
          sitekey: RECAPTCHA_SITE_KEY,
          theme: "dark",
        });
      }
    };

    if (window.grecaptcha?.render) {
      renderWidget();
    } else {
      window.onRecaptchaLoad = renderWidget;
      if (!document.querySelector('script[src*="recaptcha/api.js"]')) {
        const script = document.createElement("script");
        script.src =
          "https://www.google.com/recaptcha/api.js?onload=onRecaptchaLoad&render=explicit";
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
      }
    }

    return () => {
      // The widget can't be re-rendered into a used container; reset it for
      // the next mount (also covers StrictMode's double mount in dev).
      el.innerHTML = "";
      widgetIdRef.current = null;
    };
  }, [container]);

  return {
    getToken: () =>
      window.grecaptcha && widgetIdRef.current !== null
        ? window.grecaptcha.getResponse(widgetIdRef.current)
        : "",
    reset: () => {
      if (window.grecaptcha && widgetIdRef.current !== null) {
        window.grecaptcha.reset(widgetIdRef.current);
      }
    },
  };
}

/**
 * Login screen replicating templates/main_app/login.html: Vanta DOTS
 * background, glass card, reCAPTCHA, remember-me and the little hover/focus
 * effects from the template's inline scripts.
 */
function Login() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(
    () => localStorage.getItem("rememberMe") === "true"
  );
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const recaptchaRef = useRef(null);
  const recaptcha = useRecaptcha(recaptchaRef);

  const handleRememberChange = (e) => {
    setRemember(e.target.checked);
    localStorage.setItem("rememberMe", String(e.target.checked));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const profile = await login({
        email,
        password,
        remember,
        captcha: recaptcha.getToken(),
      });
      navigate(homePath(profile.user_type), { replace: true });
    } catch (err) {
      // Same wording as doLogin's messages.error fallbacks.
      setError(err.response?.data?.detail || "Invalid details");
      recaptcha.reset();
      setSubmitting(false);
    }
  };

  /* --- Inline-script effects from login.html, as React handlers --- */
  const focusGrow = (e) => {
    e.target.style.transform = "scale(1.02)";
    e.target.style.transition = "transform 0.2s ease";
  };
  const focusShrink = (e) => {
    e.target.style.transform = "scale(1)";
  };
  const btnHoverOn = (e) => {
    e.currentTarget.style.transform = "translateY(-2px)";
    e.currentTarget.style.boxShadow = "0 4px 12px rgba(255, 136, 32, 0.45)";
  };
  const btnHoverOff = (e) => {
    e.currentTarget.style.transform = "translateY(0)";
    e.currentTarget.style.boxShadow = "none";
  };

  // Mirrors login_page in views.py: already authenticated users go home.
  if (loading) return null;
  if (user) return <Navigate to={homePath(user.user_type)} replace />;

  return (
    <div className="login-container">
      <div className="login-card" style={{ animation: "fadeIn 0.6s ease" }}>
        <div className="login-logo">
          <h1 className="login-title">College ERP</h1>
          <p className="login-subtitle">Education Management System</p>
        </div>

        {/* Error Messages */}
        {error && <div className="alert alert-danger text-center">{error}</div>}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email" className="form-label">
              <i className="fas fa-envelope"></i> Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              className="form-control"
              placeholder="Enter your email address"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onFocus={focusGrow}
              onBlur={focusShrink}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">
              <i className="fas fa-lock"></i> Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              className="form-control"
              placeholder="Enter your password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={focusGrow}
              onBlur={focusShrink}
            />
          </div>

          {/* reCAPTCHA */}
          <div className="form-group text-center">
            <div className="g-recaptcha" ref={recaptchaRef}></div>
          </div>

          <div className="form-group">
            <div className="form-check">
              <input
                type="checkbox"
                className="form-check-input"
                id="remember"
                name="remember"
                value="1"
                checked={remember}
                onChange={handleRememberChange}
                title="Keep me logged in for 30 days"
              />
              <label className="form-check-label" htmlFor="remember">
                Remember me
              </label>
            </div>
          </div>

          <div className="form-group">
            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={submitting}
              onMouseEnter={btnHoverOn}
              onMouseLeave={btnHoverOff}
            >
              <i className="fas fa-sign-in-alt"></i>{" "}
              {submitting ? "Signing In..." : "Sign In"}
            </button>
          </div>

          <div className="text-center">
            <a
              href={`${BACKEND_ORIGIN}/accounts/password_reset/`}
              className="text-decoration-none"
            >
              Forgot your password?
            </a>
          </div>
        </form>

        {/* Footer */}
        <div className="login-footer text-center mt-4">
          <small className="text-muted">
            © 2026 College ERP System. All rights reserved.
          </small>
        </div>
      </div>
    </div>
  );
}

export default Login;
