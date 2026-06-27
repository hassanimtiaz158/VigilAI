import { SEV_COLORS } from "../utils/severity";

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function AlertPanel({ incidents }) {
  const latest = incidents.slice(0, 5);

  return (
    <div style={{ display: "flex", flexDirection: "column", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t2)" }}>Active alerts</span>
        <span style={{ background: "var(--red-dim)", border: "1px solid var(--red-border)", color: "var(--red)", fontSize: 9, fontWeight: 700, padding: "2px 8px", borderRadius: 10 }}>
          {incidents.filter((i) => i.severity === "CRITICAL").length} CRITICAL
        </span>
      </div>

      <div style={{ overflowY: "auto", maxHeight: 250 }}>
        {latest.length === 0 ? (
          <div style={{ textAlign: "center", padding: "30px 0", color: "var(--t3)", fontSize: 12 }}>No active alerts</div>
        ) : (
          latest.map((inc) => {
            const s = SEV_COLORS[inc.severity] || SEV_COLORS.MEDIUM;
            return (
              <div
                key={inc.id}
                style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", borderLeft: `2px solid ${s.left}`, background: s.dim || "transparent" }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 8, fontWeight: 800, letterSpacing: "0.7px", padding: "2px 6px", borderRadius: 3, background: s.bg, color: s.fg, border: `1px solid ${s.border}` }}>
                    {inc.severity}
                  </span>
                  <span className="font-mono" style={{ fontSize: 10, color: "var(--t3)" }}>{formatTime(inc.timestamp)}</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--t1)", lineHeight: 1.4, marginBottom: 5 }}>{inc.summary}</div>
                <div style={{ fontSize: 11, color: "var(--t2)" }}>
                  <b style={{ color: "var(--blue)", fontWeight: 600 }}>Action:</b> {inc.recommended_action}
                </div>
                <div style={{ display: "flex", gap: 6, marginTop: 7 }}>
                  <span style={{ fontSize: 9, color: "var(--t3)", background: "rgba(255,255,255,0.04)", border: "1px solid var(--border2)", padding: "2px 6px", borderRadius: 3 }}>{inc.domain}</span>
                  <span style={{ fontSize: 9, color: "var(--t3)" }}>FP est. {inc.false_positive_pct}%</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
