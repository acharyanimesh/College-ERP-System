import bookAPI from "../../api/books";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

/** Library — available books (student_template/view_books.html). */
function ViewBooks() {
  usePageHeader({ title: "Library", breadcrumb: [{ text: "Library" }] });
  const { data: books } = useApi(() => bookAPI.getAll());

  return (
    <ListCard dark title="Available Books">
      <div className="form-group" style={{ color: "red" }}>
        <label>Available books which you can issue from college library !</label>
      </div>
      <div
        className="form-group table"
        style={{ overflowX: "auto", overflowY: "auto", maxHeight: 500 }}
      >
        <table className="table table-bordered" style={{ minWidth: 600 }}>
          <tbody>
            <tr>
              <th>Sr.No</th>
              <th>Book Name</th>
              <th>Author</th>
              <th>ISBN Number</th>
              <th>Category</th>
            </tr>
            {books?.map((book, i) => (
              <tr key={book.id ?? i}>
                <td>{i + 1}.</td>
                <td>{book.name}</td>
                <td>{book.author}</td>
                <td>{book.isbn}</td>
                <td>{book.category}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ListCard>
  );
}

export default ViewBooks;
