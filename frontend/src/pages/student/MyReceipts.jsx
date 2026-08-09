import { Link } from "react-router-dom";
import feeAPI from "../../api/fees";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

/**
 * Every fee receipt the student holds, across all their bills.
 *
 * FeeInvoiceDetail already shows the receipts against one invoice; this is the
 * list you want when what you have is a receipt number and no idea which
 * semester it belonged to — or when somebody has asked for proof of payment
 * and you don't want to hunt through four bills to find it.
 */
function MyReceipts() {
  usePageHeader({
    title: "My Receipts",
    breadcrumb: [{ text: "My Fees", to: "/student/fees/" }, { text: "Receipts" }],
  });
  const { data: receipts, loading } = useApi(() => feeAPI.myReceipts());

  return (
    <ListCard title="My Receipts" scrollBody>
      <p className="text-muted">
        Every payment recorded against your name. A receipt is a permanent
        record — if something on one looks wrong, take it to the accounts
        office rather than assuming it will be corrected quietly.
      </p>

      <table className="table table-bordered table-hover" style={{ minWidth: 700 }}>
        <thead className="thead-dark">
          <tr>
            <th>Receipt</th>
            <th>Received</th>
            <th>Against</th>
            <th>Mode</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {!loading && !receipts?.length && (
            <tr>
              <td colSpan={5} className="text-center">
                You haven&apos;t paid anything yet. Your bills are under{" "}
                <Link to="/student/fees/">My Fees</Link>.
              </td>
            </tr>
          )}
          {receipts?.map((p) => (
            <tr key={p.id}>
              <td>
                <Link to={`/student/receipts/${p.id}`}>
                  {p.receipt_no}
                </Link>
              </td>
              <td>{p.received_on}</td>
              <td>{p.invoice_number}</td>
              <td>
                {p.mode_display}
                {p.reference && (
                  <>
                    <br />
                    <small className="text-muted">{p.reference}</small>
                  </>
                )}
              </td>
              <td className="font-weight-bold">{formatMoney(p.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default MyReceipts;
