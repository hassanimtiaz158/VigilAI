import { useEffect, useState, useCallback } from "react";
import LiveFeed from "./components/LiveFeed";
import AlertPanel from "./components/AlertPanel";
import IncidentLog from "./components/IncidentLog";
import AIReasoning from "./components/AIReasoning";
import DomainSelector from "./components/DomainSelector";
import StatsBar from "./components/StatsBar";
import { useWebSocket } from "./hooks/useWebSocket";

function App() {
  const [activeDomain, setActiveDomain] = useState("construction");
  const [clock, setClock] = useState("--:--:--");
  const incidents = useWebSocket("ws://localhost:8000/stream");

  useEffect(() => {
    function tick() {
      setClock(new Date().toLocaleTimeString("en-GB", { hour12: false }));
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch("http://localhost:8000/incidents")
      .then((r) => r.json())
      .then((data) => {
        if (data.incidents?.length) {
          console.log(`[VigilAI] Loaded ${data.incidents.length} historical incidents`);
        }
      })
      .catch(() => {});
  }, []);

  const handleDomainChange = useCallback((d) => setActiveDomain(d), []);

  return (
    <div style={{ height: "100vh", overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--b0)", color: "var(--t1)" }}>
      {/* Topbar */}
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 18px", height: 48, background: "var(--b1)", borderBottom: "1px solid var(--border2)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, background: "var(--red-dim)", border: "1px solid var(--red-border)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth={2} strokeLinejoin="round">
              <path d="M12 3L4 7v5c0 4.5 3.3 8.7 8 9.9C17.7 20.7 21 16.5 21 12V7z" />
            </svg>
          </div>
          <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.5px" }}>
            Vigil<span style={{ color: "var(--red)" }}>AI</span>
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 5, background: "var(--red-dim)", border: "1px solid var(--red-border)", borderRadius: 20, padding: "3px 10px", fontSize: 10, fontWeight: 700, color: "var(--red)", letterSpacing: 1 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--red)", animation: "pulse-scale 1.4s infinite", display: "inline-block" }} />
            LIVE
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--t2)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />YOLOv8 online
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--t2)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />Groq connected
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--t2)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--yellow)", display: "inline-block" }} />CAM-03 lag
          </div>
          <span className="font-mono" style={{ fontSize: 12, color: "var(--t3)" }}>{clock}</span>
        </div>
      </header>

      {/* Domain bar */}
      <DomainSelector activeDomain={activeDomain} onDomainChange={handleDomainChange} />

      {/* Stats row */}
      <StatsBar incidents={incidents} />

      {/* Main grid: 1fr 320px */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", flex: 1, overflow: "hidden" }}>
        {/* Left column: camera (290px fixed) + incident log (fill) */}
        <div style={{ borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <LiveFeed domain={activeDomain} />
          <IncidentLog incidents={incidents} />
        </div>

        {/* Right column: alerts (max 250px) + reasoning (fill) */}
        <div style={{ display: "flex", flexDirection: "column", background: "var(--b1)", overflow: "hidden" }}>
          <AlertPanel incidents={incidents} />
          <AIReasoning incident={incidents[0] || null} />
        </div>
      </div>
    </div>
  );
}

export default App;
