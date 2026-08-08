import axiosClient from "./axiosClient";

/**
 * The book catalogue. Anyone signed in may read it; only the librarian may
 * change it. Borrowing lives in api/library.js.
 *
 * A row carries `total_copies` / `available_copies`, and — for a student —
 * `my_request` ({ id, status, status_display, due_date } or null), which is
 * what decides whether the row offers a Request button or reports where their
 * existing one has got to.
 */
const bookAPI = {
  getAll() {
    return axiosClient.get("/books/");
  },

  get(bookId) {
    return axiosClient.get(`/books/${bookId}/`);
  },

  add(data) {
    return axiosClient.post("/books/", data);
  },

  update(bookId, data) {
    return axiosClient.put(`/books/${bookId}/`, data);
  },

  remove(bookId) {
    return axiosClient.delete(`/books/${bookId}/`);
  },
};

export default bookAPI;
