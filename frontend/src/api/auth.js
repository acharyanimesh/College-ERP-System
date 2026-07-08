import axiosClient from "./axiosClient";

/**
 * Auth / session endpoints.
 * Backend endpoints live under main_app/api/ and are mounted at /api/v1/.
 */
const authAPI = {
  /** Log in with email + password. Returns the user profile on success. */
  login(email, password) {
    return axiosClient.post("/auth/login/", { email, password });
  },

  /** Destroy the current session. */
  logout() {
    return axiosClient.post("/auth/logout/");
  },

  /** Fetch the currently logged-in user (used on app load / page refresh). */
  me() {
    return axiosClient.get("/auth/me/");
  },
};

export default authAPI;
