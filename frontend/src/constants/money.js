/**
 * Money formatting for the fee screens.
 *
 * The server keeps every amount as a Decimal and does all the arithmetic
 * there; DRF hands them over as JSON numbers, and these helpers only ever
 * DISPLAY one. Nothing in the frontend should add, subtract or compare
 * amounts — a total worked out in JavaScript is a total that can disagree
 * with the receipt.
 *
 * en-IN grouping, which is the lakh/crore grouping Nepal uses too:
 * 51450.5 -> "51,450.50", 100000 -> "1,00,000.00".
 */
const FORMATTER = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** "Rs. 51,450.50". Renders a missing amount as zero rather than "NaN". */
export function formatMoney(value) {
  return `Rs. ${FORMATTER.format(Number(value) || 0)}`;
}

/** Just the number, for table cells that already carry a Rs. column header. */
export function formatAmount(value) {
  return FORMATTER.format(Number(value) || 0);
}
