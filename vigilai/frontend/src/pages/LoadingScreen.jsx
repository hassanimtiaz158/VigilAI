const DOMAIN_LABELS = {
  construction: "Construction",
  school: "School",
  elderly: "Elderly Care",
  child: "Child Safety",
  public: "Public Space",
};

export default function LoadingScreen({ domain }) {
  return (
    <div style={{
      minHeight: "100vh",
      background: "#060d18",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "system-ui, sans-serif",
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32 }}>
        <div style={{
          width: 44, height: 44,
          background: "rgba(244,63,63,0.12)",
          border: "1px solid rgba(244,63,63,0.3)",
          borderRadius: 12,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="#f43f3f" strokeWidth={2} strokeLinejoin="round">
            <path d="M12 3L4 7v5c0 4.5 3.3 8.7 8 9.9C17.7 20.7 21 16.5 21 12V7z" />
          </svg>
        </div>
        <span style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.5px", color: "#e2eaf8" }}>
          Vigil<span style={{ color: "#f43f3f" }}>AI</span>
        </span>
      </div>

      {/* Spinning ring */}
      <div style={{
        width: 48, height: 48,
        border: "3px solid #1e2f4a",
        borderTop: "3px solid #60a5fa",
        borderRadius: "50%",
        animation: "spin 1s linear infinite",
        marginBottom: 24,
      }} />

      {/* Text */}
      <div style={{ color: "#8aa0c0", fontSize: 14, textAlign: "center" }}>
        Initializing{" "}
        <span style={{ color: "#60a5fa", fontWeight: 600 }}>
          {DOMAIN_LABELS[domain] || domain}
        </span>
        {" "}monitoring...
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
