import { API_BASE } from "../config";

const DOMAIN_LABELS = {
  construction: "CAM-02 · CONSTRUCTION SITE · ZONE A",
  school: "CAM-01 · SCHOOL · MAIN ENTRANCE",
  elderly: "CAM-04 · CARE FACILITY · ROOM 12",
  public: "CAM-07 · TRANSIT HUB · GATE B",
  __all__: "MULTI-CAM · ALL DOMAINS ACTIVE",
};

const BADGE_LABELS = {
  construction: "CONSTRUCTION",
  school: "SCHOOL",
  elderly: "ELDERLY CARE",
  public: "PUBLIC SPACE",
  __all__: "ALL DOMAINS",
};

export default function LiveFeed({ domain }) {
  return (
    <div style={{ background: "#000", position: "relative", overflow: "hidden", flex: "0 0 290px" }}>
      <div style={{ position: "absolute", inset: 0, background: "var(--b0)" }} />
      <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(96,165,250,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(96,165,250,0.025) 1px, transparent 1px)", backgroundSize: "36px 36px" }} />
      <div style={{ position: "absolute", left: 0, right: 0, height: 1, background: "rgba(96,165,250,0.08)", animation: "scan 5s linear infinite" }} />

      <img
        src={`${API_BASE}/video_feed`}
        alt="Live camera feed"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "slice" }}
      />

      <div style={{ position: "absolute", top: 0, left: 0, right: 0, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "linear-gradient(rgba(6,13,24,0.8), transparent)" }}>
        <span style={{ fontSize: 10, color: "rgba(255,255,255,0.5)" }}>{DOMAIN_LABELS[domain] || DOMAIN_LABELS.construction}</span>
        <span className="font-mono" style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>29.97 FPS</span>
      </div>

      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", background: "linear-gradient(transparent, rgba(6,13,24,0.8))" }}>
        <span style={{ background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)", color: "var(--blue)", fontSize: 9, fontWeight: 700, letterSpacing: "0.6px", padding: "3px 8px", borderRadius: 4 }}>
          {BADGE_LABELS[domain] || BADGE_LABELS.construction}
        </span>
        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.25)" }}>
          YOLOv8n + MediaPipe + Groq LLaMA 3.3
        </span>
      </div>
    </div>
  );
}
