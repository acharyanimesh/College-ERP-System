import { useState } from "react";
import bookAPI from "../../api/books";
import { FormCard, TextField, useFormSubmit } from "../../components/forms";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const EMPTY_BOOK = { name: "", author: "", isbn: "", category: "" };

/** Add Book (staff_template/add_book.html). */
function AddBook() {
  usePageHeader({ title: "Add Book", breadcrumb: [{ text: "Add Book" }] });
  const { addMessage } = useMessages();
  const [fields, setFields] = useState(EMPTY_BOOK);

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => bookAPI.add(fields),
    {
      onSuccess: () => {
        addMessage("Book is added successfully.", "success");
        setFields(EMPTY_BOOK);
      },
    }
  );

  return (
    <FormCard
      title="Add Book"
      onSubmit={handleSubmit}
      buttonText="Add Book"
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <TextField label="Book Name" name="name" value={fields.name} onChange={setField} error={errors.name} placeholder="Enter name of the Book" required />
      <TextField label="Author Name" name="author" value={fields.author} onChange={setField} error={errors.author} placeholder="Enter name of the Author" required />
      <TextField label="ISBN Number" name="isbn" type="number" value={fields.isbn} onChange={setField} error={errors.isbn} placeholder="Enter ISBN number of the book" required />
      <TextField label="Category" name="category" value={fields.category} onChange={setField} error={errors.category} placeholder="Enter Category of the book" required />
    </FormCard>
  );
}

export default AddBook;
