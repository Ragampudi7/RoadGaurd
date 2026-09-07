import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, Upload, ScanLine, FileText, Map, User,
  LogOut, Menu, X, ShieldAlert, ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useDetection } from "../context/DetectionContext";
import DemoBadge from "./DemoBadge";

const LINKS = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/upload", label: "Upload", icon: Upload },
  { to: "/app/result", label: "Detection", icon: ScanLine },
  { to: "/app/reports", label: "Reports", icon: FileText },
  // Only an official account has a queue. Hiding the link is a courtesy, not
  // a control: the route guards itself and the server refuses the data.
  { to: "/app/queue", label: "Queue", icon: ShieldCheck, officialOnly: true },
  { to: "/app/map", label: "Map", icon: Map },
  { to: "/app/profile", label: "Profile", icon: User },
];

export default function DashboardLayout() {
  const { user, logout, isOfficial } = useAuth();
  const { isMock } = useDetection();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);

  const sidebar = (
    <nav className="flex flex-col gap-1 p-3">
      {LINKS.filter((l) => !l.officialOnly || isOfficial).map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to} to={to} end={end} onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
              isActive
                ? "bg-[color:var(--color-brand)]/18 text-[color:var(--color-brand)] border border-[color:var(--color-brand)]/25"
                : "text-[color:var(--color-muted)] hover:bg-white/8 hover:text-[color:var(--color-ink)] border border-transparent"
            }`
          }>
          <Icon size={17} />
          {label}
        </NavLink>
      ))}

      <button
        onClick={() => { logout(); nav("/"); }}
        className="mt-2 flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium
                   text-[color:var(--color-muted)] hover:bg-white/8 hover:text-[color:var(--color-danger)]
                   transition border border-transparent cursor-pointer">
        <LogOut size={17} /> Log out
      </button>
    </nav>
  );

  return (
    <div className="min-h-screen">
      {/* header */}
      <header className="sticky top-0 z-30 glass-soft rounded-none border-x-0 border-t-0">
        <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-3">
          <button
            className="lg:hidden rounded-lg p-2 hover:bg-white/10 cursor-pointer"
            onClick={() => setOpen((o) => !o)} aria-label="Toggle navigation">
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>

          <NavLink to="/app" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg
                             bg-gradient-to-br from-[color:var(--color-brand)] to-[color:var(--color-brand-deep)]">
              <ShieldAlert size={17} className="text-white" />
            </span>
            <span className="font-semibold tracking-tight">RoadGuard <span className="text-[color:var(--color-brand)]">AI</span></span>
          </NavLink>

          <div className="ml-auto flex items-center gap-3">
            {isMock && <DemoBadge className="hidden sm:inline-flex" />}
            <div className="hidden sm:block text-right leading-tight">
              <div className="text-sm font-medium capitalize">{user?.name}</div>
              <div className="text-[11px] text-[color:var(--color-muted)]">{user?.email}</div>
            </div>
            <span className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-sm font-semibold uppercase">
              {user?.name?.[0] ?? "?"}
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1400px] gap-5 px-4 py-5">
        {/* desktop sidebar */}
        <aside className="hidden lg:block w-60 shrink-0">
          <div className="glass sticky top-20">{sidebar}</div>
        </aside>

        {/* mobile drawer */}
        <AnimatePresence>
          {open && (
            <motion.aside
              initial={{ opacity: 0, x: -18 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -18 }} transition={{ duration: 0.2 }}
              className="lg:hidden fixed inset-x-4 top-[68px] z-20 glass">
              {sidebar}
            </motion.aside>
          )}
        </AnimatePresence>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
