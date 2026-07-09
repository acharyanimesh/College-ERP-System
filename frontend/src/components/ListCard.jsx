import { Link } from "react-router-dom";

/**
 * Page shells shared by the converted list/manage templates:
 * <section class="content"> … <div class="card"> with a header (title +
 * optional right-side action) and a body, plus the tile grid used by the
 * drill-down screens (course → semester → shift).
 */

export function ListCard({ title, action, dark, scrollBody, children }) {
  return (
    <section className="content">
      <div className="container-fluid">
        <div className="row">
          <div className="col-md-12">
            <div className={`card ${dark ? "card-dark" : ""}`}>
              <div className="card-header d-flex justify-content-between align-items-center">
                <h3 className="card-title">{title}</h3>
                {action && <div className="text-nowrap">{action}</div>}
              </div>
              <div
                className="card-body"
                style={
                  scrollBody
                    ? { overflowX: "auto", overflowY: "auto", maxHeight: 600 }
                    : undefined
                }
              >
                {children}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/** Small "← Back to …" header button used across the drill-down pages. */
export function BackButton({ to, children }) {
  return (
    <Link to={to} className="btn btn-secondary btn-sm">
      &larr; {children}
    </Link>
  );
}

/** Grid wrapper for tiles. */
export function TileGrid({ children }) {
  return <div className="row">{children}</div>;
}

/**
 * One drill-down tile (course/semester/shift cards): label + count badge,
 * optionally clickable and with a footer strip (promote buttons etc.).
 */
export function Tile({ to, label, title, badge, badgeClass = "badge-info", muted, footer }) {
  const body = (
    <div
      className="card-body d-flex justify-content-between align-items-center"
      style={{ padding: "1.25rem 1.5rem" }}
    >
      <span className="font-weight-bold" style={{ fontSize: "1.05rem" }} title={title}>
        {label}
      </span>
      {badge !== undefined ? (
        <span
          className={`badge ${badgeClass} badge-pill`}
          style={{ padding: "0.5em 0.85em", fontSize: "0.85rem" }}
        >
          {badge}
        </span>
      ) : (
        <span className="text-muted" style={{ fontSize: "0.8rem" }}>
          {muted}
        </span>
      )}
    </div>
  );

  return (
    <div className="col-md-4 col-sm-6 mb-4 d-flex">
      <div
        className={`card card-outline ${to ? "card-primary" : "card-secondary"} h-100 mb-0 shadow-sm w-100`}
      >
        {to ? (
          <Link to={to} className="text-decoration-none text-reset">
            {body}
          </Link>
        ) : (
          body
        )}
        {footer && (
          <div className="card-footer text-right" style={{ padding: "0.5rem 1rem" }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
