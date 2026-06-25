import { useState } from "react";

const DOMAINS = [
  { value: "construction", icon: "🏗", label: "Construction" },
  { value: "school", icon: "🏫", label: "School" },
  { value: "elderly", icon: "🏥", label: "Elderly Care" },
  { value: "public", icon: "🌆", label: "Public Space" },
  { value: "__all__", icon: "◈", label: "All Domains" },
];

export default function DomainSelector({ activeDomain, onDomainChange }) {
  const [loading, setLoading] = useState(false);

  async function handleClick(domain) {
    if (domain === activeDomain || loading) return;
    const isAll = domain === "__all__";
    setLoading(true);
    try {
      if (!isAll) {
        await fetch("http://localhost:8000/domain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ domain }),
        });
      }
      onDomainChange(domain);
    } catch (err) {
      console.error("[VigilAI] domain switch failed", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 18px", background: "var(--b1)", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
      <span style={{ fontSize: 10, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.8px", marginRight: 6 }}>Domain</span>
      {DOMAINS.map((d) => {
        const active = d.value === activeDomain;
        return (
          <button
            key={d.value}
            onClick={() => handleClick(d.value)}
            disabled={loading}
            style={{
              padding: "5px 13px",
              borderRadius: 6,
              border: active ? "1px solid rgba(96,165,250,0.4)" : "1px solid var(--border2)",
              background: active ? "rgba(96,165,250,0.1)" : "transparent",
              color: active ? "var(--blue)" : "var(--t3)",
              fontSize: 11,
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
              transition: "all 0.15s",
              opacity: loading ? 0.6 : 1,
            }}
            onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--t2)"; }}
            onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--t3)"; }}
          >
            {d.icon} {d.label}
          </button>
        );
      })}
    </div>
  );
}
