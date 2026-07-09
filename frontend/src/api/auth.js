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
};

export default authAPI;
