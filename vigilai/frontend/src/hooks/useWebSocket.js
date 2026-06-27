import { useEffect, useRef, useState } from "react";

const MAX_INCIDENTS = 50;
const RECONNECT_DELAY_MS = 3000;
const PING_INTERVAL_MS = 25000;

function playCriticalBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    osc.frequency.value = 880;
    osc.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  } catch {
    // AudioContext unavailable — silent fallback
  }
}

/**
 * Connect to the VigilAI WebSocket stream and accumulate incidents.
 *
 * @param {string} url - e.g. "ws://localhost:8000/stream"
 * @returns {{ incidents: Incident[], connected: boolean, latestCritical: Incident|null }}
 */
export function useWebSocket(url) {
  const [incidents, setIncidents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [latestCritical, setLatestCritical] = useState(null);
  const wsRef = useRef(null);
  const pingRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[VigilAI] WebSocket connected");
        setConnected(true);

        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("");
          }
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (event) => {
        try {
          const incident = JSON.parse(event.data);

          // Play beep on CRITICAL
          if (incident.severity === "CRITICAL") {
            playCriticalBeep();
            setLatestCritical(incident);
          }

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
        setConnected(false);
        if (pingRef.current) {
          clearInterval(pingRef.current);
          pingRef.current = null;
        }
        if (!cancelled) {
          setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (pingRef.current) {
        clearInterval(pingRef.current);
      }
      wsRef.current?.close();
    };
  }, [url]);

  return { incidents, connected, latestCritical };
}
