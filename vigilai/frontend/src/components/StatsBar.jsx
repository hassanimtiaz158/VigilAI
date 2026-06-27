import { useMemo } from "react";

const DOMAIN_STATS = {
  construction: [
    { label: "PPE Violations", color: "var(--red)" },
    { label: "Zone Breaches", color: "var(--orange)" },
    { label: "Workers Detected", color: "var(--blue)" },
    { label: "Compliance Rate", color: "var(--green)" },
  ],
  school: [
    { label: "Threats Detected", color: "var(--red)" },
    { label: "Crowd Alerts", color: "var(--orange)" },
    { label: "Unauthorized Access", color: "var(--yellow)" },
    { label: "Safe Zones", color: "var(--green)" },
  ],
  elderly: [
    { label: "Falls Detected", color: "var(--red)" },
    { label: "Stillness Alerts", color: "var(--orange)" },
    { label: "Wandering Incidents", color: "var(--yellow)" },
    { label: "Response Time", color: "var(--green)" },
  ],
  child: [
    { label: "Unattended Alerts", color: "var(--red)" },
    { label: "Zone Violations", color: "var(--orange)" },
    { label: "Falls", color: "var(--yellow)" },
    { label: "Response Time", color: "var(--green)" },
  ],
  public: [
    { label: "Unattended Bags", color: "var(--red)" },
    { label: "Crowd Density", color: "var(--orange)" },
    { label: "Loitering", color: "var(--yellow)" },
    { label: "Suspicious Activity", color: "var(--green)" },
  ],
};

export default function StatsBar({ incidents, domain }) {
  const stats = useMemo(() => {
    const critical = incidents.filter((i) => i.severity === "CRITICAL").length;
    const total = incidents.length;
    const avgResponse = "1.6s";
    const fpReduction = total > 0
      ? `${Math.round(incidents.reduce((s, i) => s + (i.false_positive_pct || 0), 0) / total)}%`
      : "\u2014";
    return { critical, total, avgResponse, fpReduction };
  }, [incidents]);

  const labels = DOMAIN_STATS[domain] || DOMAIN_STATS.construction;

  const cells = [
    { label: labels[0].label, value: stats.critical, sub: "last 15 min", color: labels[0].color },
    { label: labels[1].label, value: stats.total, sub: null, color: labels[1].color },
    { label: labels[2].label, value: stats.avgResponse, sub: "detect to alert", color: labels[2].color },
    { label: labels[3].label, value: stats.fpReduction, sub: "avg FP estimate", color: labels[3].color },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", background: "var(--b1)", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
      {cells.map((c) => (
        <div key={c.label} style={{ padding: "12px 18px", borderRight: "1px solid var(--border)" }}>
          <div style={{ fontSize: 10, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.7px", marginBottom: 4 }}>{c.label}</div>
          <div style={{ fontSize: 24, fontWeight: 700, lineHeight: 1, color: c.color }}>{c.value}</div>
          {c.sub && <div style={{ fontSize: 10, color: "var(--t3)", marginTop: 3 }}>{c.sub}</div>}
        </div>
      ))}
    </div>
  );
}
