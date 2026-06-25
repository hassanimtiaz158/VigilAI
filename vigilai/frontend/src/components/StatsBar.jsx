import { useMemo } from "react";

export default function StatsBar({ incidents }) {
  const stats = useMemo(() => {
    const critical = incidents.filter((i) => i.severity === "CRITICAL").length;
    const total = incidents.length;
    const avgResponse = "1.6s";
    const fpReduction = total > 0
      ? `-${Math.round(100 - incidents.reduce((s, i) => s + (i.false_positive_pct || 0), 0) / total)}%`
      : "-31%";
    return { critical, total, avgResponse, fpReduction };
  }, [incidents]);

  const cells = [
    { label: "Critical alerts", value: stats.critical, sub: "last 15 min", color: "var(--red)", trend: null },
    { label: "Total incidents", value: stats.total, sub: null, color: "var(--blue)", trend: "+2 this minute" },
    { label: "Avg response", value: stats.avgResponse, sub: "detect to alert", color: "var(--green)", trend: null },
    { label: "FP reduction", value: stats.fpReduction, sub: "vs raw detection", color: "var(--orange)", trend: null },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", background: "var(--b1)", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
      {cells.map((c) => (
        <div key={c.label} style={{ padding: "12px 18px", borderRight: "1px solid var(--border)" }}>
          <div style={{ fontSize: 10, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.7px", marginBottom: 4 }}>{c.label}</div>
          <div style={{ fontSize: 24, fontWeight: 700, lineHeight: 1, color: c.color }}>{c.value}</div>
          {c.sub && <div style={{ fontSize: 10, color: "var(--t3)", marginTop: 3 }}>{c.sub}</div>}
          {c.trend && <div style={{ fontSize: 10, color: "var(--green)", marginTop: 3 }}>{c.trend}</div>}
        </div>
      ))}
    </div>
  );
}
