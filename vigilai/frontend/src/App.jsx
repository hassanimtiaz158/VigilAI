import { BrowserRouter, Routes, Route } from "react-router-dom";
import DomainSelectionPage from "./pages/DomainSelectionPage";
import LoadingScreen from "./pages/LoadingScreen";
import Dashboard from "./components/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DomainSelectionPage />} />
        <Route path="/loading/:domain" element={<LoadingWrapper />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

function LoadingWrapper() {
  const params = new URLSearchParams(window.location.search);
  const domain = params.get("domain") || "construction";
  return <LoadingScreen domain={domain} />;
}
