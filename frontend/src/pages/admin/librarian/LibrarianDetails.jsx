import { useParams } from "react-router-dom";
import librarianAPI from "../../../api/librarians";
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

/** Librarian Details — the librarian counterpart of StaffDetails. */
function LibrarianDetails() {
  const { librarianId } = useParams();
  const { data: librarian } = useApi(
    () => librarianAPI.get(librarianId),
    [librarianId]
  );

  const fullName = librarian
    ? `${librarian.first_name} ${librarian.last_name}`
    : "";
  usePageHeader({
    title: librarian ? `Librarian Details - ${fullName}` : "Librarian Details",
    breadcrumb: [{ text: "Librarian Details" }],
  });

  if (!librarian) return null;

  return (
    <ListCard
      dark
      title={fullName}
      action={
        <BackButton to="/librarian/manage/">Back to Manage Librarians</BackButton>
      }
    >
      <dl className="row">
        <DetailRow label="Librarian ID">{librarian.librarian_id || "—"}</DetailRow>
        <DetailRow label="Full Name">{fullName}</DetailRow>
        <DetailRow label="Email">{librarian.email}</DetailRow>
        <DetailRow label="Phone Number">{librarian.phone_number || "—"}</DetailRow>
        <DetailRow label="Date of Birth">{librarian.date_of_birth || "—"}</DetailRow>
        <DetailRow label="Gender">{librarian.gender_display || "—"}</DetailRow>
        <DetailRow label="Address">{librarian.address || "—"}</DetailRow>
        <DetailRow label="Account Status">
          {librarian.verified ? (
            <span className="badge badge-success">Verified</span>
          ) : (
            <span className="badge badge-warning">Pending verification</span>
          )}
        </DetailRow>
      </dl>
    </ListCard>
  );
}

export default LibrarianDetails;
