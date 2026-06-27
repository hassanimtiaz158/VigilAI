import { useEffect, useState } from "react";

const DISMISS_MS = 8000;

export default function AlertBanner({ incident, onDismiss }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!incident || incident.severity !== "CRITICAL") {
      setVisible(false);
      return;
    }
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, DISMISS_MS);
    return () => clearTimeout(timer);
  }, [incident, onDismiss]);

  if (!visible || !incident) return null;

  const activity = (incident.activity_type || "UNKNOWN").toUpperCase();
  const notifLine = incident.alert_police
    ? "Police notified"
    : incident.alert_emergency
      ? "Emergency services notified"
      : "Owner notified";

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: "rgba(180, 20, 20, 0.92)",
        backdropFilter: "blur(6px)",
        color: "#fff",
        padding: "12px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        animation: "pulse-border 1.2s infinite",
        borderTop: "3px solid #ef4444",
        boxShadow: "0 -4px 24px rgba(220, 38, 38, 0.4)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span
          style={{
            fontSize: 20,
            animation: "pulse-scale 1s infinite",
            display: "inline-block",
          }}
        >
          🚨
        </span>
        <div>
          <div style={{ fontSize: 14, fontWeight: 800, letterSpacing: "0.5px" }}>
            CRITICAL ALERT — {activity}
          </div>
          <div style={{ fontSize: 11, opacity: 0.85, marginTop: 2 }}>
            {notifLine}
          </div>
        </div>
      </div>
      <button
        onClick={() => {
          setVisible(false);
          onDismiss?.();
        }}
        style={{
          background: "rgba(255,255,255,0.15)",
          border: "1px solid rgba(255,255,255,0.3)",
          color: "#fff",
          borderRadius: 6,
          padding: "4px 12px",
          fontSize: 11,
          fontWeight: 600,
          cursor: "pointer",
          flexShrink: 0,
        }}
      >
        Dismiss
      </button>
    </div>
  );
}
