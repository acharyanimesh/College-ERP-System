import axiosClient from "./axiosClient";
import toFormData from "./formData";

/** Staff-management endpoints (manage/add/edit staff, subject assignment). */
const staffAPI = {
  getAll() {
    return axiosClient.get("/staff/");
  },

  /** Full details for one staff member (admin staff_details page). */
  get(staffId) {
    return axiosClient.get(`/staff/${staffId}/`);
  },

  /** Create staff (multipart: profile_pic). Fields match StaffForm. */
  create(data) {
    return axiosClient.post("/staff/", toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  update(staffId, data) {
    return axiosClient.put(`/staff/${staffId}/`, toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  delete(staffId) {
    return axiosClient.delete(`/staff/${staffId}/`);
  },

  /** Re-send the verification email for a not-yet-verified staff member. */
  resendVerification(staffId) {
    return axiosClient.post(`/staff/${staffId}/resend-verification/`);
  },

  /** Data for the assign-subjects page (assign_staff_subjects GET). */
  getSubjectAssignments(staffId) {
    return axiosClient.get(`/staff/${staffId}/subject-assignments/`);
  },

  /**
   * Save per-shift assignments (assign_staff_subjects POST):
   * { morning: [courseSubjectIds], day: [courseSubjectIds] }.
   */
  saveSubjectAssignments(staffId, selection) {
    return axiosClient.post(`/staff/${staffId}/subject-assignments/`, selection);
  },

  /**
   * Free teaching slots this staff member holds (Edit Staff page).
   * `cs_id` omitted clears every slot; `shift` omitted clears both shifts.
   * Resolves to { detail, cleared, assignments, subject_count }.
   */
  unassignSubject(staffId, { cs_id, shift } = {}) {
    return axiosClient.post(`/staff/${staffId}/unassign-subject/`, { cs_id, shift });
  },
};

export default staffAPI;
