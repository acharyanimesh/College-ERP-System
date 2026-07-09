import { useParams } from "react-router-dom";
import { subjectAPI } from "../../../api/academics";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/** Subject Details (hod_template/subject_details.html). */
function SubjectDetails() {
  const { subjectId } = useParams();
  const { data: subject } = useApi(() => subjectAPI.get(subjectId), [subjectId]);

  usePageHeader({
    title: subject ? `Subject Details - ${subject.name}` : "Subject Details",
    breadcrumb: [{ text: "Subject Details" }],
  });

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
        can differ.
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
              <tr key={i}>
                <td>{i + 1}</td>
                <td title={cs.course_name}>{cs.course_short_name}</td>
                <td>{cs.semester || "—"}</td>
                <td>
                  {cs.morning_staff_name ? (
                    <span className="badge badge-info">{cs.morning_staff_name}</span>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td>
                  {cs.day_staff_name ? (
                    <span className="badge badge-info">{cs.day_staff_name}</span>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
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
