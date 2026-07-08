import axios from "axios";

/**
 * Global axios instance for every API call in the app.
 *
 * - Base URL comes from the environment (.env.development / .env.production),
 *   so components never hardcode server addresses.
 * - The Django backend uses session-cookie authentication, so
 *   `withCredentials` sends the sessionid/csrftoken cookies with each request.
 * - Django's CSRF protection requires the `X-CSRFToken` header on unsafe
 *   methods (POST/PUT/PATCH/DELETE); the request interceptor reads the token
 *   from the `csrftoken` cookie automatically.
 */
const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

/** Read a cookie value by name (used for Django's csrftoken cookie). */
function getCookie(name) {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
}

// Attach the CSRF token to every mutating request.
axiosClient.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const token = getCookie("csrftoken");
    if (token) {
      config.headers["X-CSRFToken"] = token;
    }
  }
  return config;
});

// Normalize responses/errors in one place.
axiosClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Session expired or not logged in — let the app react in one place.
      window.dispatchEvent(new CustomEvent("api:unauthorized"));
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
