import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Navigation guard, not security: the server re-checks the token and role on
 * every request, so bypassing this gets an empty screen and a 401/403.
 * `role="official"` additionally requires that role.
 */
export default function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-base">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-signal border-t-transparent" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (role && user.role !== role) return <Navigate to="/app/dashboard" replace />;
  return children;
}
