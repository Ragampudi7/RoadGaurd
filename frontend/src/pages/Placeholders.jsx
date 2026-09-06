/**
 * Screens that cannot exist until the database does.
 *
 * These are deliberately stubs rather than mock-data screens: a History page
 * populated with invented rows looks finished and hides the fact that nothing
 * is persisted yet. Each stub names the endpoint it is waiting for, so wiring
 * it up in step 3 is mechanical.
 */

function Pending({ title, sub, needs, children }) {
  return (
    <>
      <h1 className="pagehead">{title}</h1>
      <p className="pagesub">{sub}</p>
      <div className="pending">
        <h3>Waiting on the database layer</h3>
        <p style={{ margin: 0 }}>
          This screen needs <code>{needs}</code>, which does not exist yet. The
          backend currently persists nothing — every analysis is computed and
          returned in one request.
        </p>
        {children}
      </div>
    </>
  );
}

export function History() {
  return (
    <Pending
      title="Submission history"
      sub="Every report this device has filed, newest first."
      needs="GET /reports"
    >
      <p style={{ margin: 0 }}>
        Will list stored reports with score, condition, risk tier, timestamp and a
        thumbnail, each linking to its saved PDF.
      </p>
    </Pending>
  );
}

export function MapView() {
  return (
    <Pending
      title="Reported locations"
      sub="Every submission pinned by GPS, coloured by risk level."
      needs="GET /reports?bbox=…"
    >
      <p style={{ margin: 0 }}>
        Leaflet is already installed. Pins will be coloured by risk band, using the
        same palette as the score gauge and the PDF.
      </p>
    </Pending>
  );
}

export function Admin() {
  return (
    <Pending
      title="Grievance queue"
      sub="Track complaints from submission through to resolution."
      needs="GET /reports and PATCH /reports/{id}/status"
    >
      <p style={{ margin: 0 }}>
        Filter by priority tier, move a complaint between Submitted, Acknowledged
        and Resolved. Note this implies an authentication story — an open endpoint
        that lets anyone mark a pothole resolved is not a workflow, so we should
        decide who is allowed to change status before building it.
      </p>
    </Pending>
  );
}

export function Analytics() {
  return (
    <Pending
      title="Analytics"
      sub="Aggregate road condition across all submissions."
      needs="GET /reports/stats"
    >
      <p style={{ margin: 0 }}>
        Defects by class, health score distribution, submissions over time, worst
        locations by risk index. Recharts is installed and ready.
      </p>
    </Pending>
  );
}
