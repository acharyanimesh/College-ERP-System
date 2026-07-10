import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import authAPI from "../../../api/auth";
import staffAPI from "../../../api/staff";
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
  teaches_morning: false,
  teaches_day: false,
  password: "",
};

/**
 * Add/Edit Staff, converted from add_staff_template.html /
 * edit_staff_template.html + StaffForm. Fields are grouped into labelled
 * sections and sized to their content instead of one long column of
 * full-width inputs. Which courses a staff member teaches is derived from
 * their subject assignments (Assign Subjects), not set here.
 */
function StaffFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Staff" : "Add Staff";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { staffId } = useParams();

  const [fields, setFields] = useState(EMPTY_STAFF);
  const [existingPhotoUrl, setExistingPhotoUrl] = useState("");
  const [emailStatus, setEmailStatus] = useState(null);
  const [initialEmail, setInitialEmail] = useState("");

  useEffect(() => {
    if (!edit) return;
    staffAPI
      .get(staffId)
      .then((s) => {
        // courses is read-only (derived from subject assignments), not part
        // of this form's editable fields.
        const { courses: _courses, ...staffData } = s;
        setFields({
          ...EMPTY_STAFF,
          ...staffData,
          profile_pic: null,
          password: "",
        });
        setExistingPhotoUrl(s.profile_pic || "");
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
      <SectionHeading icon="user" title="Personal Information" first />
      <AvatarField
        name="profile_pic"
        file={fields.profile_pic}
        existingUrl={existingPhotoUrl}
        onChange={setField}
        error={errors.profile_pic}
      />
      <Row>
        <TextField col="col-md-6" label="First name" name="first_name" value={fields.first_name} onChange={setField} error={errors.first_name} required />
        <TextField col="col-md-6" label="Last name" name="last_name" value={fields.last_name} onChange={setField} error={errors.last_name} required />
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

      <SectionHeading icon="briefcase" title="Employment Details" />
      <Row>
        <TextField
          col="col-md-4"
          label="Staff id"
          name="staff_id"
          icon="id-card"
          value={fields.staff_id}
          onChange={setField}
          error={errors.staff_id}
          inputMode="numeric"
          placeholder="6-digit ID"
          maxLength={6}
          required
        />
      </Row>
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

export default StaffFormPage;
