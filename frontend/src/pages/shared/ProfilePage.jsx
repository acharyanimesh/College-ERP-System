import { useEffect, useRef, useState } from "react";
import profileAPI from "../../api/profile";
import {
  FileField,
  FormCard,
  SelectField,
  TextAreaField,
  TextField,
  useFormSubmit,
} from "../../components/forms";
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
    <FormCard
      title="View/Edit Profile"
      onSubmit={handleSubmit}
      buttonText="Update Profile"
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <TextField label="First name" name="first_name" value={fields.first_name} onChange={setField} error={errors.first_name} required />
      <TextField label="Last name" name="last_name" value={fields.last_name} onChange={setField} error={errors.last_name} required />
      <TextField label="Email" name="email" type="email" value={fields.email} onChange={setField} error={errors.email} required />
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
  );
}

export default ProfilePage;
