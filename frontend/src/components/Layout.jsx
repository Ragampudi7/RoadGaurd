import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { getHealth, API_BASE } from "../api";
import "./layout.css";

const NAV = [
  { to: "/", label: "Analyse", end: true },
  { to: "/history", label: "History" },
  { to: "/map", label: "Map" },
  { to: "/admin", label: "Grievances" },
  { to: "/analytics", label: "Analytics" },
];

export default function Layout() {
  const [health, setHealth] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  // The single most useful thing in the header: whether the API is reachable
  // and whether it is serving the real road-defect model or the COCO fallback.
  const model = health?.model;
  let status = { text: "checking API…", tone: "idle" };
  if (failed) status = { text: "API unreachable", tone: "bad" };
  else if (model && !model.is_road_defect_model)
    status = { text: `fallback model (${model.name}) — not road defects`, tone: "warn" };
  else if (model) status = { text: `${model.name} · ${model.classes.join(", ")}`, tone: "ok" };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brandmark">
          <span className="dot" aria-hidden="true" />
          <div>
            <strong>Road Health</strong>
            <span className="muted small"> · citizen grievance tool</span>
          </div>
        </div>

        <nav className="nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className={`apistatus ${status.tone}`} title={API_BASE}>
          <span className="pip" aria-hidden="true" />
          <span className="small">{status.text}</span>
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>

      <footer className="foot small muted">
        Automated visual estimate from a single photograph. Score, severity and risk
        thresholds are defined by this project and are not taken from IRC, MoRTH,
        GHMC or any other official standard. Not a substitute for inspection by a
        qualified engineer.
      </footer>
    </div>
  );
}
