import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Upload,
  FileText,
  Map,
  User,
  LogOut,
  Menu,
  X,
  Shield,
  Bell,
  ClipboardList,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useReports } from "../context/ReportsContext";
import { riskColor } from "../lib/present";

function timeAgo(iso) {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs === 1 ? "" : "s"} ago`;
  const days = Math.round(hrs / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

const navItems = [
  { to: "/app/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/app/upload", icon: Upload, label: "Upload" },
  { to: "/app/reports", icon: FileText, label: "Reports" },
  { to: "/app/map", icon: Map, label: "Map View" },
  { to: "/app/profile", icon: User, label: "Profile" },
];

export default function DashboardLayout() {
  const { user, logout, isOfficial } = useAuth();
  const { reports } = useReports();
  const items = isOfficial
    ? [...navItems.slice(0, 1), { to: "/app/queue", icon: ClipboardList, label: "Grievance Queue" }, ...navItems.slice(1)]
    : navItems;
  // Notifications are the account's own most recent reports and their status.
  const recentActivity = [...reports]
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, 4);
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const showNotifications = location.pathname === "/app/dashboard";

  useEffect(() => {
    if (!showNotifications) setNotificationsOpen(false);
  }, [showNotifications]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="px-6 py-6 font-display text-lg font-bold">
        <Shield className="mb-1 inline h-5 w-5 text-signal" />{" "}
        <span className="text-white">RoadGuard </span>
        <span className="text-signal">AI</span>
      </div>

      <div className="mx-4 mb-3 rounded-lg border border-signal/20 bg-signal/10 px-3 py-2 text-xs font-medium text-signal">
        {isOfficial ? "Official Portal" : "Citizen Portal"}
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {items.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? "bg-signal/15 text-signal"
                  : "text-ink/60 hover:bg-panel2 hover:text-ink"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-line p-4">
        <div className="mb-3 flex items-center gap-3 rounded-lg bg-panel2 px-3 py-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-signal/20 text-sm font-bold text-signal">
            {user?.name?.charAt(0) || "U"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-white">{user?.name}</div>
            <div className="truncate text-xs text-ink/50">{user?.email}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink/60 transition-colors hover:bg-red-500/10 hover:text-red-400"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-base">
      <aside className="hidden w-64 shrink-0 border-r border-line bg-panel lg:block">{sidebar}</aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            className="relative h-full w-64 border-r border-line bg-panel"
          >
            <button onClick={() => setMobileOpen(false)} className="absolute right-3 top-5 text-ink/60">
              <X className="h-5 w-5" />
            </button>
            {sidebar}
          </motion.aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-panel/80 px-4 py-4 backdrop-blur-md lg:px-8">
          <button onClick={() => setMobileOpen(true)} className="text-ink/60 lg:hidden">
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden lg:block" />
          <div className="flex items-center gap-4">
            {showNotifications && (
              <button
                onClick={() => setNotificationsOpen((open) => !open)}
                className="relative rounded-lg border border-line p-2 text-ink/60 transition-colors hover:text-ink"
                aria-label="Open notifications"
              >
                <Bell className="h-4 w-4" />
                {recentActivity.length > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-hazard" />
                )}
              </button>
            )}
            {showNotifications && notificationsOpen && createPortal(
              <>
                <button
                  aria-label="Close notifications"
                  className="fixed inset-0 cursor-default bg-transparent"
                  style={{ zIndex: 2147483600 }}
                  onClick={() => setNotificationsOpen(false)}
                />
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  style={{ zIndex: 2147483601 }}
                  className="fixed right-4 top-14 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-line bg-panel shadow-[0_24px_70px_rgba(0,0,0,0.8)] lg:right-8"
                >
                  <div className="border-b border-line px-4 py-3">
                    <p className="font-display font-semibold text-white">Notifications</p>
                    <p className="text-xs text-ink/50">Your latest reports</p>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {recentActivity.length === 0 && (
                      <p className="px-4 py-4 text-sm text-ink/50">Nothing yet.</p>
                    )}
                    {recentActivity.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          setNotificationsOpen(false);
                          navigate("/app/reports");
                        }}
                        className="flex w-full items-start gap-3 border-b border-line/60 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-panel2 focus:outline-none"
                      >
                        <span
                          className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: riskColor[item.riskLevel] || "#2563eb" }}
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium text-white">
                            {item.status === "Draft" ? "Draft saved" : `Report ${item.status.toLowerCase()}`}
                          </span>
                          <span className="block text-xs text-ink/55">{item.area} · {item.riskLevel} risk</span>
                          <span className="block text-xs text-ink/40">{item.reference} | {timeAgo(item.createdAt)}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => {
                      setNotificationsOpen(false);
                      navigate("/app/reports");
                    }}
                    className="w-full border-t border-line px-4 py-3 text-sm font-medium text-signal hover:bg-signal/10"
                  >
                    View all reports
                  </button>
                </motion.div>
              </>,
              document.body
            )}
            <div className="hidden items-center gap-2 sm:flex">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-signal/20 text-xs font-bold text-signal">
                {user?.name?.charAt(0) || "U"}
              </div>
              <span className="text-sm font-medium text-ink">{user?.name}</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
