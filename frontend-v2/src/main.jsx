import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { DetectionProvider } from "./context/DetectionContext";
import { ReportsProvider } from "./context/ReportsContext";
import { getHealth } from "./lib/api";
import "./index.css";

// Wake the API the moment anyone opens the site. On Render's free plan it
// sleeps when idle and takes a while to start; this way it is usually awake
// by the time the visitor has typed their password.
getHealth().catch(() => {});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <DetectionProvider>
          <ReportsProvider>
            <App />
          </ReportsProvider>
        </DetectionProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
