import { SEV_COLORS } from "../utils/severity";

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function IncidentLog({ incidents }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 14px", borderBottom: "1px solid var(--border)", background: "var(--b1)", flexShrink: 0 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t2)" }}>Incident log</span>
        <span style={{ fontSize: 10, color: "var(--t3)" }}>{incidents.length} total</span>
      </div>

      <div style={{ overflowY: "auto", flex: 1 }}>
        <div style={{ display: "grid", gridTemplateColumns: "70px 80px 1fr 72px", gap: 8, padding: "8px 14px", background: "var(--b1)", fontSize: 9, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--t3)", fontWeight: 700, position: "sticky", top: 0 }}>
          <div>Time</div><div>Domain</div><div>Summary</div><div>Severity</div>
        </div>

        {incidents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "20px 0", color: "var(--t3)", fontSize: 11 }}>No incidents recorded</div>
        ) : (
          incidents.map((inc) => {
            const s = SEV_COLORS[inc.severity] || SEV_COLORS.MEDIUM;
            return (
              <div
                key={inc.id}
                style={{ display: "grid", gridTemplateColumns: "70px 80px 1fr 72px", gap: 8, padding: "8px 14px", borderBottom: "1px solid var(--border)", fontSize: 11, alignItems: "center" }}
                className="hover:bg-white/[0.015]"
              >
                <div className="font-mono" style={{ color: "var(--t3)" }}>{formatTime(inc.timestamp)}</div>
                <div style={{ color: "var(--t2)" }}>{inc.domain}</div>
                <div style={{ color: "var(--t1)", lineHeight: 1.3 }} className="truncate">{inc.summary}</div>
                <div>
                  <span style={{
                    fontSize: 8, fontWeight: 800, letterSpacing: "0.7px", padding: "2px 6px", borderRadius: 3, textAlign: "center", display: "inline-block",
                    background: s.bg, color: s.fg, border: `1px solid ${s.border}`,
                  }}>
                    {inc.severity}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
