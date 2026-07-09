import axiosClient from "./axiosClient";

/** Feedback: staff/student submit + admin reply. */
const feedbackAPI = {
  /** Own feedback history + submit (staff_feedback / student_feedback). */
  getMine(role) {
    return axiosClient.get(`/feedback/${role}/mine/`);
  },
  submit(role, feedback) {
    return axiosClient.post(`/feedback/${role}/mine/`, { feedback });
  },

  /** Admin view + reply (staff/student_feedback_message). */
  getAll(role) {
    return axiosClient.get(`/feedback/${role}/`);
  },
  reply(role, feedbackId, reply) {
    return axiosClient.post(`/feedback/${role}/${feedbackId}/reply/`, { reply });
  },
};

export default feedbackAPI;
