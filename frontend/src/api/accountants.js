import axiosClient from "./axiosClient";
import toFormData from "./formData";

/** Accountant-management endpoints (admin: add/edit/manage accountants). */
const accountantAPI = {
  getAll() {
    return axiosClient.get("/accountants/");
  },

  get(accountantId) {
    return axiosClient.get(`/accountants/${accountantId}/`);
  },

  /** Create an accountant (multipart: profile_pic). Fields match AccountantForm. */
  create(data) {
    return axiosClient.post("/accountants/", toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  update(accountantId, data) {
    return axiosClient.put(`/accountants/${accountantId}/`, toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  delete(accountantId) {
    return axiosClient.delete(`/accountants/${accountantId}/`);
  },

  /** Re-send the verification email for a not-yet-verified accountant. */
  resendVerification(accountantId) {
    return axiosClient.post(`/accountants/${accountantId}/resend-verification/`);
  },
};

export default accountantAPI;
