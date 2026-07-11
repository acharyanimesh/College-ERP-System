import { useState } from "react";
import authAPI from "../../api/auth";
import { useAuth } from "../../context/AuthContext";
import Watermark from "../../layouts/Watermark";
import brandIcon from "../../assets/image/brand-icon.png";

/**
 * First-login gate for Admin/HOD accounts (rendered by App.jsx's
 * ProtectedLayout in place of the normal app chrome whenever
 * user.email_verified is false): the bootstrap account they were given
 * doesn't count as a real inbox, so before they can reach the dashboard
 * they must submit their college/university email and confirm it via the
 * link this sends. See main_app/api/auth.py's request/confirm_admin_email_verification.
 */
function AdminEmailSetup() {
  const { user, logout } = useAuth();
  const [email, setEmail] = useState("");
  const [sentTo, setSentTo] = useState(user?.pending_email || "");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await authAPI.requestAdminEmailVerification(email);
      setSentTo(email);
    } catch (err) {
      const data = err.response?.data;
      setError(data?.email?.[0] || data?.detail || "Could not send the verification email.");
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
          <p className="login-subtitle">One more step</p>
        </div>

        {sentTo ? (
          <div className="text-center">
            <div className="alert alert-success">
              A verification link was sent to <strong>{sentTo}</strong>. Open it
              from that inbox to finish setting up your admin account.
            </div>
            <button
              type="button"
              className="btn btn-outline-primary w-100 mb-2"
              onClick={() => setSentTo("")}
            >
              Use a different email
            </button>
            <button type="button" className="btn btn-link w-100" onClick={logout}>
              Log out
            </button>
          </div>
        ) : (
          <>
            <p className="text-muted text-center">
              Before you continue, confirm your college/university email
              address. We'll send a link there to verify it.
            </p>
            {error && <div className="alert alert-danger text-center">{error}</div>}
            <form onSubmit={submit} className="login-form">
              <div className="form-group">
                <label htmlFor="admin-email" className="form-label">
                  <i className="fas fa-envelope"></i> Institutional Email
                </label>
                <input
                  type="email"
                  id="admin-email"
                  className="form-control"
                  placeholder="you@college.edu"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="form-group">
                <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
                  {submitting ? "Sending..." : "Send Verification Link"}
                </button>
              </div>
            </form>
            <button type="button" className="btn btn-link w-100" onClick={logout}>
              Log out
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default AdminEmailSetup;
