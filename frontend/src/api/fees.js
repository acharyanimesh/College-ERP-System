import axiosClient from "./axiosClient";
import toFormData from "./formData";

/**
 * Fee endpoints (main_app/api/fees.py).
 *
 * Reads are open to the accountant and, for oversight, the admin; every
 * write is accountant-only and the server is what enforces that.
 */
const feeAPI = {
  // ---- Fee heads: the college's chart of fees
  getHeads() {
    return axiosClient.get("/fees/heads/");
  },

  createHead(data) {
    return axiosClient.post("/fees/heads/", data);
  },

  updateHead(headId, data) {
    return axiosClient.put(`/fees/heads/${headId}/`, data);
  },

  deleteHead(headId) {
    return axiosClient.delete(`/fees/heads/${headId}/`);
  },

  // ---- Fee structures: what a (course, session, semester) costs
  getStructures(params) {
    return axiosClient.get("/fees/structures/", { params });
  },

  getStructure(structureId) {
    return axiosClient.get(`/fees/structures/${structureId}/`);
  },

  /** `items` is [{ head, amount }] and REPLACES whatever the structure had. */
  createStructure(data) {
    return axiosClient.post("/fees/structures/", data);
  },

  updateStructure(structureId, data) {
    return axiosClient.put(`/fees/structures/${structureId}/`, data);
  },

  deleteStructure(structureId) {
    return axiosClient.delete(`/fees/structures/${structureId}/`);
  },

  /** Copy a structure onto another session (and optionally another semester). */
  cloneStructure(structureId, data) {
    return axiosClient.post(`/fees/structures/${structureId}/clone/`, data);
  },

  // ---- The invoice run
  /** What billing this class would do, without doing it. */
  previewRun(params) {
    return axiosClient.get("/fees/invoice-run/preview/", { params });
  },

  /** Raise the bills. Safe to call twice — nobody is billed a second time. */
  run(data) {
    return axiosClient.post("/fees/invoice-run/", data);
  },

  // ---- The invoice register
  getInvoices(params) {
    return axiosClient.get("/fees/invoices/", { params });
  },

  getInvoice(invoiceId) {
    return axiosClient.get(`/fees/invoices/${invoiceId}/`);
  },

  cancelInvoice(invoiceId, reason) {
    return axiosClient.post(`/fees/invoices/${invoiceId}/cancel/`, { reason });
  },

  /**
   * Scholarship / discount / waiver / late fine / correction. Send a plain
   * positive `amount` — the `kind` is what decides whether it adds to the
   * bill or takes away. Append-only, so this can never be undone, only
   * offset by another one.
   */
  adjustInvoice(invoiceId, data) {
    return axiosClient.post(`/fees/invoices/${invoiceId}/adjust/`, data);
  },

  // ---- The student's own view. All scoped to the caller server-side.
  /** { outstanding_total, overdue_total, next_due_date, invoices: [...] } */
  mine() {
    return axiosClient.get("/fees/mine/");
  },

  /** One of the caller's own bills, itemised. Somebody else's is a 404. */
  myInvoice(invoiceId) {
    return axiosClient.get(`/fees/mine/${invoiceId}/`);
  },

  myReceipts() {
    return axiosClient.get("/fees/mine/receipts/");
  },

  // ---- The counter
  /** Outstanding bills, searchable by roll number, name or invoice number. */
  collectable(params) {
    return axiosClient.get("/fees/collectable/", { params });
  },

  /**
   * Record money taken at the counter. `mode` is cash / cheque / bank —
   * "online" is refused here, since an online payment only exists because a
   * gateway confirmed it. Returns { payment, invoice }.
   */
  collect(invoiceId, data) {
    return axiosClient.post(`/fees/invoices/${invoiceId}/collect/`, data);
  },

  /** The office cash book: { payments: [...], total }. */
  getPayments(params) {
    return axiosClient.get("/fees/payments/", { params });
  },

  /** One receipt — readable by the office, or by the student it belongs to. */
  getReceipt(paymentId) {
    return axiosClient.get(`/fees/payments/${paymentId}/receipt/`);
  },

  // ---- Bank deposit slips
  /** Every slip this student has submitted, verified or not. */
  mySlips() {
    return axiosClient.get("/fees/mine/slips/");
  },

  /**
   * Claim to have paid a bill into the college's bank (multipart: image).
   * Nothing is credited by this — the office has to verify it first.
   */
  submitSlip(invoiceId, data) {
    return axiosClient.post(`/fees/mine/${invoiceId}/slips/`, toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** Take back a slip the office hasn't looked at yet. */
  withdrawSlip(slipId) {
    return axiosClient.delete(`/fees/mine/slips/${slipId}/`);
  },

  /** The office's work queue: { slips: [...], pending_count }. */
  getSlips(params) {
    return axiosClient.get("/fees/slips/", { params });
  },

  /**
   * Agree the money is in the bank; writes the receipt. `amount` overrides
   * what the student claimed, for when the statement says otherwise.
   */
  verifySlip(slipId, data) {
    return axiosClient.post(`/fees/slips/${slipId}/verify/`, data);
  },

  /** Turn a claim down. The reason is required and goes to the student. */
  rejectSlip(slipId, reason) {
    return axiosClient.post(`/fees/slips/${slipId}/reject/`, { reason });
  },
};

export default feeAPI;
