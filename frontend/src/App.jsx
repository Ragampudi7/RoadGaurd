import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardLayout from "./components/DashboardLayout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Upload from "./pages/app/Upload";
import DetectionResult from "./pages/app/DetectionResult";
import Reports from "./pages/app/Reports";
import Profile from "./pages/app/Profile";
import Queue from "./pages/app/Queue";

/* Recharts and Leaflet are the two heaviest dependencies and neither is needed
   to render the landing page, so they load only when their route is opened. */
const Dashboard = lazy(() => import("./pages/app/Dashboard"));
const MapView = lazy(() => import("./pages/app/MapView"));

const Loading = () => (
  <div className="glass grid place-items-center p-12 text-sm text-[color:var(--color-muted)]">Loading…</div>
);

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route path="/app" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Suspense fallback={<Loading />}><Dashboard /></Suspense>} />
        <Route path="upload" element={<Upload />} />
        <Route path="result" element={<DetectionResult />} />
        <Route path="reports" element={<Reports />} />
        <Route path="queue" element={<ProtectedRoute role="official"><Queue /></ProtectedRoute>} />
        <Route path="map" element={<Suspense fallback={<Loading />}><MapView /></Suspense>} />
        <Route path="profile" element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
