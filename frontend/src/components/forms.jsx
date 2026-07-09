import { useState } from "react";

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

/** Two-column row from the templates (<div class="row"> around col-md-6 fields). */
export function Row({ children }) {
  return <div className="row">{children}</div>;
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

export function TextField({ label, name, value, onChange, type = "text", col, error, help, ...rest }) {
  return (
    <Group col={col} label={label} htmlFor={`id_${name}`} error={error} help={help}>
      <input
        type={type}
        id={`id_${name}`}
        name={name}
        className="form-control"
        value={value ?? ""}
        onChange={(e) => onChange(name, e.target.value)}
        {...rest}
      />
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
export function SelectField({ label, name, value, onChange, options, col, error, placeholder, ...rest }) {
  return (
    <Group col={col} label={label} htmlFor={`id_${name}`} error={error}>
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
