import { useEffect, useRef, useState } from "react";

const MAX_INCIDENTS = 50;

/**
 * Connect to the VigilAI WebSocket stream and accumulate incidents.
 *
 * @param {string} url - e.g. "ws://localhost:8000/stream"
 * @returns {Incident[]} latest incidents (newest first, max 50)
 */
export function useWebSocket(url) {
  const [incidents, setIncidents] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[VigilAI] WebSocket connected");
      };

      ws.onmessage = (event) => {
        try {
          const incident = JSON.parse(event.data);
          setIncidents((prev) => {
            const next = [incident, ...prev];
            return next.slice(0, MAX_INCIDENTS);
          });
        } catch {
          // Non-JSON frame - ignore
        }
      };

      ws.onerror = (err) => {
        console.warn("[VigilAI] WebSocket error", err);
      };

      ws.onclose = () => {
        console.log("[VigilAI] WebSocket closed");
        if (!cancelled) {
          setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [url]);

  return incidents;
}
