import axiosClient from "./axiosClient";
import toFormData from "./formData";

/** Librarian-management endpoints (admin: add/edit/manage librarians). */
const librarianAPI = {
  getAll() {
    return axiosClient.get("/librarians/");
  },

  get(librarianId) {
    return axiosClient.get(`/librarians/${librarianId}/`);
  },

  /** Create a librarian (multipart: profile_pic). Fields match LibrarianForm. */
  create(data) {
    return axiosClient.post("/librarians/", toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  update(librarianId, data) {
    return axiosClient.put(`/librarians/${librarianId}/`, toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  delete(librarianId) {
    return axiosClient.delete(`/librarians/${librarianId}/`);
  },

  /** Re-send the verification email for a not-yet-verified librarian. */
  resendVerification(librarianId) {
    return axiosClient.post(`/librarians/${librarianId}/resend-verification/`);
  },
};

export default librarianAPI;
