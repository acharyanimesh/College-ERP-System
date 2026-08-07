import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { courseAPI } from "../../../api/academics";
import { FormCard, TextField, useFormSubmit } from "../../../components/forms";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

const EMPTY_COURSE = { name: "", abbreviation: "", code: "", semesters: "" };

/** Add/Edit Course (add/edit_course_template.html + CourseForm). */
function CourseFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Course" : "Add Course";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { courseId } = useParams();

  const [fields, setFields] = useState(EMPTY_COURSE);

  useEffect(() => {
    if (!edit) return;
    courseAPI
      .get(courseId)
      .then((c) => setFields({ ...EMPTY_COURSE, ...c }))
      .catch(() => addMessage("Could not load the course.", "danger"));
  }, [edit, courseId, addMessage]);

  const setField = (name, value) => {
    if (name === "code") value = value.replace(/\D/g, "").slice(0, 2);
    setFields((f) => ({ ...f, [name]: value }));
  };

  // The code is a position in the slot table rather than something that shows
  // up in a roll number verbatim, so spell out the two slots it buys.
  const slotHelp = (() => {
    const code = parseInt(fields.code, 10);
    if (!code || code < 1 || code > 49) {
      return "Position in the roll-number slot table (1-49). Leave blank to take the next free one.";
    }
    const morning = String((code - 1) * 2 + 1).padStart(2, "0");
    const day = String((code - 1) * 2 + 2).padStart(2, "0");
    return `Roll numbers here read YY-${morning}-NN for the morning shift and YY-${day}-NN for the day shift.`;
  })();

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => (edit ? courseAPI.update(courseId, fields) : courseAPI.create(fields)),
    {
      onSuccess: () => {
        addMessage(
          edit ? "Course updated successfully!" : "Course added successfully!",
          "success"
        );
        navigate("/course/manage/");
      },
    }
  );

  return (
    <FormCard
      title={pageTitle}
      onSubmit={handleSubmit}
      buttonText={edit ? "Update Course" : "Add Course"}
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <TextField label="Name" name="name" value={fields.name} onChange={setField} error={errors.name} required />
      <TextField label="Abbreviation" name="abbreviation" value={fields.abbreviation} onChange={setField} error={errors.abbreviation} />
      <TextField
        label="Course Code"
        name="code"
        value={fields.code}
        onChange={setField}
        error={errors.code}
        inputMode="numeric"
        placeholder="e.g. 1"
        maxLength={2}
        help={slotHelp}
      />
      <TextField
        label="Semesters"
        name="semesters"
        type="number"
        min={1}
        value={fields.semesters}
        onChange={setField}
        error={errors.semesters}
      />
    </FormCard>
  );
}

export default CourseFormPage;
