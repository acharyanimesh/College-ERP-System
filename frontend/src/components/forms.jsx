import { useEffect, useState } from "react";

/**
 * Form building blocks replicating the Django form pages
 * (form_template.html / add_*_template.html): a card-dark card with the
 * page title, form-groups with labels, and a full-width success button.
 * All inputs carry .form-control like FormSettings added server-side.
 */

/** Card + form shell: <section class="content"> … card card-dark … */
export function FormCard({ title, onSubmit, buttonText = "Submit", nonFieldError, submitting, children }) {
  return (
    <section className="content">
      <div className="container-fluid">
        <div className="row">
          <div className="col-md-12">
            <div className="card card-dark">
              <div className="card-header">
                <h3 className="card-title">{title}</h3>
              </div>
              <form role="form" onSubmit={onSubmit}>
                <div className="card-body">
                  {nonFieldError && (
                    <div className="alert alert-danger">{nonFieldError}</div>
                  )}
                  {children}
                </div>
                <div className="card-footer">
                  <button
                    type="submit"
                    className="btn btn-success btn-block w-100"
                    disabled={submitting}
                  >
                    {buttonText}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/** Row of fields with a comfortable gutter (<div class="row g-3"> around col-md-* fields). */
export function Row({ children }) {
  return <div className="row g-3">{children}</div>;
}

/**
 * Section divider for long forms (Add/Edit Student, Add/Edit Staff): an
 * icon + title with a rule underneath, so a 20-field form reads as a few
 * short, labelled groups instead of one long column.
 */
export function SectionHeading({ icon, title, first = false }) {
  return (
    <div className={`form-section-heading ${first ? "form-section-heading-first" : ""}`}>
      {icon && <i className={`fas fa-${icon} form-section-heading-icon`}></i>}
      <h5>{title}</h5>
    </div>
  );
}

/** Field error text (Django's {{ field.errors }}). */
function FieldError({ error }) {
  if (!error) return null;
  const text = Array.isArray(error) ? error.join(" ") : error;
  return <div className="text-danger small mt-1">{text}</div>;
}

function Group({ col, label, htmlFor, error, help, children }) {
  return (
    <div className={`form-group ${col || ""}`}>
      {label && <label htmlFor={htmlFor}>{label}:</label>}
      {children}
      {help && <small className="form-text text-muted">{help}</small>}
      <FieldError error={error} />
    </div>
  );
}

export function TextField({ label, name, value, onChange, type = "text", col, error, help, icon, ...rest }) {
  const input = (
    <input
      type={type}
      id={`id_${name}`}
      name={name}
      className="form-control"
      value={value ?? ""}
      onChange={(e) => onChange(name, e.target.value)}
      {...rest}
    />
  );
  return (
    <Group col={col} label={label} htmlFor={`id_${name}`} error={error} help={help}>
      {icon ? (
        <div className="input-group">
          <span className="input-group-text">
            <i className={`fas fa-${icon}`}></i>
          </span>
          {input}
        </div>
      ) : (
        input
      )}
    </Group>
  );
}

export function TextAreaField({ label, name, value, onChange, col, error, rows = 3, ...rest }) {
  return (
    <Group col={col} label={label} htmlFor={`id_${name}`} error={error}>
      <textarea
        id={`id_${name}`}
        name={name}
        className="form-control"
        rows={rows}
        value={value ?? ""}
        onChange={(e) => onChange(name, e.target.value)}
        {...rest}
      ></textarea>
    </Group>
  );
}

/** options: [{ value, label }]. */
export function SelectField({ label, name, value, onChange, options, col, error, placeholder, icon, ...rest }) {
  const select = (
    <select
      id={`id_${name}`}
      name={name}
      className="form-control"
      value={value ?? ""}
      onChange={(e) => onChange(name, e.target.value)}
      {...rest}
    >
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
  return (
    <Group col={col} label={label} htmlFor={`id_${name}`} error={error}>
      {icon ? (
        <div className="input-group">
          <span className="input-group-text">
            <i className={`fas fa-${icon}`}></i>
          </span>
          {select}
        </div>
      ) : (
        select
      )}
    </Group>
  );
}

export function CheckboxField({ label, name, checked, onChange, col, error }) {
  return (
    <div className={`form-group ${col || ""}`}>
      <div className="form-check">
        <input
          type="checkbox"
          id={`id_${name}`}
          name={name}
          className="form-check-input"
          checked={!!checked}
          onChange={(e) => onChange(name, e.target.checked)}
        />
        <label className="form-check-label" htmlFor={`id_${name}`}>
          {label}
        </label>
      </div>
      <FieldError error={error} />
    </div>
  );
}

export function FileField({ label, name, onChange, col, error, ...rest }) {
  return (
    <Group col={col} label={label} htmlFor={`id_${name}`} error={error}>
      <input
        type="file"
        id={`id_${name}`}
        name={name}
        className="form-control"
        onChange={(e) => onChange(name, e.target.files[0] || null)}
        {...rest}
      />
    </Group>
  );
}

/**
 * Profile photo picker with a circular preview: shows `existingUrl` (the
 * photo already on file, from the API) until a new `file` is chosen, then
 * previews that instead. Used by Add/Edit Student and Add/Edit Staff in
 * place of a bare <FileField>, which just showed "No file chosen".
 */
export function AvatarField({ label = "Profile photo", name, file, existingUrl, onChange, error }) {
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const shownUrl = previewUrl || existingUrl;

  return (
    <div className="form-group">
      <label>{label}:</label>
      <div className="avatar-upload">
        <div className="avatar-upload-preview">
          {shownUrl ? (
            <img src={shownUrl} alt="" />
          ) : (
            <i className="fas fa-user"></i>
          )}
        </div>
        <div className="avatar-upload-controls">
          <label htmlFor={`id_${name}`} className="btn btn-secondary btn-sm">
            <i className="fas fa-camera"></i> Choose Photo
          </label>
          <input
            type="file"
            id={`id_${name}`}
            name={name}
            accept="image/*"
            className="d-none"
            onChange={(e) => onChange(name, e.target.files[0] || null)}
          />
          {file && (
            <button
              type="button"
              className="btn btn-link btn-sm avatar-upload-clear"
              onClick={() => onChange(name, null)}
            >
              Remove
            </button>
          )}
        </div>
      </div>
      <FieldError error={error} />
    </div>
  );
}

/**
 * Submit handling every converted form page shares: tracks the in-flight
 * state and maps DRF-style error responses ({ field: [msgs], detail,
 * non_field_errors }) onto the form.
 */
export function useFormSubmit(submitFn, { onSuccess } = {}) {
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setSubmitting(true);
    try {
      const result = await submitFn();
      if (onSuccess) onSuccess(result);
    } catch (err) {
      const data = err.response?.data;
      if (data && typeof data === "object") {
        setErrors(data);
      } else {
        setErrors({ non_field_errors: "Could not submit the form. Please try again." });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const nonFieldError = errors.detail || errors.non_field_errors;
  return { submitting, errors, nonFieldError, handleSubmit };
}
