/** Rupee formatting shared across the finance desk, e.g. rs(12000) → "Rs. 12,000". */
export function rs(n) {
  return "Rs. " + Number(n || 0).toLocaleString("en-IN");
}

/** Payment methods, matching FeePayment.METHOD_CHOICES on the backend. */
export const PAYMENT_METHODS = [
  { value: "cash", label: "Cash" },
  { value: "online", label: "Online transfer" },
  { value: "cheque", label: "Cheque" },
  { value: "bank", label: "Bank deposit" },
];
