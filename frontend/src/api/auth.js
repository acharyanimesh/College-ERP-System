import axiosClient from "./axiosClient";

/**
 * Auth / session endpoints.
 * Backend endpoints live under main_app/api/ and are mounted at /api/v1/.
 */
const authAPI = {
  /**
   * Log in and return the user profile.
   * credentials: { email, password, remember, captcha } — `captcha` is the
   * g-recaptcha-response token, verified server-side like doLogin does.
   */
  login(credentials) {
    return axiosClient.post("/auth/login/", credentials);
  },

  /** Destroy the current session. */
  logout() {
    return axiosClient.post("/auth/logout/");
  },

  /** Fetch the currently logged-in user (used on app load / page refresh). */
  me() {
    return axiosClient.get("/auth/me/");
  },

  /** Live email-availability check (check_email_availability). */
  checkEmail(email) {
    return axiosClient.post("/auth/check-email/", { email });
  },

  /** Confirm a Staff/Student's emailed verification link and set their first password. */
  verifyEmail(uidb64, token, password) {
    return axiosClient.post(`/auth/verify-email/${uidb64}/${token}/`, { password });
  },

  /** Admin first-login step: submit the institutional email to confirm. */
  requestAdminEmailVerification(email) {
    return axiosClient.post("/auth/admin/request-email-verification/", { email });
  },

  /** Confirm the link emailed by requestAdminEmailVerification. */
  confirmAdminEmailVerification(uidb64, token) {
    return axiosClient.post(`/auth/admin/verify-email/${uidb64}/${token}/`);
  },

  /**
   * Staff/Student profile step: submit a new email address. Unlike the
   * admin flow above, no link is sent yet — it's queued for admin approval.
   */
  requestEmailChange(email) {
    return axiosClient.post("/auth/request-email-change/", { email });
  },

  /** Confirm the link emailed after an admin approves requestEmailChange. */
  confirmEmailChange(uidb64, token) {
    return axiosClient.post(`/auth/verify-email-change/${uidb64}/${token}/`);
  },
};

export default authAPI;
