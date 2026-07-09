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
};

export default staffAPI;
