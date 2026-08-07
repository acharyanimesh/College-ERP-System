import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import studentAPI from "../../../api/students";
import { BackButton, ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/**
 * Roll-number lock control for a semester. `state` is what the API reports for
 * the intake(s) sitting in that semester: 'open' (still renumbering
 * alphabetically), 'locked' (frozen), or 'mixed' when a semester holds several
 * intakes that disagree — which the label has to say out loud, because a single
 * "Locked" badge there would be a lie about half of them.
 *
 * Locked is a dead end, not a toggle: it renders as static text with no click
 * target, because there is no unlock.
 */
function RollLockControl({ state, onLock }) {
  if (!state) return null;
  if (state === "locked") {
    return (
      <span
        className="text-muted"
        style={{ fontSize: "0.8rem", alignSelf: "center" }}
        title="Roll numbers are frozen for this intake. New students are appended at the end. This cannot be undone."
      >
        <i className="fas fa-lock"></i> Roll numbers locked
      </span>
    );
  }
  return (
    <button
      type="button"
      className="btn btn-outline-warning btn-sm"
      title="Roll numbers still renumber alphabetically when a student is added. Lock them once admissions close — this cannot be undone."
      onClick={onLock}
    >
      <i className="fas fa-lock-open"></i>{" "}
      {state === "mixed" ? "Lock remaining intakes" : "Lock roll numbers"}
    </button>
  );
}

/**
 * Password confirmation for locking. The lock is irreversible, so it asks for
 * the admin's own password rather than a yes/no the mouse can hit by accident.
 */
function LockPasswordDialog({ semester, submitting, error, onCancel, onConfirm }) {
  const [password, setPassword] = useState("");
  return (
    <div
      className="modal d-block"
      role="dialog"
      style={{ background: "rgba(0,0,0,0.5)" }}
    >
      <div className="modal-dialog modal-dialog-centered" role="document">
        <form
          className="modal-content"
          onSubmit={(e) => {
            e.preventDefault();
            onConfirm(password);
          }}
        >
          <div className="modal-header">
            <h5 className="modal-title">Lock roll numbers — Semester {semester}</h5>
          </div>
          <div className="modal-body">
            <p>
              Roll numbers for this intake will stop renumbering alphabetically.
              Students added afterwards are given the next free number at the
              end of the batch instead of their alphabetical position.
            </p>
            <p className="text-danger">
              <strong>This cannot be undone.</strong> There is no unlock.
            </p>
            <label htmlFor="id_lock_password">
              Confirm with your password:
            </label>
            <input
              id="id_lock_password"
              type="password"
              className="form-control"
              value={password}
              autoFocus
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <div className="text-danger small mt-2">{error}</div>}
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-warning"
              disabled={submitting || !password}
            >
              {submitting ? "Locking…" : "Lock roll numbers"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Manage Students — semester tiles with cascading promote / pass-out
 * actions (student_semester_list.html + promote_class).
 */
function StudentSemesters() {
  const { courseId } = useParams();
  const { addMessage } = useMessages();
  const { data, reload } = useApi(
    () => studentAPI.manageSemesters(courseId),
    [courseId]
  );

  const course = data?.course;
  const totalSemesters = data?.total_semesters || 0;
  const title = course
    ? `Manage Students - ${course.short_name} (Select Semester)`
    : "Manage Students";
  usePageHeader({ title, breadcrumb: [{ text: "Manage Students" }] });

  // Locking is what closes admissions for an intake: until then adding a
  // student re-sorts the batch so roll numbers stay alphabetical, and after it
  // late arrivals are simply appended at the end. It is one-way.
  const [lockingSemester, setLockingSemester] = useState(null);
  const [lockSubmitting, setLockSubmitting] = useState(false);
  const [lockError, setLockError] = useState("");

  const closeLockDialog = () => {
    setLockingSemester(null);
    setLockError("");
  };

  const confirmLock = async (password) => {
    setLockSubmitting(true);
    setLockError("");
    try {
      const res = await studentAPI.lockRollNumbers(
        courseId, lockingSemester, password);
      addMessage(res?.detail || "Roll numbers locked.", "success");
      closeLockDialog();
      reload();
    } catch (err) {
      // A wrong password keeps the dialog open so it can be retyped; anything
      // else is not retryable here, so it surfaces as a page message.
      const detail = err.response?.data?.detail;
      if (err.response?.status === 403) {
        setLockError(detail || "That password is not correct.");
      } else {
        addMessage(detail || "Could not lock the roll numbers.", "danger");
        closeLockDialog();
      }
    } finally {
      setLockSubmitting(false);
    }
  };

  const promote = async (semester, count) => {
    const isFinal = semester >= totalSemesters;
    const question = isFinal
      ? `Mark all ${count} final-semester student(s) of Semester ${semester} (both shifts) as PASSED OUT? They move to Passed Out records and leave the active student body.`
      : `Promote Semester ${semester} AND every higher semester up by one (both shifts)? Final-semester students will be marked as passed out. This cannot be undone.`;
    if (!window.confirm(question)) return;
    try {
      const res = await studentAPI.promote(courseId, semester);
      addMessage(res?.detail || "Promotion applied.", "success");
      reload();
    } catch {
      addMessage("Could not promote the class.", "danger");
    }
  };

  return (
    <ListCard
      title={title}
      action={<BackButton to="/student/manage/">Back to Courses</BackButton>}
    >
      {data && !data.semester_data?.length ? (
        <>
          <p className="text-muted">
            No semesters have been configured for this course.
          </p>
          <Link to={`/course/edit/${courseId}`} className="btn btn-primary">
            Set Number of Semesters
          </Link>
        </>
      ) : (
        <>
          <p className="text-muted">
            Select a semester to view its students. Promoting a semester moves
            it <strong>and every higher semester</strong> up by one (both
            shifts), so batches never mix. Final-semester students are marked
            as <strong>passed out</strong>.
          </p>
          <div className="text-right text-end mb-3">
            <Link
              to="/student/passed-out/"
              className="btn btn-outline-secondary btn-sm"
            >
              <i className="fas fa-user-graduate"></i> Passed Out Students
            </Link>
          </div>
          <TileGrid>
            {data?.semester_data?.map((item) => (
              <Tile
                key={item.number}
                to={`/student/manage/course/${courseId}/semester/${item.number}/`}
                label={`Semester ${item.number}`}
                badge={item.student_count}
                footer={
                  !item.student_count ? (
                    <span style={{ fontSize: "0.8rem" }}>
                      Semester currently not active
                    </span>
                  ) : (
                    <div className="d-flex flex-wrap justify-content-end gap-2">
                      <RollLockControl
                        state={item.roll_lock}
                        onLock={() => {
                          setLockError("");
                          setLockingSemester(item.number);
                        }}
                      />
                      {item.number >= totalSemesters ? (
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm"
                          onClick={() => promote(item.number, item.student_count)}
                        >
                          <i className="fas fa-user-graduate"></i> Pass out Sem{" "}
                          {item.number}
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-outline-success btn-sm"
                          onClick={() => promote(item.number, item.student_count)}
                        >
                          <i className="fas fa-arrow-up"></i> Promote Sem{" "}
                          {item.number} &amp; above
                        </button>
                      )}
                    </div>
                  )
                }
              />
            ))}
          </TileGrid>
        </>
      )}
      {lockingSemester !== null && (
        <LockPasswordDialog
          semester={lockingSemester}
          submitting={lockSubmitting}
          error={lockError}
          onCancel={closeLockDialog}
          onConfirm={confirmLock}
        />
      )}
    </ListCard>
  );
}

export default StudentSemesters;
