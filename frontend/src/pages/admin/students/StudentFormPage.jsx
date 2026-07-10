import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { courseAPI, sessionAPI } from "../../../api/academics";
import authAPI from "../../../api/auth";
import studentAPI from "../../../api/students";
import { NEPAL_PROVINCES } from "../../../constants/nepal";
import {
  AvatarField,
  FormCard,
  Row,
  SectionHeading,
  SelectField,
  TextField,
  useFormSubmit,
} from "../../../components/forms";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

const EMAIL_RE =
  /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

const EMPTY_STUDENT = {
  first_name: "",
  middle_name: "",
  last_name: "",
  date_of_birth: "",
  gender: "M",
  registration_number: "",
  roll_number: "",
  phone_number: "",
  email: "",
  address_line1: "",
  address_line2: "",
  city: "",
  province: "",
  profile_pic: null,
  course: "",
  session: "",
  shift: "morning",
  current_semester: 1,
  parent_full_name: "",
  parent_phone_number: "",
  parent_relationship: "Father",
  password: "",
};

/**
 * Add/Edit Student, converted from add_student_template.html /
 * edit_student_template.html + StudentForm in forms.py — same field layout,
 * live registration/roll number formatting and the email-availability
 * check from the template's custom_js. Fields are grouped into labelled
 * sections and sized to their content (short fields stay short) instead of
 * one long column of full-width inputs.
 */
function StudentFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Student" : "Add Student";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { studentId } = useParams();

  const [fields, setFields] = useState(EMPTY_STUDENT);
  const [existingPhotoUrl, setExistingPhotoUrl] = useState("");
  const [courses, setCourses] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [emailStatus, setEmailStatus] = useState(null); // 'taken' | 'available'
  const [initialEmail, setInitialEmail] = useState("");

  useEffect(() => {
    courseAPI.getAll().then(setCourses).catch(() => {});
    sessionAPI.getAll().then(setSessions).catch(() => {});
  }, []);

  useEffect(() => {
    if (!edit) return;
    studentAPI
      .get(studentId)
      .then((s) => {
        setFields({ ...EMPTY_STUDENT, ...s, profile_pic: null, password: "" });
        setExistingPhotoUrl(s.profile_pic || "");
        setInitialEmail(s.email || "");
      })
      .catch(() => addMessage("Could not load the student.", "danger"));
  }, [edit, studentId, addMessage]);

  const setField = (name, value) => {
    if (name === "registration_number") {
      // 12 digits, auto-grouped as XXXX-XXXX-XXXX (template custom_js).
      const digits = value.replace(/\D/g, "").slice(0, 12);
      value = digits.replace(/(\d{4})(?=\d)/g, "$1-");
    }
    if (name === "roll_number") {
      value = value.replace(/\D/g, "").slice(0, 6);
    }
    setFields((f) => ({ ...f, [name]: value }));

    // Live email-availability check (check_email_availability endpoint).
    if (name === "email") {
      setEmailStatus(null);
      if (EMAIL_RE.test(String(value).toLowerCase()) && value !== initialEmail) {
        authAPI
          .checkEmail(value)
          .then((res) => setEmailStatus(res.exists ? "taken" : "available"))
          .catch(() => {});
      }
    }
  };

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () =>
      edit ? studentAPI.update(studentId, fields) : studentAPI.create(fields),
    {
      onSuccess: () => {
        addMessage(
          edit ? "Successfully Updated" : "Successfully Added",
          "success"
        );
        navigate("/student/manage/");
      },
    }
  );

  const emailNote =
    emailStatus === "taken" ? (
      <span style={{ fontStyle: "italic", fontWeight: "bold", color: "red" }}>
        Email Address Already Exist
      </span>
    ) : emailStatus === "available" ? (
      <span style={{ fontStyle: "italic", fontWeight: "bold", color: "green" }}>
        Email Address Available
      </span>
    ) : null;

  return (
    <FormCard
      title={pageTitle}
      onSubmit={handleSubmit}
      buttonText={edit ? "Update Student" : "Add Student"}
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <SectionHeading icon="user" title="Personal Information" first />
      <AvatarField
        name="profile_pic"
        file={fields.profile_pic}
        existingUrl={existingPhotoUrl}
        onChange={setField}
        error={errors.profile_pic}
      />
      <Row>
        <TextField col="col-md-4" label="First name" name="first_name" value={fields.first_name} onChange={setField} error={errors.first_name} required />
        <TextField col="col-md-4" label="Middle name" name="middle_name" value={fields.middle_name} onChange={setField} error={errors.middle_name} />
        <TextField col="col-md-4" label="Last name" name="last_name" value={fields.last_name} onChange={setField} error={errors.last_name} required />
      </Row>
      <Row>
        <TextField col="col-md-4" label="Date of birth" name="date_of_birth" type="date" icon="calendar-alt" value={fields.date_of_birth} onChange={setField} error={errors.date_of_birth} />
        <SelectField
          col="col-md-4"
          label="Gender"
          name="gender"
          icon="venus-mars"
          value={fields.gender}
          onChange={setField}
          error={errors.gender}
          options={[
            { value: "M", label: "Male" },
            { value: "F", label: "Female" },
          ]}
        />
        <TextField col="col-md-4" label="Phone number" name="phone_number" icon="phone" placeholder="98XXXXXXXX" maxLength={14} value={fields.phone_number} onChange={setField} error={errors.phone_number} />
      </Row>
      <Row>
        <TextField col="col-md-6" label="Email" name="email" type="email" icon="envelope" value={fields.email} onChange={setField} error={errors.email} help={emailNote} required />
      </Row>

      <SectionHeading icon="map-marker-alt" title="Address" />
      <Row>
        <TextField col="col-md-6" label="Address Line 1" name="address_line1" value={fields.address_line1} onChange={setField} error={errors.address_line1} required />
        <TextField col="col-md-6" label="Address Line 2" name="address_line2" value={fields.address_line2} onChange={setField} error={errors.address_line2} />
      </Row>
      <Row>
        <TextField col="col-md-6" label="City" name="city" value={fields.city} onChange={setField} error={errors.city} />
        <SelectField
          col="col-md-6"
          label="Province"
          name="province"
          icon="map-marker-alt"
          value={fields.province}
          onChange={setField}
          error={errors.province}
          options={NEPAL_PROVINCES.map((p) => ({ value: p, label: p }))}
          placeholder="Select province"
        />
      </Row>

      <SectionHeading icon="graduation-cap" title="Academic Details" />
      <Row>
        <TextField
          col="col-md-4"
          label="Registration Number"
          name="registration_number"
          icon="id-card"
          value={fields.registration_number}
          onChange={setField}
          error={errors.registration_number}
          inputMode="numeric"
          placeholder="XXXX-XXXX-XXXX"
          maxLength={14}
          required
        />
        <TextField
          col="col-md-4"
          label="Roll Number"
          name="roll_number"
          icon="hashtag"
          value={fields.roll_number}
          onChange={setField}
          error={errors.roll_number}
          inputMode="numeric"
          placeholder="6-digit roll number"
          maxLength={6}
          required
        />
        <TextField
          col="col-md-4"
          label="Current Semester"
          name="current_semester"
          type="number"
          min={1}
          step={1}
          value={fields.current_semester}
          onChange={setField}
          error={errors.current_semester}
          help="New students start at 1."
        />
      </Row>
      <Row>
        <SelectField
          col="col-md-6"
          label="Course"
          name="course"
          value={fields.course}
          onChange={setField}
          error={errors.course}
          options={courses.map((c) => ({ value: c.id, label: c.name }))}
          placeholder="---------"
          required
        />
        <SelectField
          col="col-md-6"
          label="Session"
          name="session"
          value={fields.session}
          onChange={setField}
          error={errors.session}
          options={sessions.map((s) => ({
            value: s.id,
            label: `From ${s.start_year} to ${s.end_year}`,
          }))}
          placeholder="---------"
          required
        />
      </Row>
      <Row>
        <SelectField
          col="col-md-6"
          label="Shift"
          name="shift"
          value={fields.shift}
          onChange={setField}
          error={errors.shift}
          options={[
            { value: "morning", label: "Morning Shift" },
            { value: "day", label: "Day Shift" },
          ]}
        />
      </Row>

      <SectionHeading icon="users" title="Parent Information" />
      <Row>
        <TextField
          col="col-md-4"
          label="Parent full name"
          name="parent_full_name"
          icon="user"
          value={fields.parent_full_name}
          onChange={setField}
          error={errors.parent_full_name}
          required
        />
        <TextField
          col="col-md-4"
          label="Parent phone number"
          name="parent_phone_number"
          icon="phone"
          maxLength={10}
          value={fields.parent_phone_number}
          onChange={setField}
          error={errors.parent_phone_number}
          required
        />
        <SelectField
          col="col-md-4"
          label="Relationship with student"
          name="parent_relationship"
          value={fields.parent_relationship}
          onChange={setField}
          error={errors.parent_relationship}
          options={[
            { value: "Father", label: "Father" },
            { value: "Mother", label: "Mother" },
            { value: "Guardian", label: "Guardian" },
            { value: "Other", label: "Other" },
          ]}
          required
        />
      </Row>

      <SectionHeading icon="lock" title="Account Security" />
      <Row>
        <TextField
          col="col-md-6"
          label="Password"
          name="password"
          type="password"
          icon="lock"
          value={fields.password}
          onChange={setField}
          error={errors.password}
          placeholder={edit ? "Fill this only if you wish to update password" : undefined}
          required={!edit}
        />
      </Row>
    </FormCard>
  );
}

export default StudentFormPage;
