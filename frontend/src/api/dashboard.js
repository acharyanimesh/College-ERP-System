import axiosClient from "./axiosClient";

/**
 * Dashboard statistics endpoints. Each returns the same fields the matching
 * Django view passed as template context (snake_case names kept identical),
 * e.g. admin_home in hod_views.py → adminHome().
 */
const dashboardAPI = {
  /** Admin dashboard counters + chart series (hod_views.admin_home). */
  adminHome() {
    return axiosClient.get("/dashboard/admin/");
  },
};

export default dashboardAPI;
