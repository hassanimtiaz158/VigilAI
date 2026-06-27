import { useState } from "react";
import { API_BASE } from "../config";

const DOMAIN_ACCENT = {
  construction: "#fb923c",
  school: "#60a5fa",
  elderly: "#a78bfa",
  child: "#34d399",
  public: "#fbbf24",
};

const DOMAINS = [
  { value: "construction", icon: "\uD83C\uDFD7", label: "Construction" },
  { value: "school", icon: "\uD83C\uDFEB", label: "School" },
  { value: "elderly", icon: "\uD83D\uDC74", label: "Elderly Care" },
  { value: "child", icon: "\uD83D\uDC76", label: "Child Safety" },
  { value: "public", icon: "\uD83C\uDF06", label: "Public Space" },
];

export default function DomainSelector({ activeDomain, onDomainChange }) {
  const [loading, setLoading] = useState(false);

  async function handleClick(domain) {
    if (domain === activeDomain || loading) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/domain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain }),
      });
      onDomainChange(domain);
    } catch (err) {
      console.error("[VigilAI] domain switch failed", err);
    } finally {
      setLoading(false);
    }
  }

  const accent = DOMAIN_ACCENT[activeDomain] || "#60a5fa";
  const activeInfo = DOMAINS.find((d) => d.value === activeDomain);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 18px", background: "var(--b1)", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
      {/* Active domain indicator */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "3px 10px", borderRadius: 6,
        background: `${accent}15`,
        border: `1px solid ${accent}40`,
        marginRight: 8,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: accent, display: "inline-block" }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: accent }}>
          {activeInfo ? `${activeInfo.icon} ${activeInfo.label}` : activeDomain}
        </span>
      </div>

      <span style={{ fontSize: 10, color: "var(--t3)", textTransform: "uppercase", letterSpacing: "0.8px", marginRight: 4 }}>Switch</span>
      {DOMAINS.map((d) => {
        const active = d.value === activeDomain;
        const dAccent = DOMAIN_ACCENT[d.value];
        return (
          <button
            key={d.value}
            onClick={() => handleClick(d.value)}
            disabled={loading}
            style={{
              padding: "5px 13px",
              borderRadius: 6,
              border: active ? `1px solid ${dAccent}60` : "1px solid var(--border2)",
              background: active ? `${dAccent}18` : "transparent",
              color: active ? dAccent : "var(--t3)",
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
