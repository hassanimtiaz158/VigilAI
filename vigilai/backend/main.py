"""VigilAI — FastAPI application.

Provides:
  - MJPEG video stream with annotated detections
  - WebSocket push of real-time incidents
  - REST endpoints for health, incidents, and domain switching
"""

from __future__ import annotations

import asyncio
import os
from collections import deque

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from alert_manager import AlertManager
from detector import SafeWatchDetector
from models import DomainSwitch
from reasoning import analyze_incident
from video_stream import VideoStream

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
load_dotenv()

# --------------------------------------------------------------------------- #
# Application & middleware
# --------------------------------------------------------------------------- #
app = FastAPI(title="VigilAI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
detector = SafeWatchDetector()
alert_mgr = AlertManager()

VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "demo/samples/test.mp4")
video = VideoStream(source=VIDEO_SOURCE)

active_clients: list[WebSocket] = []
incident_log: deque[dict] = deque(maxlen=100)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
_WIDTH = 640
_HEIGHT = 360

# Reference to the running event loop — populated at startup so sync
# generators (video_feed) can schedule async broadcasts from a thread.
_loop: asyncio.AbstractEventLoop | None = None


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
        active_clients.remove(ws)


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


@app.post("/domain")
def switch_domain(body: DomainSwitch) -> dict:
    """Switch the active detection domain."""
    detector.set_domain(body.domain)
    return {"active_domain": body.domain}


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
            # Keep the connection alive; actual pushes happen via broadcast()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_clients.remove(websocket)


# --------------------------------------------------------------------------- #
# Routes — MJPEG video stream
# --------------------------------------------------------------------------- #
@app.get("/video_feed")
def video_feed() -> StreamingResponse:
    """Stream annotated video frames as MJPEG.

    Note: this is a sync generator. Broadcasts are fire-and-forget via
    asyncio.run_coroutine_threadsafe because the generator runs inside
    FastAPI's thread pool, not on the event loop directly.
    """

    def generate():
        import numpy as np

        while True:
            ret, frame = video.read_frame()

            # Loop video when it ends
            if not ret or frame is None:
                video.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = video.read_frame()
                if not ret or frame is None:
                    # Video file missing or unreadable — yield a blank frame
                    frame = np.zeros((_HEIGHT, _WIDTH, 3), dtype=np.uint8)

            # Resize to standard size
            frame = cv2.resize(frame, (_WIDTH, _HEIGHT))

            # Run detection
            annotated, detections = detector.process_frame(frame)

            # On detections: reason + log + broadcast
            if detections:
                incident = analyze_incident(
                    detections, detector.active_domain, 1.0
                )
                incident_dict = incident.model_dump(mode="json")
                incident_log.appendleft(incident_dict)

                # Schedule broadcast on the event loop (thread-safe)
                if _loop is not None:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            broadcast(incident_dict), _loop
                        )
                    except RuntimeError:
                        pass  # Loop closed during shutdown

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

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# --------------------------------------------------------------------------- #
# Startup / shutdown
# --------------------------------------------------------------------------- #
@app.on_event("startup")
async def startup_event() -> None:
    global _loop
    _loop = asyncio.get_running_loop()
    print(f"[VigilAI] Starting — domain: {detector.active_domain}")
    print(f"[VigilAI] Video source: {VIDEO_SOURCE}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    print("[VigilAI] Shutting down — releasing video capture")
    video.release()
