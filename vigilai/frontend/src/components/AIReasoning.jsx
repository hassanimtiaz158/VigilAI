export default function AIReasoning({ incident }) {
  return (
    <div style={{ borderTop: "1px solid var(--border)", flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderBottom: "1px solid var(--border)", background: "var(--b0)", flexShrink: 0 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t2)" }}>AI reasoning</span>
        <span style={{ fontSize: 9, color: "var(--t3)" }}>LLaMA 3.3 70B · Groq · 1.4s</span>
      </div>

      {/* Body */}
      <div style={{ padding: "12px 14px", overflowY: "auto", flex: 1 }}>
        {!incident ? (
          <div style={{ textAlign: "center", padding: "20px 0", color: "var(--t3)", fontSize: 11 }}>Awaiting incident data…</div>
        ) : (
          <>
            {/* Detections */}
            <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "10px 12px", marginBottom: 8 }}>
              <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t3)", marginBottom: 4 }}>Detections</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                {incident.detections?.length ? incident.detections.map((d, i) => (
                  <span key={i} style={{
                    fontSize: 9, padding: "2px 7px", borderRadius: 3,
                    background: d.label?.includes("no_") || d.label === "fall_detected" ? "rgba(244,63,63,0.1)" : "rgba(96,165,250,0.1)",
                    border: d.label?.includes("no_") || d.label === "fall_detected" ? "1px solid var(--red-border)" : "1px solid rgba(96,165,250,0.25)",
                    color: d.label?.includes("no_") || d.label === "fall_detected" ? "#f87171" : "var(--blue)",
                  }}>
                    {d.label} {(d.confidence * 100).toFixed(0)}%
                  </span>
                )) : <span style={{ fontSize: 9, color: "var(--t3)" }}>—</span>}
              </div>
            </div>

            {/* Context */}
            <Box label="Context analysis" value={incident.summary || "—"} />

            {/* Severity */}
            <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "10px 12px", marginBottom: 8 }}>
              <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t3)", marginBottom: 4 }}>Severity</div>
              <div style={{
                fontSize: 14, fontWeight: 700,
                color: incident.severity === "CRITICAL" ? "var(--red)" :
                       incident.severity === "HIGH" ? "var(--orange)" :
                       incident.severity === "MEDIUM" ? "var(--yellow)" : "var(--green)",
              }}>
                {incident.severity}
              </div>
            </div>

            {/* Action */}
            <Box label="Recommended action" value={incident.recommended_action || "—"} />

            {/* FP */}
            <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "10px 12px", marginBottom: 8 }}>
              <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t3)", marginBottom: 4 }}>False positive likelihood</div>
              <div style={{ fontSize: 11, color: "var(--t1)", lineHeight: 1.5 }}>
                {incident.false_positive_pct}% <span style={{ color: "var(--t3)", fontSize: 10 }}>— {incident.false_positive_pct <= 10 ? "high confidence" : "moderate"}</span>
              </div>
              <div style={{ height: 3, background: "var(--border2)", borderRadius: 2, marginTop: 7, overflow: "hidden" }}>
                <div style={{ height: "100%", borderRadius: 2, width: `${100 - (incident.false_positive_pct || 0)}%`, background: "var(--green)", transition: "width 0.5s" }} />
              </div>
            </div>

            {/* Status */}
            <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "10px 12px", marginBottom: 8 }}>
              <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t3)", marginBottom: 4 }}>Status</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--blue)", animation: "aidot 1.2s infinite", display: "inline-block" }} />
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--blue)", animation: "aidot 1.2s infinite 0.2s", display: "inline-block" }} />
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--blue)", animation: "aidot 1.2s infinite 0.4s", display: "inline-block" }} />
                </div>
                <span style={{ fontSize: 11, color: "var(--green)", fontWeight: 600 }}>Monitoring active</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Box({ label, value }) {
  return (
    <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "10px 12px", marginBottom: 8 }}>
      <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.7px", color: "var(--t3)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 11, color: "var(--t1)", lineHeight: 1.5 }}>{value}</div>
    </div>
  );
}
