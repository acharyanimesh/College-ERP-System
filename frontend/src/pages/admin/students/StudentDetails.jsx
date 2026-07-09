import { useParams } from "react-router-dom";
import studentAPI from "../../../api/students";
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

/** Student Details (hod_template/student_details.html). */
function StudentDetails() {
  const { studentId } = useParams();
  const { data: student } = useApi(() => studentAPI.get(studentId), [studentId]);

  const fullName = student ? `${student.first_name} ${student.last_name}` : "";
  usePageHeader({
    title: student ? `Student Details - ${fullName}` : "Student Details",
    breadcrumb: [{ text: "Student Details" }],
  });

  if (!student) return null;

  return (
    <ListCard
      dark
      title={fullName}
      action={<BackButton to="/student/manage/">Back to Manage Students</BackButton>}
    >
      {student.profile_pic && (
        <div className="mb-3">
          <img
            className="img img-fluid"
            height={96}
            width={96}
            src={student.profile_pic}
            alt=""
          />
        </div>
      )}
      <dl className="row">
        <DetailRow label="Registration Number">
          {student.registration_number || "—"}
        </DetailRow>
        <DetailRow label="Roll Number">{student.roll_number || "—"}</DetailRow>
        <DetailRow label="Full Name">{fullName}</DetailRow>
        <DetailRow label="Email">{student.email}</DetailRow>
        <DetailRow label="Phone Number">{student.phone_number || "—"}</DetailRow>
        <DetailRow label="Date of Birth">{student.date_of_birth || "—"}</DetailRow>
        <DetailRow label="Gender">{student.gender_display || "—"}</DetailRow>
        <DetailRow label="Address">{student.address || "—"}</DetailRow>
        <DetailRow label="Course">
          {student.course ? (
            <span className="badge badge-info" title={student.course_name}>
              {student.course_short_name}
            </span>
          ) : (
            <span className="text-muted">No course assigned</span>
          )}
        </DetailRow>
        <DetailRow label="Session">{student.session_label || "—"}</DetailRow>
        <DetailRow label="Shift">
          <span className="badge badge-secondary">{student.shift_display}</span>
        </DetailRow>
      </dl>
    </ListCard>
  );
}

export default StudentDetails;
