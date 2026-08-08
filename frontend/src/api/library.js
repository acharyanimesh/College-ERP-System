import axiosClient from "./axiosClient";

/**
 * Borrowing: the student's side (request / cancel / track) and the
 * librarian's side (queue, decisions, loans).
 *
 * A request moves pending → approved → issued → returned, with rejected and
 * cancelled as the two dead ends. Every response is one request object with
 * the same shape, so callers can just replace the row they acted on.
 */
const libraryAPI = {
  /* -- student -- */

  /** Own requests and loans, newest first. */
  mine() {
    return axiosClient.get("/library/requests/mine/");
  },

  /** Ask to borrow: { book: bookId, note? }. */
  request(bookId, note = "") {
    return axiosClient.post("/library/requests/mine/", { book: bookId, note });
  },

  /** Withdraw a request the librarian hasn't decided on yet. */
  cancel(requestId) {
    return axiosClient.post(`/library/requests/${requestId}/cancel/`);
  },

  /** Ask to keep a borrowed book one more week. Allowed once per loan. */
  requestRenewal(requestId, reason = "") {
    return axiosClient.post(`/library/requests/${requestId}/renew/`, { reason });
  },

  /** Own fine receipts — the student's copy of the cash record. */
  myFines() {
    return axiosClient.get("/library/fines/mine/");
  },

  /* -- librarian -- */

  /** The queue. `status` filters to one state, `q` searches book/student. */
  getRequests({ status, q } = {}) {
    return axiosClient.get("/library/requests/", { params: { status, q } });
  },

  /** Books currently out, most overdue first. */
  getLoans() {
    return axiosClient.get("/library/loans/");
  },

  /** Allow the borrowing; reserves a copy for pickup. */
  approve(requestId, note = "") {
    return axiosClient.post(`/library/requests/${requestId}/approve/`, { note });
  },

  /** Turn it down. A reason is required — the student is told it. */
  reject(requestId, reason) {
    return axiosClient.post(`/library/requests/${requestId}/reject/`, { reason });
  },

  /** The student collected the book; the 14-day clock starts here. */
  issue(requestId) {
    return axiosClient.post(`/library/requests/${requestId}/issue/`);
  },

  /** Book is back; whatever fine had accrued is frozen. */
  markReturned(requestId) {
    return axiosClient.post(`/library/requests/${requestId}/return/`);
  },

  /** Grant the extension: due date moves out by a week. */
  approveRenewal(requestId, note = "") {
    return axiosClient.post(`/library/requests/${requestId}/renew/approve/`, { note });
  },

  /** Decline it; the original due date stands. A reason is required. */
  rejectRenewal(requestId, reason) {
    return axiosClient.post(`/library/requests/${requestId}/renew/reject/`, { reason });
  },

  /* -- fines: cash at the desk, recorded once and never edited -- */

  /** The cash book: every receipt, plus collected/waived totals. */
  getFines(q = "") {
    return axiosClient.get("/library/fines/", { params: { q } });
  },

  /** Late returns that haven't been settled yet. */
  getUnsettledFines() {
    return axiosClient.get("/library/fines/unsettled/");
  },

  /** Record cash taken over the counter; writes a permanent receipt. */
  collectFine(requestId, note = "") {
    return axiosClient.post(`/library/requests/${requestId}/fine/collect/`, { note });
  },

  /** Write the fine off. Still a receipt, and the reason is required. */
  waiveFine(requestId, note) {
    return axiosClient.post(`/library/requests/${requestId}/fine/waive/`, { note });
  },

  /** Run the due-soon sweep by hand (same code as the scheduled command). */
  sendReminders() {
    return axiosClient.post("/library/reminders/send/");
  },
};

export default libraryAPI;
