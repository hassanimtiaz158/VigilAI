"""VigilAI — FastAPI application.

Provides:
  - MJPEG video stream with annotated detections
  - WebSocket push of real-time incidents
  - REST endpoints for health, incidents, and domain switching
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from alert_manager import AlertManager
from detector import SafeWatchDetector
from domain_rules import should_trigger_alert
from models import DomainSwitch
from reasoning import analyze_incident, _reasoning_cache
from video_stream import VideoStream

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
load_dotenv()

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
_WIDTH = 640
_HEIGHT = 360
_FPS_CAP = 30
_FRAME_INTERVAL = 1.0 / _FPS_CAP
_WS_PING_INTERVAL = 15  # seconds
_MAX_LLM_WORKERS = 2
_ALERT_COOLDOWN_SEC = 10  # same alert type can't fire more than once per 10s

# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
detector = SafeWatchDetector()
alert_mgr = AlertManager()

VIDEO_SOURCE = os.getenv(
    "VIDEO_SOURCE",
    str(Path(__file__).parent / "demo" / "samples" / "test.mp4"),
)
video = VideoStream(source=VIDEO_SOURCE)

active_clients: list[WebSocket] = []
incident_log: deque[dict] = deque(maxlen=100)
_llm_pool = ThreadPoolExecutor(max_workers=_MAX_LLM_WORKERS)

# Reference to the running event loop — populated at startup so sync
# generators (video_feed) can schedule async broadcasts from a thread.
_loop: asyncio.AbstractEventLoop | None = None

# --------------------------------------------------------------------------- #
# Alert cooldown tracker (BUG 4)
# --------------------------------------------------------------------------- #
_last_alert: dict[str, datetime] = {}


def _is_cooldown_active(domain: str, label_key: str) -> bool:
    """Return True if the same alert type fired within the cooldown window."""
    key = f"{domain}:{label_key}"
    last = _last_alert.get(key)
    if last and datetime.now() - last < timedelta(seconds=_ALERT_COOLDOWN_SEC):
        return True
    _last_alert[key] = datetime.now()
    return False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def broadcast(incident: dict) -> None:
    """Push an incident JSON to all connected WebSocket clients.

    Removes any client whose send fails (disconnected).
    """
    disconnected: list[WebSocket] = []
    for ws in active_clients:
        try:
            await ws.send_json(incident)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_clients:
            active_clients.remove(ws)


def _build_incident_dict(detections, domain: str, duration: float) -> dict:
    """Run LLM analysis in a thread pool to avoid blocking the MJPEG generator."""
    incident = analyze_incident(detections, domain, duration)
    return incident.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Lifespan
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop
    _loop = asyncio.get_running_loop()
    print(f"[VigilAI] Starting — domain: {detector.active_domain}")
    print(f"[VigilAI] Video source: {VIDEO_SOURCE}")
    yield
    print("[VigilAI] Shutting down — releasing video capture")
    video.release()
    _llm_pool.shutdown(wait=False)


# --------------------------------------------------------------------------- #
# Application & middleware
# --------------------------------------------------------------------------- #
app = FastAPI(title="VigilAI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Exception handlers
# --------------------------------------------------------------------------- #
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Not found"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# --------------------------------------------------------------------------- #
# Routes — REST
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict:
    """Return system status."""
    return {
        "status": "ok",
        "active_domain": detector.active_domain,
        "incidents": len(incident_log),
        "active_clients": len(active_clients),
        "video_source": VIDEO_SOURCE,
    }


@app.get("/incidents")
def get_incidents() -> dict:
    """Return the most recent incidents (up to 100)."""
    return {"incidents": list(incident_log)}


@app.get("/domain")
def get_domain() -> dict:
    """Return the currently active detection domain."""
    return {"active_domain": detector.active_domain}


@app.post("/domain")
def switch_domain(body: DomainSwitch) -> dict:
    """Switch the active detection domain."""
    detector.set_domain(body.domain)
    print(f"[DOMAIN] Switched to: {body.domain}")
    return {"active_domain": body.domain}


@app.post("/monitoring/stop")
def stop_monitoring() -> dict:
    """Release the video capture and stop processing frames."""
    video.release()
    print("[MONITORING] Stopped — video capture released")
    return {"status": "stopped"}


@app.post("/monitoring/start")
def start_monitoring() -> dict:
    """Re-open the video capture to resume processing."""
    global video
    try:
        video = VideoStream(source=VIDEO_SOURCE)
        print(f"[MONITORING] Started — source: {VIDEO_SOURCE}")
        return {"status": "started"}
    except FileNotFoundError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/debug")
def debug() -> dict:
    """Temporary debug endpoint to verify state."""
    return {
        "active_domain": detector.active_domain,
        "cache_size": len(_reasoning_cache),
        "cache_keys": list(_reasoning_cache.keys())[:10],
        "last_alerts": {k: str(v) for k, v in _last_alert.items()},
        "cooldown_active": {
            k: (datetime.now() - v) < timedelta(seconds=_ALERT_COOLDOWN_SEC)
            for k, v in _last_alert.items()
        },
    }


# --------------------------------------------------------------------------- #
# Routes — WebSocket
# --------------------------------------------------------------------------- #
@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """Keep a WebSocket open and push new incidents as they arrive."""
    await websocket.accept()
    active_clients.append(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=_WS_PING_INTERVAL)
            except asyncio.TimeoutError:
                # No message received — send keepalive ping
                try:
                    await websocket.send_text("")
                except Exception:
                    break
    except Exception:
        # Any error means the client is gone
        pass
    finally:
        if websocket in active_clients:
            active_clients.remove(websocket)


# --------------------------------------------------------------------------- #
# Routes — MJPEG video stream
# --------------------------------------------------------------------------- #
@app.get("/video_feed")
def video_feed() -> StreamingResponse:
    """Stream annotated video frames as MJPEG.

    Note: this is a sync generator running in FastAPI's thread pool.
    LLM calls are dispatched to a separate thread pool to avoid blocking
    the frame stream. Broadcasts are fire-and-forget via
    asyncio.run_coroutine_threadsafe.
    """

    def generate():
        while True:
            frame_start = time.monotonic()

            # BUG 1: Read domain per-frame to confirm switch is live
            current_domain = detector.active_domain

            ret, frame = video.read_frame()

            # Loop video when it ends
            if not ret or frame is None:
                video.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = video.read_frame()
                if not ret or frame is None:
                    # Video file missing or unreadable — yield a blank frame
                    import numpy as np
                    frame = np.zeros((_HEIGHT, _WIDTH, 3), dtype=np.uint8)

            # Resize to standard size
            frame = cv2.resize(frame, (_WIDTH, _HEIGHT))

            # Run detection
            annotated, detections = detector.process_frame(frame)

            # BUG 3: Only trigger alert if detections meet domain criteria
            # BUG 4: Apply cooldown to prevent repeated alerts
            if detections and should_trigger_alert(detections, current_domain):
                label_key = ":".join(sorted(d.label for d in detections))

                if not _is_cooldown_active(current_domain, label_key):
                    print(
                        f"[FRAME] Active domain: {current_domain} | "
                        f"Detections: {[d.label for d in detections]} | "
                        f"Alerting..."
                    )
                    # Submit LLM call to thread pool (non-blocking)
                    future = _llm_pool.submit(
                        _build_incident_dict,
                        list(detections),
                        current_domain,
                        1.0,
                    )
                    # Try to get result with timeout to avoid blocking forever
                    try:
                        incident_dict = future.result(timeout=5)
                        incident_log.appendleft(incident_dict)
                        if _loop is not None:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    broadcast(incident_dict), _loop
                                )
                            except RuntimeError:
                                pass  # Loop closed during shutdown
                    except Exception:
                        pass  # LLM timeout or error — skip this incident
                else:
                    pass  # Cooldown active — skip this alert

            # Encode as JPEG
            _, buffer = cv2.imencode(
                ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )

            # Frame rate throttle
            elapsed = time.monotonic() - frame_start
            if elapsed < _FRAME_INTERVAL:
                time.sleep(_FRAME_INTERVAL - elapsed)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
