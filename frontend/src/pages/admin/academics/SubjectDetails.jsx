import { useState } from "react";
import { useParams } from "react-router-dom";
import { subjectAPI } from "../../../api/academics";
import staffAPI from "../../../api/staff";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** Subject Details (hod_template/subject_details.html). */
function SubjectDetails() {
  const { subjectId } = useParams();
  const { addMessage } = useMessages();
  const [unassigning, setUnassigning] = useState(false);
  const { data: subject, reload } = useApi(
    () => subjectAPI.get(subjectId),
    [subjectId]
  );

  usePageHeader({
    title: subject ? `Subject Details - ${subject.name}` : "Subject Details",
    breadcrumb: [{ text: "Subject Details" }],
  });

  /**
   * Free this class's shift from the teacher holding it. Same endpoint the
   * Edit Staff page uses, just reached from the subject's side.
   */
  const unassign = async (cs, shift) => {
    const who = cs[`${shift}_staff_name`];
    const where = `${cs.course_short_name}${cs.semester ? ` Sem ${cs.semester}` : ""}`;
    if (!window.confirm(`Unassign ${who} from ${where} (${shift} shift)?`)) return;

    setUnassigning(true);
    try {
      const res = await staffAPI.unassignSubject(cs[`${shift}_staff_id`], {
        cs_id: cs.cs_id,
        shift,
      });
      addMessage(res.detail || "Teacher unassigned.", "success");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not unassign the teacher.",
        "danger"
      );
    } finally {
      setUnassigning(false);
    }
  };

  const teacherCell = (cs, shift) => {
    const name = cs[`${shift}_staff_name`];
    if (!name) return <span className="text-muted">—</span>;
    return (
      <span className="text-nowrap">
        <span className="badge badge-info">{name}</span>{" "}
        <button
          type="button"
          className="btn btn-sm btn-outline-danger"
          title={`Unassign ${name}`}
          disabled={unassigning}
          onClick={() => unassign(cs, shift)}
        >
          <i className="fas fa-user-slash"></i>
        </button>
      </span>
    );
  };

  if (!subject) return null;

  return (
    <ListCard
      dark
      title={subject.name}
      action={<BackButton to="/course/manage/">Back to Courses</BackButton>}
    >
      <dl className="row">
        <dt className="col-sm-3">Subject Name</dt>
        <dd className="col-sm-9">{subject.name}</dd>
        <dt className="col-sm-3">Subject Code</dt>
        <dd className="col-sm-9">{subject.code || "—"}</dd>
        <dt className="col-sm-3">Credit Hours</dt>
        <dd className="col-sm-9">{subject.credit_hours || "—"}</dd>
      </dl>

      <hr />

      <h5>Per-Course Teaching Assignments</h5>
      <p className="text-muted">
        Each course runs both shifts; the morning and day teacher of a class
        can differ. Use the <i className="fas fa-user-slash"></i> button to
        free a shift — the slot opens up for another teacher, and the subject
        itself is left in place.
      </p>
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Course</th>
            <th>Semester</th>
            <th>Morning Teacher</th>
            <th>Day Teacher</th>
          </tr>
        </thead>
        <tbody>
          {subject.course_semesters?.length ? (
            subject.course_semesters.map((cs, i) => (
              <tr key={cs.cs_id}>
                <td>{i + 1}</td>
                <td title={cs.course_name}>{cs.course_short_name}</td>
                <td>{cs.semester || "—"}</td>
                <td>{teacherCell(cs, "morning")}</td>
                <td>{teacherCell(cs, "day")}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={5} className="text-center">
                This subject is not assigned to any course yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </ListCard>
  );
}

export default SubjectDetails;
