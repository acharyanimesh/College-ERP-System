import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import bookAPI from "../../api/books";
import { FormCard, Row, TextField, useFormSubmit } from "../../components/forms";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const EMPTY_BOOK = {
  name: "",
  author: "",
  isbn: "",
  category: "",
  total_copies: 1,
};

/** Add/Edit Book — the librarian's catalogue entry (replaces staff AddBook). */
function BookFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Book" : "Add Book";
  usePageHeader({
    title: pageTitle,
    breadcrumb: [{ text: "Catalogue" }, { text: pageTitle }],
  });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { bookId } = useParams();

  const [fields, setFields] = useState(EMPTY_BOOK);

  useEffect(() => {
    if (!edit) return;
    bookAPI
      .get(bookId)
      .then((b) => setFields({ ...EMPTY_BOOK, ...b }))
      .catch(() => addMessage("Could not load the book.", "danger"));
  }, [edit, bookId, addMessage]);

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => (edit ? bookAPI.update(bookId, fields) : bookAPI.add(fields)),
    {
      onSuccess: () => {
        if (edit) {
          addMessage("Book updated successfully.", "success");
          navigate("/librarian/books/");
        } else {
          addMessage("Book is added successfully.", "success");
          setFields(EMPTY_BOOK);
        }
      },
    }
  );

  return (
    <FormCard
      title={pageTitle}
      onSubmit={handleSubmit}
      buttonText={edit ? "Update Book" : "Add Book"}
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <Row>
        <TextField col="col-md-8" label="Book Name" name="name" value={fields.name} onChange={setField} error={errors.name} placeholder="Enter name of the Book" required />
      </Row>
      <Row>
        <TextField col="col-md-8" label="Author Name" name="author" value={fields.author} onChange={setField} error={errors.author} placeholder="Enter name of the Author" required />
      </Row>
      <Row>
        <TextField col="col-md-4" label="ISBN Number" name="isbn" value={fields.isbn} onChange={setField} error={errors.isbn} placeholder="e.g. 9780132350884" maxLength={13} required />
        <TextField col="col-md-4" label="Category" name="category" value={fields.category} onChange={setField} error={errors.category} placeholder="e.g. Software" required />
      </Row>
      <Row>
        <TextField
          col="col-md-4"
          label="Number of Copies"
          name="total_copies"
          type="number"
          min={1}
          value={fields.total_copies}
          onChange={setField}
          error={errors.total_copies}
          help="How many physical copies the library holds. Students can only be approved while a copy is free."
          required
        />
      </Row>
    </FormCard>
  );
}

export default BookFormPage;
