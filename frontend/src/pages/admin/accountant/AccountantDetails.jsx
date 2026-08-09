import { useParams } from "react-router-dom";
import accountantAPI from "../../../api/accountants";
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

/** Accountant Details — the accountant counterpart of LibrarianDetails. */
function AccountantDetails() {
  const { accountantId } = useParams();
  const { data: accountant } = useApi(
    () => accountantAPI.get(accountantId),
    [accountantId]
  );

  const fullName = accountant
    ? `${accountant.first_name} ${accountant.last_name}`
    : "";
  usePageHeader({
    title: accountant ? `Accountant Details - ${fullName}` : "Accountant Details",
    breadcrumb: [{ text: "Accountant Details" }],
  });

  if (!accountant) return null;

  return (
    <ListCard
      dark
      title={fullName}
      action={
        <BackButton to="/accountant/manage/">Back to Manage Accountants</BackButton>
      }
    >
      <dl className="row">
        <DetailRow label="Accountant ID">{accountant.accountant_id || "—"}</DetailRow>
        <DetailRow label="Full Name">{fullName}</DetailRow>
        <DetailRow label="Email">{accountant.email}</DetailRow>
        <DetailRow label="Phone Number">{accountant.phone_number || "—"}</DetailRow>
        <DetailRow label="Date of Birth">{accountant.date_of_birth || "—"}</DetailRow>
        <DetailRow label="Gender">{accountant.gender_display || "—"}</DetailRow>
        <DetailRow label="Address">{accountant.address || "—"}</DetailRow>
        <DetailRow label="Account Status">
          {accountant.verified ? (
            <span className="badge badge-success">Verified</span>
          ) : (
            <span className="badge badge-warning">Pending verification</span>
          )}
        </DetailRow>
      </dl>
    </ListCard>
  );
}

export default AccountantDetails;
