import { useState, useCallback } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import DomainSelectionPage from "./pages/DomainSelectionPage";
import LoadingScreen from "./pages/LoadingScreen";
import Dashboard from "./components/Dashboard";
import AlertBanner from "./components/AlertBanner";

export default function App() {
  const [dismissedCritical, setDismissedCritical] = useState(null);

  const handleDismissBanner = useCallback(() => {
    setDismissedCritical(null);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DomainSelectionPage />} />
        <Route path="/loading/:domain" element={<LoadingWrapper />} />
        <Route
          path="/dashboard"
          element={
            <Dashboard
              onCriticalIncident={setDismissedCritical}
            />
          }
        />
      </Routes>
      <AlertBanner
        incident={dismissedCritical}
        onDismiss={handleDismissBanner}
      />
    </BrowserRouter>
  );
}

function LoadingWrapper() {
  const params = new URLSearchParams(window.location.search);
  const domain = params.get("domain") || "construction";
  return <LoadingScreen domain={domain} />;
}
