import { useEffect, useState, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import LiveFeed from "./LiveFeed";
import AlertPanel from "./AlertPanel";
import IncidentLog from "./IncidentLog";
import NotificationLog from "./NotificationLog";
import AIReasoning from "./AIReasoning";
import StatsBar from "./StatsBar";
import { useWebSocket } from "../hooks/useWebSocket";
import { API_BASE, WS_URL } from "../config";

const DOMAIN_META = {
  construction: { icon: "\uD83C\uDFD7", label: "Construction", color: "#fb923c" },
  school: { icon: "\uD83C\uDFEB", label: "School", color: "#60a5fa" },
  elderly: { icon: "\uD83D\uDC74", label: "Elderly Care", color: "#a78bfa" },
  child: { icon: "\uD83D\uDC76", label: "Child Safety", color: "#34d399" },
  public: { icon: "\uD83C\uDF06", label: "Public Space", color: "#fbbf24" },
};

export default function Dashboard({ onCriticalIncident }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeDomain, setActiveDomain] = useState(
    location.state?.selectedDomain || "construction"
  );
  const [clock, setClock] = useState("--:--:--");
  const { incidents, connected, latestCritical } = useWebSocket(WS_URL);

  const domainMeta = DOMAIN_META[activeDomain] || DOMAIN_META.construction;

  useEffect(() => {
    function tick() {
      setClock(new Date().toLocaleTimeString("en-GB", { hour12: false }));
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (latestCritical) {
      onCriticalIncident?.(latestCritical);
    }
  }, [latestCritical, onCriticalIncident]);

  const handleSwitchDomain = useCallback(() => {
    navigate("/#domains");
  }, [navigate]);

  const handleStopMonitoring = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/monitoring/stop`, { method: "POST" });
    } catch {
      // Best-effort — navigate even if backend is down
    }
    navigate("/");
  }, [navigate]);

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
          <div style={{ display: "flex", alignItems: "center", gap: 5, background: connected ? "var(--red-dim)" : "var(--border2)", border: `1px solid ${connected ? "var(--red-border)" : "var(--border)"}`, borderRadius: 20, padding: "3px 10px", fontSize: 10, fontWeight: 700, color: connected ? "var(--red)" : "var(--t3)", letterSpacing: 1 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: connected ? "var(--red)" : "var(--t3)", animation: connected ? "pulse-scale 1.4s infinite" : "none", display: "inline-block" }} />
            {connected ? "LIVE" : "OFFLINE"}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--t2)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />YOLOv8 online
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--t2)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: connected ? "var(--green)" : "var(--red)", display: "inline-block" }} />{connected ? "Groq connected" : "Groq disconnected"}
          </div>
          <span className="font-mono" style={{ fontSize: 12, color: "var(--t3)" }}>{clock}</span>
          <button
            onClick={handleSwitchDomain}
            style={{
              padding: "4px 12px",
              borderRadius: 6,
              border: `1px solid ${domainMeta.color}40`,
              background: `${domainMeta.color}15`,
              color: domainMeta.color,
              fontSize: 11,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = `${domainMeta.color}25`; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = `${domainMeta.color}15`; }}
          >
            <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 1l4 4-4 4" /><path d="M3 11V9a4 4 0 0 1 4-4h14" />
              <path d="M7 23l-4-4 4-4" /><path d="M21 13v2a4 4 0 0 1-4 4H3" />
            </svg>
            Switch Domain
          </button>
          <button
            onClick={handleStopMonitoring}
            style={{
              padding: "4px 12px",
              borderRadius: 6,
              border: "1px solid rgba(244,63,63,0.3)",
              background: "rgba(244,63,63,0.1)",
              color: "#f87171",
              fontSize: 11,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(244,63,63,0.2)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(244,63,63,0.1)"; }}
          >
            <svg width={12} height={12} viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
            Stop Monitoring
          </button>
        </div>
      </header>

      {/* Active domain bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "6px 18px", background: "var(--b1)",
        borderBottom: "1px solid var(--border)", flexShrink: 0,
      }}>
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          padding: "3px 10px", borderRadius: 6,
          background: `${domainMeta.color}15`,
          border: `1px solid ${domainMeta.color}40`,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: domainMeta.color, display: "inline-block" }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: domainMeta.color }}>
            {domainMeta.icon} {domainMeta.label}
          </span>
        </span>
        <span style={{ fontSize: 10, color: "var(--t3)", letterSpacing: "0.5px" }}>Monitoring active</span>
      </div>

      {/* Stats row */}
      <StatsBar incidents={incidents} domain={activeDomain} />

      {/* Main grid: 1fr 320px */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", flex: 1, overflow: "hidden" }}>
        {/* Left column: camera (290px fixed) + incident log (fill) + notification log */}
        <div style={{ borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <LiveFeed domain={activeDomain} />
          <IncidentLog incidents={incidents} />
          <NotificationLog />
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
