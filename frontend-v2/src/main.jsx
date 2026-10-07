import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { DetectionProvider } from "./context/DetectionContext";
import { ReportsProvider } from "./context/ReportsContext";
import "./index.css";

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
