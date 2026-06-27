export const SEV_COLORS = {
  CRITICAL: {
    bg: "rgba(244,63,63,0.2)",
    fg: "#f87171",
    border: "var(--red-border)",
    left: "var(--red)",
    dim: "var(--red-dim)",
  },
  HIGH: {
    bg: "rgba(251,146,60,0.18)",
    fg: "#fb923c",
    border: "var(--orange-border)",
    left: "var(--orange)",
    dim: "var(--orange-dim)",
  },
  MEDIUM: {
    bg: "rgba(251,191,36,0.16)",
    fg: "#fbbf24",
    border: "var(--yellow-border)",
    left: "var(--yellow)",
    dim: "var(--yellow-dim)",
  },
  LOW: {
    bg: "rgba(52,211,153,0.12)",
    fg: "#34d399",
    border: "var(--green-border)",
    left: "var(--green)",
    dim: null,
  },
};

export function getSevColor(severity) {
  return SEV_COLORS[severity] || SEV_COLORS.MEDIUM;
}
