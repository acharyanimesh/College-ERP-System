import axiosClient from "./axiosClient";

/**
 * Finance-desk endpoints for the accountant: the per-semester fee price list,
 * each student's dues against it, and the payment receipts taken at the
 * counter. Backed by main_app/api/finance.py.
 */
const financeAPI = {
  /** The full price-list grid (every course × semester). */
  getFeeStructures() {
    return axiosClient.get("/finance/fee-structures/");
  },

  /** Upsert amounts: { items: [{ course, semester, amount }] }. */
  saveFeeStructures(items) {
    return axiosClient.post("/finance/fee-structures/", { items });
  },

  /** Active students with term dues; params: { course, semester, status, search }. */
  getStudentFees(params = {}) {
    return axiosClient.get("/finance/student-fees/", { params });
  },

  /** One student's dues + receipt history. */
  getStudentFee(studentId) {
    return axiosClient.get(`/finance/student-fees/${studentId}/`);
  },

  /** Every receipt; params: { course, student, search }. */
  getPayments(params = {}) {
    return axiosClient.get("/finance/payments/", { params });
  },

  /** Record a payment: { student, amount, semester?, method?, note? }. */
  recordPayment(data) {
    return axiosClient.post("/finance/payments/", data);
  },

  /** Read-only view of library fine receipts + outstanding loan fines. */
  getLibraryFines() {
    return axiosClient.get("/finance/library-fines/");
  },
};

export default financeAPI;
