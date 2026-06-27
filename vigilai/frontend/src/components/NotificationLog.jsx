import { useEffect, useState } from "react";
import { API_BASE } from "../config";

const TYPE_COLORS = {
  police: { bg: "#1e3a5f", fg: "#60a5fa", border: "#2563eb" },
  emergency: { bg: "#7f1d1d", fg: "#fca5a5", border: "#dc2626" },
  owner: { bg: "#064e3b", fg: "#6ee7b7", border: "#10b981" },
};

const STATUS_STYLES = {
  delivered: { bg: "#065f46", fg: "#34d399", border: "#059669" },
  failed: { bg: "#7f1d1d", fg: "#fca5a5", border: "#dc2626" },
};

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function NotificationLog() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function fetchNotifications() {
      try {
        const res = await fetch(`${API_BASE}/notifications`);
        const data = await res.json();
        if (!cancelled) {
          setNotifications(data.notifications || []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    }
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        maxHeight: 180,
        borderTop: "1px solid var(--border)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "9px 14px",
          borderBottom: "1px solid var(--border)",
          background: "var(--b1)",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.7px",
            color: "var(--t2)",
          }}
        >
          Notification log
        </span>
        <span style={{ fontSize: 10, color: "var(--t3)" }}>
          {notifications.length} sent
        </span>
      </div>

      {/* Column headers */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "70px 80px 100px 80px",
          gap: 8,
          padding: "6px 14px",
          background: "var(--b1)",
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: "0.6px",
          color: "var(--t3)",
          fontWeight: 700,
          position: "sticky",
          top: 0,
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div>Time</div>
        <div>Type</div>
        <div>Sent To</div>
        <div>Status</div>
      </div>

      {/* Rows */}
      <div style={{ overflowY: "auto", flex: 1 }}>
        {loading ? (
          <div
            style={{
              textAlign: "center",
              padding: "16px 0",
              color: "var(--t3)",
              fontSize: 11,
            }}
          >
            Loading...
          </div>
        ) : notifications.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "16px 0",
              color: "var(--t3)",
              fontSize: 11,
            }}
          >
            No notifications sent
          </div>
        ) : (
          notifications.map((n, i) => {
            const tc = TYPE_COLORS[n.type] || TYPE_COLORS.owner;
            const sc = STATUS_STYLES[n.status] || STATUS_STYLES.delivered;
            return (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "70px 80px 100px 80px",
                  gap: 8,
                  padding: "6px 14px",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 11,
                  alignItems: "center",
                }}
                className="hover:bg-white/[0.015]"
              >
                <div className="font-mono" style={{ color: "var(--t3)" }}>
                  {formatTime(n.timestamp)}
                </div>
                <div>
                  <span
                    style={{
                      fontSize: 8,
                      fontWeight: 700,
                      letterSpacing: "0.5px",
                      padding: "2px 6px",
                      borderRadius: 3,
                      background: tc.bg,
                      color: tc.fg,
                      border: `1px solid ${tc.border}`,
                    }}
                  >
                    {n.type.toUpperCase()}
                  </span>
                </div>
                <div style={{ color: "var(--t2)" }} className="truncate">
                  {Array.isArray(n.sent_to) ? n.sent_to.join(", ") : n.sent_to}
                </div>
                <div>
                  <span
                    style={{
                      fontSize: 8,
                      fontWeight: 700,
                      letterSpacing: "0.5px",
                      padding: "2px 6px",
                      borderRadius: 3,
                      background: sc.bg,
                      color: sc.fg,
                      border: `1px solid ${sc.border}`,
                    }}
                  >
                    {n.status}
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
