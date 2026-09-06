import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { DetectionProvider } from "./context/DetectionContext";
import { ReportsProvider } from "./context/ReportsContext";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <DetectionProvider>
          <ReportsProvider>
            <App />
          </ReportsProvider>
        </DetectionProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
