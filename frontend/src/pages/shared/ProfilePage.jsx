import { useEffect, useRef, useState } from "react";
import authAPI from "../../api/auth";
import profileAPI from "../../api/profile";
import { ListCard } from "../../components/ListCard";
import {
  FileField,
  FormCard,
  SelectField,
  TextAreaField,
  TextField,
  useFormSubmit,
} from "../../components/forms";
import { useAuth } from "../../context/AuthContext";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const EMPTY_PROFILE = {
  first_name: "",
  last_name: "",
  email: "",
  gender: "M",
  password: "",
  profile_pic: null,
  address: "",
};

/**
 * Change-email sub-flow shown below the main profile form. Email can't be
 * edited inline (see ProfilePage's disabled email field) because both roles
 * require verification before it takes effect — Admin gets a link sent
 * immediately, Staff/Student's request first needs an admin's approval on
 * the "Email Change Requests" review page (see auth.py's
 * request_admin_email_verification / request_email_change).
 */
function ChangeEmailCard() {
  const { user, refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!user) return null;
  const isAdmin = user.user_type === "1";

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (isAdmin) {
        await authAPI.requestAdminEmailVerification(email);
      } else {
        await authAPI.requestEmailChange(email);
      }
      await refreshUser();
      setEmail("");
    } catch (err) {
      const data = err.response?.data;
      setError(data?.email?.[0] || data?.detail || "Could not submit the request.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ListCard title="Change Email Address">
      {user.pending_email && (
        <div className="alert alert-info">
          {isAdmin || user.pending_email_approved ? (
            <>
              A verification link was sent to <strong>{user.pending_email}</strong>.
              Open it from that inbox to confirm the change.
            </>
          ) : (
            <>
              Your request to change your email to <strong>{user.pending_email}</strong>{" "}
              is awaiting admin approval. A verification link will be sent once it's approved.
            </>
          )}
        </div>
      )}
      <form onSubmit={submit} className="form-row align-items-start">
        <div className="col-auto" style={{ minWidth: 260 }}>
          <input
            type="email"
            className="form-control"
            placeholder="New email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {error && <div className="text-danger small mt-1">{error}</div>}
        </div>
        <div className="col-auto">
          <button type="submit" className="btn btn-secondary" disabled={submitting}>
            {submitting
              ? "Submitting..."
              : user.pending_email
              ? "Use a different email"
              : isAdmin
              ? "Send Verification Link"
              : "Request Email Change"}
          </button>
        </div>
      </form>
    </ListCard>
  );
}

/**
 * View/Edit Profile for the logged-in user (admin_view_profile.html /
 * staff_view_profile.html / student_view_profile.html — all render
 * CustomUserForm through form_template.html). Password is only sent when
 * filled, with the template's "session will end" warning on first change.
 */
function ProfilePage() {
  usePageHeader({
    title: "View/Edit Profile",
    breadcrumb: [{ text: "View/Edit Profile" }],
  });
  const { addMessage } = useMessages();
  const [fields, setFields] = useState(EMPTY_PROFILE);
  const passwordNotified = useRef(false);

  useEffect(() => {
    profileAPI
      .get()
      .then((p) => setFields({ ...EMPTY_PROFILE, ...p, profile_pic: null, password: "" }))
      .catch(() => addMessage("Could not load your profile.", "danger"));
  }, [addMessage]);

  const setField = (name, value) => {
    if (name === "password" && value && !passwordNotified.current) {
      passwordNotified.current = true;
      window.alert(
        "After a successful profile update:\n\nYour session would be terminated\nYou would be required to login again"
      );
    }
    setFields((f) => ({ ...f, [name]: value }));
  };

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => profileAPI.update({ ...fields, password: fields.password || null }),
    {
      onSuccess: () => addMessage("Profile Updated!", "success"),
    }
  );

  return (
    <>
      <FormCard
        title="View/Edit Profile"
        onSubmit={handleSubmit}
        buttonText="Update Profile"
        nonFieldError={nonFieldError}
        submitting={submitting}
      >
        <TextField label="First name" name="first_name" value={fields.first_name} onChange={setField} error={errors.first_name} required />
        <TextField label="Last name" name="last_name" value={fields.last_name} onChange={setField} error={errors.last_name} required />
        <TextField
          label="Email"
          name="email"
          type="email"
          value={fields.email}
          onChange={setField}
          disabled
          help="Use the Change Email Address section below to update this."
        />
        <SelectField
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
        <TextField
          label="Password"
          name="password"
          type="password"
          value={fields.password}
          onChange={setField}
          error={errors.password}
          placeholder="Fill this only if you wish to update password"
        />
        <FileField label="Profile pic" name="profile_pic" onChange={setField} error={errors.profile_pic} accept="image/*" />
        <TextAreaField label="Address" name="address" value={fields.address} onChange={setField} error={errors.address} />
      </FormCard>
      <ChangeEmailCard />
    </>
  );
}

export default ProfilePage;
