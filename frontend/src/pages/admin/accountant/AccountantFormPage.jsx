import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import authAPI from "../../../api/auth";
import accountantAPI from "../../../api/accountants";
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

const EMPTY_ACCOUNTANT = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  gender: "M",
  accountant_id: "",
  phone_number: "",
  email: "",
  address_line1: "",
  address_line2: "",
  city: "",
  province: "",
  profile_pic: null,
  password: "",
};

/**
 * Add/Edit Accountant. Same shape as LibrarianFormPage — an accountant, like
 * a librarian, has no shift and no subjects.
 */
function AccountantFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Accountant" : "Add Accountant";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { accountantId } = useParams();

  const [fields, setFields] = useState(EMPTY_ACCOUNTANT);
  const [existingPhotoUrl, setExistingPhotoUrl] = useState("");
  const [emailStatus, setEmailStatus] = useState(null);
  const [initialEmail, setInitialEmail] = useState("");

  useEffect(() => {
    if (!edit) return;
    accountantAPI
      .get(accountantId)
      .then((a) => {
        setFields({ ...EMPTY_ACCOUNTANT, ...a, profile_pic: null, password: "" });
        setExistingPhotoUrl(a.profile_pic || "");
        setInitialEmail(a.email || "");
      })
      .catch(() => addMessage("Could not load the accountant.", "danger"));
  }, [edit, accountantId, addMessage]);

  const setField = (name, value) => {
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
    () =>
      edit
        ? accountantAPI.update(accountantId, fields)
        : accountantAPI.create(fields),
    {
      onSuccess: () => {
        addMessage(edit ? "Successfully Updated" : "Successfully Added", "success");
        navigate("/accountant/manage/");
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
      buttonText={edit ? "Update Accountant" : "Add Accountant"}
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
        {/* Issued by the server on creation and fixed from then on — and drawn
            from the same counter as staff and librarian IDs, so one number
            means one employee whichever role they hold. */}
        <TextField
          col="col-md-4"
          label="Accountant id"
          name="accountant_id"
          icon="id-card"
          value={fields.accountant_id}
          onChange={setField}
          placeholder="Assigned on save"
          help={
            edit
              ? "Issued when this account was created; it does not change."
              : "Assigned automatically — joining year plus a serial, e.g. 260001."
          }
          disabled
        />
      </Row>

      <SectionHeading icon="lock" title="Account Security" />
      {edit ? (
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
            placeholder="Fill this only if you wish to update password"
          />
        </Row>
      ) : (
        <p className="text-muted">
          A verification email will be sent to the address above; the accountant
          sets their own password by following the link in it.
        </p>
      )}
    </FormCard>
  );
}

export default AccountantFormPage;
