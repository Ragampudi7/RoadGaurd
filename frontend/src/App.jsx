import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Analyze from "./pages/Analyze";
import { History, MapView, Admin, Analytics } from "./pages/Placeholders";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Analyze />} />
          <Route path="history" element={<History />} />
          <Route path="map" element={<MapView />} />
          <Route path="admin" element={<Admin />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="*" element={<Analyze />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
