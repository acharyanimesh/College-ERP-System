import axiosClient from "./axiosClient";

/**
 * Attendance endpoints (staff Take / Update / View attendance flows).
 * Endpoint methods are added here as the corresponding pages are converted.
 */
const attendanceAPI = {
  /** Students of a class: { subject, course, semester, shift } */
  getStudents(params) {
    return axiosClient.get("/attendance/students/", { params });
  },

  /** Existing attendance dates for a class; pass include_locked for View. */
  getAttendance(params) {
    return axiosClient.get("/attendance/", { params });
  },

  /** Save a new attendance record. */
  save(payload) {
    return axiosClient.post("/attendance/", payload);
  },

  /** Update (and lock) an existing attendance record. */
  update(attendanceId, payload) {
    return axiosClient.put(`/attendance/${attendanceId}/`, payload);
  },
};

export default attendanceAPI;
