import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, ready } = useAuth();
  const loc = useLocation();

  // Wait for the localStorage read before deciding, otherwise a signed-in user
  // is bounced to /login for a frame on every refresh.
  if (!ready) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="glass px-6 py-4 text-sm text-[color:var(--color-muted)]">Loading…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return children;
}
