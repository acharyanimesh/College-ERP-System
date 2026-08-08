import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import bookAPI from "../../api/books";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/** Manage Books — the catalogue, with copy counts and what's out. */
function ManageBooks() {
  usePageHeader({
    title: "Manage Books",
    breadcrumb: [{ text: "Catalogue" }, { text: "Manage Books" }],
  });
  const { addMessage } = useMessages();
  const { data: books, reload } = useApi(() => bookAPI.getAll());
  const [query, setQuery] = useState("");

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

  const remove = async (book) => {
    if (!window.confirm(`Remove "${book.name}" from the catalogue?`)) return;
    try {
      await bookAPI.remove(book.id);
      addMessage("Book removed from the catalogue.", "success");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not remove the book.",
        "danger"
      );
    }
  };

  return (
    <ListCard
      title="Manage Books"
      action={
        <Link to="/librarian/books/add/" className="btn btn-sm btn-primary">
          <i className="fas fa-plus"></i> Add Book
        </Link>
      }
      scrollBody
    >
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
            <th>ISBN</th>
            <th>Category</th>
            <th>Copies</th>
            <th>Out</th>
            <th>Available</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {!books?.length && (
            <tr>
              <td colSpan={9} className="text-center">
                No books in the catalogue yet.{" "}
                <Link to="/librarian/books/add/">Add the first one</Link>.
              </td>
            </tr>
          )}
          {books?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={9} className="text-center">
                No books match your search.
              </td>
            </tr>
          )}
          {visible.map((book, i) => (
            <tr key={book.id}>
              <td>{i + 1}</td>
              <td>{book.name}</td>
              <td>{book.author}</td>
              <td>{book.isbn}</td>
              <td>{book.category}</td>
              <td>{book.total_copies}</td>
              <td>{book.copies_out}</td>
              <td>
                <span
                  className={`badge ${
                    book.available_copies ? "badge-success" : "badge-secondary"
                  }`}
                >
                  {book.available_copies}
                </span>
              </td>
              <td className="text-nowrap">
                <Link
                  to={`/librarian/books/edit/${book.id}`}
                  className="btn btn-sm btn-info"
                  title="Edit"
                >
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Remove from catalogue"
                  onClick={() => remove(book)}
                >
                  <i className="fas fa-trash"></i>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default ManageBooks;
