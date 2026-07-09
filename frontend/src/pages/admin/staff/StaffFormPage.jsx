import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { courseAPI } from "../../../api/academics";
import authAPI from "../../../api/auth";
import staffAPI from "../../../api/staff";
import {
  FileField,
  FormCard,
  Row,
  SelectField,
  TextField,
  useFormSubmit,
} from "../../../components/forms";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

const EMAIL_RE =
  /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

const EMPTY_STAFF = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  gender: "M",
  staff_id: "",
  phone_number: "",
  email: "",
  address_line1: "",
  address_line2: "",
  city: "",
  province: "",
  profile_pic: null,
  courses: [],
  teaches_morning: false,
  teaches_day: false,
  password: "",
};

/**
 * Add/Edit Staff, converted from add_staff_template.html /
 * edit_staff_template.html + StaffForm. The Select2 course picker becomes a
 * native multi-select (same underlying widget Django rendered).
 */
function StaffFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Staff" : "Add Staff";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { staffId } = useParams();

  const [fields, setFields] = useState(EMPTY_STAFF);
  const [courses, setCourses] = useState([]);
  const [emailStatus, setEmailStatus] = useState(null);
  const [initialEmail, setInitialEmail] = useState("");

  useEffect(() => {
    courseAPI.getAll().then(setCourses).catch(() => {});
  }, []);

  useEffect(() => {
    if (!edit) return;
    staffAPI
      .get(staffId)
      .then((s) => {
        setFields({
          ...EMPTY_STAFF,
          ...s,
          // The API returns courses as objects (Staff Details needs them);
          // the multi-select works on ids.
          courses: (s.courses || []).map((c) => c.id ?? c),
          profile_pic: null,
          password: "",
        });
        setInitialEmail(s.email || "");
      })
      .catch(() => addMessage("Could not load the staff member.", "danger"));
  }, [edit, staffId, addMessage]);

  const setField = (name, value) => {
    if (name === "staff_id") {
      value = value.replace(/\D/g, "").slice(0, 6);
    }
    setFields((f) => ({ ...f, [name]: value }));
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
    () => (edit ? staffAPI.update(staffId, fields) : staffAPI.create(fields)),
    {
      onSuccess: () => {
        addMessage(
          edit ? "Successfully Updated" : "Successfully Added",
          "success"
        );
        navigate("/staff/manage/");
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

  const shiftError = errors.teaches_morning || errors.teaches_day;

  return (
    <FormCard
      title={pageTitle}
      onSubmit={handleSubmit}
      buttonText={edit ? "Update Staff" : "Add Staff"}
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <Row>
        <TextField col="col-md-6" label="First name" name="first_name" value={fields.first_name} onChange={setField} error={errors.first_name} required />
        <TextField col="col-md-6" label="Last name" name="last_name" value={fields.last_name} onChange={setField} error={errors.last_name} required />
      </Row>
      <Row>
        <TextField col="col-md-6" label="Date of birth" name="date_of_birth" type="date" value={fields.date_of_birth} onChange={setField} error={errors.date_of_birth} />
        <SelectField
          col="col-md-6"
          label="Gender"
          name="gender"
          value={fields.gender}
          onChange={setField}
          error={errors.gender}
          options={[
            { value: "M", label: "Male" },
            { value: "F", label: "Female" },
          ]}
        />
      </Row>
      <Row>
        <TextField
          col="col-md-6"
          label="Staff id"
          name="staff_id"
          value={fields.staff_id}
          onChange={setField}
          error={errors.staff_id}
          inputMode="numeric"
          placeholder="6-digit ID"
          maxLength={6}
          required
        />
        <TextField col="col-md-6" label="Phone number" name="phone_number" value={fields.phone_number} onChange={setField} error={errors.phone_number} />
      </Row>
      <TextField label="Email" name="email" type="email" value={fields.email} onChange={setField} error={errors.email} help={emailNote} required />
      <TextField label="Address Line 1" name="address_line1" value={fields.address_line1} onChange={setField} error={errors.address_line1} required />
      <TextField label="Address Line 2" name="address_line2" value={fields.address_line2} onChange={setField} error={errors.address_line2} />
      <Row>
        <TextField col="col-md-6" label="City" name="city" value={fields.city} onChange={setField} error={errors.city} />
        <TextField col="col-md-6" label="Province" name="province" value={fields.province} onChange={setField} error={errors.province} />
      </Row>
      <FileField label="Profile pic" name="profile_pic" onChange={setField} error={errors.profile_pic} accept="image/*" />
      <div className="form-group">
        <label htmlFor="id_courses">Courses:</label>
        <select
          id="id_courses"
          multiple
          className="form-control"
          size={Math.min(Math.max(courses.length, 4), 8)}
          value={fields.courses.map(String)}
          onChange={(e) =>
            setField(
              "courses",
              Array.from(e.target.selectedOptions, (o) => o.value)
            )
          }
        >
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <small className="form-text text-muted">
          Select one or more courses (hold Ctrl/Cmd to multi-select).
        </small>
        {errors.courses && (
          <div className="text-danger small mt-1">
            {Array.isArray(errors.courses) ? errors.courses.join(" ") : errors.courses}
          </div>
        )}
      </div>
      <div className="form-group">
        <label className="d-block">Shift</label>
        <div className="form-check form-check-inline">
          <input
            type="checkbox"
            className="form-check-input"
            id="id_teaches_morning"
            checked={fields.teaches_morning}
            onChange={(e) => setField("teaches_morning", e.target.checked)}
          />
          <label className="form-check-label" htmlFor="id_teaches_morning">
            Morning Shift
          </label>
        </div>
        <div className="form-check form-check-inline">
          <input
            type="checkbox"
            className="form-check-input"
            id="id_teaches_day"
            checked={fields.teaches_day}
            onChange={(e) => setField("teaches_day", e.target.checked)}
          />
          <label className="form-check-label" htmlFor="id_teaches_day">
            Day Shift
          </label>
        </div>
        {shiftError && (
          <div className="text-danger small mt-1">
            {Array.isArray(shiftError) ? shiftError.join(" ") : shiftError}
          </div>
        )}
      </div>
      <TextField
        label="Password"
        name="password"
        type="password"
        value={fields.password}
        onChange={setField}
        error={errors.password}
        placeholder={edit ? "Fill this only if you wish to update password" : undefined}
        required={!edit}
      />
    </FormCard>
  );
}

export default StaffFormPage;
