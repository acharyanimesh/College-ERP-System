import { useParams } from "react-router-dom";
import staffAPI from "../../../api/staff";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

function DetailRow({ label, children }) {
  return (
    <>
      <dt className="col-sm-3">{label}</dt>
      <dd className="col-sm-9">{children}</dd>
    </>
  );
}

/** Staff Details (hod_template/staff_details.html). */
function StaffDetails() {
  const { staffId } = useParams();
  const { data: staff } = useApi(() => staffAPI.get(staffId), [staffId]);

  const fullName = staff ? `${staff.first_name} ${staff.last_name}` : "";
  usePageHeader({
    title: staff ? `Staff Details - ${fullName}` : "Staff Details",
    breadcrumb: [{ text: "Staff Details" }],
  });

  if (!staff) return null;

  return (
    <ListCard
      dark
      title={fullName}
      action={<BackButton to="/staff/manage/">Back to Manage Staff</BackButton>}
    >
      <dl className="row">
        <DetailRow label="Staff ID">{staff.staff_id || "—"}</DetailRow>
        <DetailRow label="Full Name">{fullName}</DetailRow>
        <DetailRow label="Email">{staff.email}</DetailRow>
        <DetailRow label="Phone Number">{staff.phone_number || "—"}</DetailRow>
        <DetailRow label="Date of Birth">{staff.date_of_birth || "—"}</DetailRow>
        <DetailRow label="Gender">{staff.gender_display || "—"}</DetailRow>
        <DetailRow label="Address">{staff.address || "—"}</DetailRow>
        <DetailRow label="Teaches in Course(s)">
          {staff.courses?.length ? (
            staff.courses.map((c) => (
              <span key={c.id} className="badge badge-info" title={c.name}>
                {c.short_name}
              </span>
            ))
          ) : (
            <span className="text-muted">No course assigned</span>
          )}
        </DetailRow>
        <DetailRow label="Shift(s)">
          <span className="badge badge-secondary">{staff.shifts_display}</span>
        </DetailRow>
        <DetailRow label="Distinct Subjects Taught">
          <span className="badge badge-success">{staff.subject_count}</span>
        </DetailRow>
      </dl>

      <hr />

      <h5>Teaching Assignments</h5>
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Code</th>
            <th>Subject</th>
            <th>Course</th>
            <th>Semester</th>
            <th>Shift</th>
          </tr>
        </thead>
        <tbody>
          {staff.assignments?.length ? (
            staff.assignments.map((a, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td>{a.subject_code || "—"}</td>
                <td>{a.subject_name}</td>
                <td title={a.course_name}>{a.course_short_name}</td>
                <td>{a.semester || "—"}</td>
                <td>
                  <span className="badge badge-secondary">{a.shifts}</span>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6} className="text-center">
                No teaching assignments yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </ListCard>
  );
}

export default StaffDetails;
