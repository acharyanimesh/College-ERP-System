import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import authAPI from "../api/auth";
import Watermark from "../layouts/Watermark";
import brandIcon from "../assets/image/brand-icon.png";

/**
 * Public page reached from the "verify your account" email. Lets a newly
 * created Staff/Student confirm their address and set their first password.
 * Styled like Login.jsx since it's shown to logged-out visitors.
 */
function VerifyEmail() {
  const { uidb64, token } = useParams();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [passwordErrors, setPasswordErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setPasswordErrors([]);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await authAPI.verifyEmail(uidb64, token, password);
      setDone(true);
    } catch (err) {
      const data = err.response?.data;
      if (data?.password) {
        setPasswordErrors(Array.isArray(data.password) ? data.password : [data.password]);
      } else {
        setError(data?.detail || "This verification link is invalid or has expired.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-container">
      <Watermark />
      <div className="login-card" style={{ animation: "fadeIn 0.6s ease" }}>
        <div className="login-logo">
          <img src={brandIcon} alt="" width={64} height={64} />
          <h1 className="login-title">College ERP</h1>
          <p className="login-subtitle">Verify your account</p>
        </div>

        {done ? (
          <div className="text-center">
            <div className="alert alert-success">
              Email verified — your account is now active.
            </div>
            <Link to="/" className="btn btn-primary w-100">
              Go to Login
            </Link>
          </div>
        ) : (
          <>
            {error && <div className="alert alert-danger text-center">{error}</div>}

            <form onSubmit={handleSubmit} className="login-form">
              <div className="form-group">
                <label htmlFor="password" className="form-label">
                  <i className="fas fa-lock"></i> New Password
                </label>
                <input
                  type="password"
                  id="password"
                  className="form-control"
                  placeholder="Choose a password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {passwordErrors.map((msg, i) => (
                  <div className="text-danger small mt-1" key={i}>
                    {msg}
                  </div>
                ))}
              </div>

              <div className="form-group">
                <label htmlFor="confirmPassword" className="form-label">
                  <i className="fas fa-lock"></i> Confirm Password
                </label>
                <input
                  type="password"
                  id="confirmPassword"
                  className="form-control"
                  placeholder="Re-enter the password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              <div className="form-group">
                <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
                  {submitting ? "Verifying..." : "Set Password & Verify"}
                </button>
              </div>
            </form>
          </>
        )}

        <div className="login-footer text-center mt-4">
          <small className="text-muted">© 2026 College ERP System. All rights reserved.</small>
        </div>
      </div>
    </div>
  );
}

export default VerifyEmail;
