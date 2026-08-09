import { Link, useParams } from "react-router-dom";
import feeAPI from "../../api/fees";
import Receipt from "../../components/Receipt";
import { ListCard } from "../../components/ListCard";
import { useAuth } from "../../context/AuthContext";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

/**
 * One receipt, laid out to be printed and handed to whoever asked for proof.
 *
 * The payer's name is filled in from the logged-in user rather than from the
 * response: the API scopes this endpoint by owner, so a receipt that loads
 * here is by definition this student's, and the student half of
 * fee_payment_dict deliberately carries no names.
 */
function ReceiptDetail() {
  const { paymentId } = useParams();
  const { user } = useAuth();
  usePageHeader({
    title: "Receipt",
    breadcrumb: [
      { text: "My Fees", to: "/student/fees/" },
      { text: "Receipts", to: "/student/receipts/" },
      { text: "Receipt" },
    ],
  });

  const { data: payment, loading, error } = useApi(
    () => feeAPI.getReceipt(paymentId),
    [paymentId]
  );

  if (loading) return null;
  if (error || !payment) {
    return (
      <ListCard title="Receipt">
        <div className="alert alert-warning mb-0">
          That receipt isn&apos;t one of yours.{" "}
          <Link to="/student/receipts/">Back to my receipts</Link>.
        </div>
      </ListCard>
    );
  }

  return (
    <ListCard title="Receipt">
      <Receipt
        payment={{ ...payment, student_name: user?.full_name }}
        onPrint={() => window.print()}
      />
      <hr className="d-print-none" />
      <Link className="d-print-none" to={`/student/fees/${payment.invoice_id}`}>
        See the bill this was paid against
      </Link>
    </ListCard>
  );
}

export default ReceiptDetail;
