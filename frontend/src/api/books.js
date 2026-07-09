import axiosClient from "./axiosClient";

/** Library: staff add/issue books, students browse. */
const bookAPI = {
  getAll() {
    return axiosClient.get("/books/");
  },
  add(data) {
    return axiosClient.post("/books/", data);
  },
  /** Issue a book to a student: { isbn, student } (IssueBookForm). */
  issue(data) {
    return axiosClient.post("/books/issue/", data);
  },
  getIssued() {
    return axiosClient.get("/books/issued/");
  },
};

export default bookAPI;
