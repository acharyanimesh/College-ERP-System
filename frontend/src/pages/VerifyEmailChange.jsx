import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import authAPI from "../api/auth";
import Watermark from "../layouts/Watermark";
import brandIcon from "../assets/image/brand-icon.png";

/**
 * Public page reached from the "confirm your new email" link Staff/Student
 * get once an admin approves their request (see ProfilePage.jsx's
 * ChangeEmailCard and the admin Email Change Requests review page). Nothing
 * to fill in — the account already has a password — so this just confirms
 * the token and reports success/failure, like VerifyAdminEmail.jsx does for
 * the Admin-only flow.
 */
function VerifyEmailChange() {
  const { uidb64, token } = useParams();
  const [status, setStatus] = useState("checking"); // checking | done | error
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    authAPI
      .confirmEmailChange(uidb64, token)
      .then(() => {
        if (!cancelled) setStatus("done");
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "This verification link is invalid or has expired."
          );
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [uidb64, token]);

  return (
    <div className="login-container">
      <Watermark />
      <div className="login-card" style={{ animation: "fadeIn 0.6s ease" }}>
        <div className="login-logo">
          <img src={brandIcon} alt="" width={64} height={64} />
          <h1 className="login-title">College ERP</h1>
          <p className="login-subtitle">Confirm new email</p>
        </div>

        {status === "checking" && (
          <p className="text-center text-muted">Verifying your new email…</p>
        )}

        {status === "done" && (
          <div className="text-center">
            <div className="alert alert-success">
              Email confirmed — your account now uses this address to log in.
            </div>
            <a href="/" className="btn btn-primary w-100">
              Continue to Login
            </a>
          </div>
        )}

        {status === "error" && (
          <div className="text-center">
            <div className="alert alert-danger">{error}</div>
            <a href="/" className="btn btn-primary w-100">
              Back to Login
            </a>
          </div>
        )}

        <div className="login-footer text-center mt-4">
          <small className="text-muted">© 2026 College ERP System. All rights reserved.</small>
        </div>
      </div>
    </div>
  );
}

export default VerifyEmailChange;
