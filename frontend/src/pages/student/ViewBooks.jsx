import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import bookAPI from "../../api/books";
import libraryAPI from "../../api/library";
import { ListCard } from "../../components/ListCard";
import Modal from "../../components/Modal";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/** What the Action column says once the student already has this title open. */
const OWN_STATE = {
  pending: { icon: "fas fa-hourglass-half", className: "badge-warning", text: "Awaiting approval" },
  approved: { icon: "fas fa-check", className: "badge-info", text: "Ready for pickup" },
  issued: { icon: "fas fa-book-reader", className: "badge-success", text: "Borrowed" },
};

/** Library — browse the catalogue and ask to borrow. */
function ViewBooks() {
  usePageHeader({ title: "Library", breadcrumb: [{ text: "Library" }] });
  const { addMessage } = useMessages();
  const { data: books, reload } = useApi(() => bookAPI.getAll());

  const [query, setQuery] = useState("");
  const [target, setTarget] = useState(null); // the book being requested
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const visible = useMemo(() => {
    if (!books) return [];
    const q = query.toLowerCase().trim();
    if (!q) return books;
    return books.filter((b) =>
      [b.name, b.author, b.isbn, b.category].some((field) =>
        String(field || "").toLowerCase().includes(q)
      )
    );
  }, [books, query]);

  const submitRequest = async () => {
    setSubmitting(true);
    try {
      await libraryAPI.request(target.id, note);
      addMessage(
        `Your request for "${target.name}" has been sent to the librarian.`,
        "success"
      );
      setTarget(null);
      setNote("");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not send your request.",
        "danger"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ListCard
      dark
      title="Available Books"
      action={
        <Link to="/student/borrowings/" className="btn btn-sm btn-secondary">
          <i className="fas fa-bookmark"></i> My Borrowings
        </Link>
      }
      scrollBody
    >
      <p className="text-muted">
        Ask the librarian for any book below. You'll be notified once your
        request is approved, then collect the book from the library.
      </p>

      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by title, author, ISBN or category..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <table className="table table-bordered table-hover" style={{ minWidth: 900 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Book Name</th>
            <th>Author</th>
            <th>ISBN Number</th>
            <th>Category</th>
            <th>Availability</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {!books?.length && (
            <tr>
              <td colSpan={7} className="text-center">
                The library catalogue is empty.
              </td>
            </tr>
          )}
          {books?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={7} className="text-center">
                No books match your search.
              </td>
            </tr>
          )}
          {visible.map((book, i) => {
            const own = book.my_request && OWN_STATE[book.my_request.status];
            return (
              <tr key={book.id}>
                <td>{i + 1}.</td>
                <td>{book.name}</td>
                <td>{book.author}</td>
                <td>{book.isbn}</td>
                <td>{book.category}</td>
                <td>
                  <span
                    className={`badge ${
                      book.available_copies ? "badge-success" : "badge-secondary"
                    }`}
                  >
                    {book.available_copies} of {book.total_copies} free
                  </span>
                </td>
                <td className="text-nowrap">
                  {own ? (
                    <span className={`badge ${own.className}`}>
                      <i className={own.icon}></i> {own.text}
                      {book.my_request.due_date &&
                        ` · due ${book.my_request.due_date}`}
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => {
                        setTarget(book);
                        setNote("");
                      }}
                    >
                      <i className="fas fa-hand-paper"></i> Request to borrow
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <Modal
        show={target !== null}
        onClose={() => setTarget(null)}
        header={<h5 className="modal-title">Request to borrow</h5>}
        footer={
          <button
            type="button"
            className="btn btn-success"
            disabled={submitting}
            onClick={submitRequest}
          >
            {submitting ? "Sending..." : "Send request"}
          </button>
        }
      >
        <p>
          Ask the librarian for <strong>{target?.name}</strong> by{" "}
          {target?.author}.
        </p>
        {target?.available_copies === 0 && (
          <div className="alert alert-warning">
            Every copy is currently out. You can still ask — the librarian will
            decide once one comes back.
          </div>
        )}
        <div className="form-group">
          <label htmlFor="request-note">Note for the librarian (optional)</label>
          <textarea
            id="request-note"
            className="form-control"
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. needed for the semester project"
          />
        </div>
      </Modal>
    </ListCard>
  );
}

export default ViewBooks;
