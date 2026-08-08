import { useEffect, useRef, useState } from "react";
import authAPI from "../../api/auth";
import profileAPI from "../../api/profile";
import { ListCard } from "../../components/ListCard";
import {
  AvatarField,
  FormCard,
  Row,
  SectionHeading,
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
      <form onSubmit={submit} className="row g-3 align-items-start">
        <div className="col-xl-4 col-md-6">
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
        <div className="col-md-auto">
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
 * Laid out like Add/Edit Student: labelled sections and side-by-side
 * columns rather than one stack of full-width inputs. The card spans the
 * content area (photo panel on the left, fields on the right) while the
 * fields themselves stay in narrow grid columns, so the page reads as full
 * without any single input growing to 400px for a first name.
 */
function ProfilePage() {
  usePageHeader({
    title: "View/Edit Profile",
    breadcrumb: [{ text: "View/Edit Profile" }],
  });
  const { addMessage } = useMessages();
  const [fields, setFields] = useState(EMPTY_PROFILE);
  const [existingPhotoUrl, setExistingPhotoUrl] = useState("");
  const passwordNotified = useRef(false);

  useEffect(() => {
    profileAPI
      .get()
      .then((p) => {
        setFields({ ...EMPTY_PROFILE, ...p, profile_pic: null, password: "" });
        setExistingPhotoUrl(p.profile_pic || "");
      })
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
        <SectionHeading icon="user" title="Personal Information" first />
        <Row>
          <AvatarField
            col="col-lg-3 col-md-4"
            name="profile_pic"
            file={fields.profile_pic}
            existingUrl={existingPhotoUrl}
            onChange={setField}
            error={errors.profile_pic}
            stacked
          />
          <div className="col-lg-9 col-md-8">
            <Row>
              <TextField col="col-xl-4 col-md-6" label="First name" name="first_name" value={fields.first_name} onChange={setField} error={errors.first_name} required />
              <TextField col="col-xl-4 col-md-6" label="Last name" name="last_name" value={fields.last_name} onChange={setField} error={errors.last_name} required />
              <SelectField
                col="col-xl-4 col-md-6"
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
              <TextField
                col="col-xl-5 col-md-6"
                label="Email"
                name="email"
                type="email"
                icon="envelope"
                value={fields.email}
                onChange={setField}
                disabled
                help="Change it in the section below."
              />
              <TextAreaField col="col-xl-7 col-12" label="Address" name="address" rows={3} value={fields.address} onChange={setField} error={errors.address} />
            </Row>
          </div>
        </Row>

        <SectionHeading icon="lock" title="Account Security" />
        <Row>
          <TextField
            col="col-xl-3 col-md-5"
            label="Password"
            name="password"
            type="password"
            icon="lock"
            value={fields.password}
            onChange={setField}
            error={errors.password}
            placeholder="Only if you wish to change it"
          />
          <div className="col-xl-9 col-md-7 d-flex align-items-center">
            <small className="text-muted">
              Leave this blank to keep your current password. Changing it ends
              your session and you'll need to log in again.
            </small>
          </div>
        </Row>
      </FormCard>
      <ChangeEmailCard />
    </>
  );
}

export default ProfilePage;
