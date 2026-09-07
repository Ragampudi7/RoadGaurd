import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * `role="official"` additionally requires the account to hold that role.
 *
 * This is navigation, not security. The role in the client came from the
 * server's own profile response and the server re-checks it on every request,
 * so bypassing this guard gets you an empty screen and a 403, not data.
 */
export default function ProtectedRoute({ children, role }) {
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
  if (role && user.role !== role) return <Navigate to="/app" replace />;
  return children;
}
