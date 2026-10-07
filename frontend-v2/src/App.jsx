import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import UploadPage from "./pages/Upload";
import DetectionResult from "./pages/DetectionResult";
import Reports from "./pages/Reports";
import MapView from "./pages/MapView";
import Profile from "./pages/Profile";
import Queue from "./pages/Queue";
import DashboardLayout from "./layouts/DashboardLayout";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="result" element={<DetectionResult />} />
        <Route path="reports" element={<Reports />} />
        <Route path="map" element={<MapView />} />
        <Route path="profile" element={<Profile />} />
        <Route
          path="queue"
          element={
            <ProtectedRoute role="official">
              <Queue />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
