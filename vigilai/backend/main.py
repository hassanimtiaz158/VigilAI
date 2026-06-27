"""VigilAI — FastAPI application.

Provides:
  - MJPEG video stream with annotated detections
  - WebSocket push of real-time incidents
  - REST endpoints for health, incidents, domain switching, and alerts
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
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

from activity_tracker import FightDetector, LoiteringTracker, UnattendedBagTracker
from alert_manager import AlertManager
from alert_sender import AlertSender
from detector import SafeWatchDetector
from domain_rules import should_trigger_alert
from models import DomainSwitch, TestAlertBody
from reasoning import analyze_incident, _reasoning_cache
from suspicious_rules import SUSPICIOUS_ACTIVITIES
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
alert_sender = AlertSender()

# Activity trackers
loitering_tracker = LoiteringTracker()
fight_detector = FightDetector()
bag_tracker = UnattendedBagTracker()

VIDEO_SOURCE = os.getenv(
    "VIDEO_SOURCE",
    str(Path(__file__).parent / "demo" / "samples" / "test.mp4"),
)
video = VideoStream(source=VIDEO_SOURCE)

active_clients: list[WebSocket] = []
incident_log: deque[dict] = deque(maxlen=100)
notification_log: deque[dict] = deque(maxlen=200)
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
# Notification log helpers
# --------------------------------------------------------------------------- #
def _record_notification(
    activity_type: str,
    severity: str,
    sent_to: list[str],
    channels: list[str],
    status: str,
    error_message: str | None = None,
) -> None:
    """Append a structured entry to notification_log."""
    notification_log.appendleft({
        "id": uuid.uuid4().hex[:12],
        "timestamp": time.time(),
        "activity_type": activity_type,
        "severity": severity,
        "sent_to": sent_to,
        "channels": channels,
        "status": status,
        "error_message": error_message,
    })


def _record_alert_result(
    activity_type: str,
    severity: str,
    recipient: str,
    result: dict,
) -> None:
    """Record a single alert sender result into notification_log."""
    channels: list[str] = []
    if result.get("email_ok"):
        channels.append("email")
    if result.get("sms_ok"):
        channels.append("sms")

    ok = result.get("email_ok", False) or result.get("sms_ok", False)
    error = result.get("error")

    _record_notification(
        activity_type=activity_type,
        severity=severity,
        sent_to=[recipient],
        channels=channels,
        status="delivered" if ok else "failed",
        error_message=error,
    )


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

    # Startup checks for alerting configuration
    if not os.getenv("GMAIL_USER"):
        print("[VigilAI] WARNING: GMAIL_USER not set — email alerts disabled")
    if not os.getenv("TWILIO_ACCOUNT_SID"):
        print("[VigilAI] WARNING: TWILIO_ACCOUNT_SID not set — SMS alerts disabled")

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
        "notifications": len(notification_log),
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


@app.get("/suspicious-only")
def suspicious_only() -> dict:
    """Return whether the system is in suspicious-only alert mode."""
    return {"mode": "suspicious_only", "normal_ignored": True}


@app.get("/notifications")
def get_notifications() -> dict:
    """Return the last 100 notification log entries."""
    return {"notifications": list(notification_log)[:100]}


@app.post("/test-alert")
def test_alert(body: TestAlertBody) -> dict:
    """Send a test email + SMS to the owner only.

    Used to verify that the alerting pipeline is working.
    """
    result = alert_sender.test_owner(body.message)

    _record_notification(
        activity_type="test",
        severity="LOW",
        sent_to=["owner"],
        channels=(
            (["email"] if result["email_sent"] else [])
            + (["sms"] if result["sms_sent"] else [])
        ),
        status="delivered" if (result["email_sent"] or result["sms_sent"]) else "failed",
        error_message=None if (result["email_sent"] or result["sms_sent"]) else "Both channels failed",
    )

    return result


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

            # --- Update activity trackers with current frame data ---
            now = time.time()
            person_dets = [d for d in detections if d.label == "person"]
            bag_labels = {"backpack", "suitcase", "handbag"}
            bag_dets = [d for d in detections if d.label in bag_labels]

            # Update loitering tracker for each person
            for i, det in enumerate(person_dets):
                loitering_tracker.update(f"person_{i}", det.bbox, now)

            # Update fight detector
            fight_detector.update(person_dets)

            # Update bag tracker
            person_bboxes = [d.bbox for d in person_dets]
            for bag_det in bag_dets:
                bag_tracker.update(bag_det.bbox, person_bboxes, now)

            # --- Check temporal suspicious conditions ---
            temporal_activity = None
            temporal_message = None

            # Check loitering (person stationary > 300s)
            for i, det in enumerate(person_dets):
                if loitering_tracker.is_loitering(f"person_{i}"):
                    temporal_activity = "loitering"
                    temporal_message = SUSPICIOUS_ACTIVITIES["loitering"]["message"]
                    break

            # Check fight (2+ persons in proximity for 3+ frames)
            if temporal_activity is None and fight_detector.is_fight():
                temporal_activity = "fight"
                temporal_message = SUSPICIOUS_ACTIVITIES["fight"]["message"]

            # Check unattended bag (> 120s with no person nearby)
            if temporal_activity is None and bag_dets:
                for bag_det in bag_dets:
                    bag_id = bag_tracker._bbox_to_id(bag_det.bbox)
                    if bag_tracker.is_unattended(bag_id):
                        temporal_activity = "unattended_bag"
                        temporal_message = SUSPICIOUS_ACTIVITIES["unattended_bag"]["message"]
                        break

            # --- Combine frame-based + temporal suspicious checks ---
            is_suspicious, activity_type, alert_message = detector.is_suspicious(
                detections, frame
            )

            # Temporal checks override if frame-based didn't fire
            if not is_suspicious and temporal_activity:
                is_suspicious = True
                activity_type = temporal_activity
                alert_message = temporal_message

            if not is_suspicious:
                pass  # Normal detections — skip entirely
            else:
                # Capture alert screenshot BEFORE LLM call
                image_bytes = detector.capture_alert_frame(
                    frame, detections, activity_type
                )

                # Cooldown check via LoiteringTracker
                if not loitering_tracker.is_cooldown_active(
                    activity_type, current_domain
                ):
                    print(
                        f"[FRAME] SUSPICIOUS: {activity_type} | "
                        f"Domain: {current_domain} | "
                        f"Detections: {[d.label for d in detections]}"
                    )

                    # LLM analysis (non-blocking)
                    future = _llm_pool.submit(
                        _build_incident_dict,
                        list(detections),
                        current_domain,
                        1.0,
                    )
                    try:
                        incident_dict = future.result(timeout=5)
                        incident_dict["activity_type"] = activity_type
                        incident_dict["alert_message"] = alert_message
                        incident_dict["image_bytes"] = image_bytes
                        incident_log.appendleft(incident_dict)

                        # WebSocket broadcast (strip non-serializable fields)
                        ws_payload = {k: v for k, v in incident_dict.items() if k != "image_bytes"}
                        if _loop is not None:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    broadcast(ws_payload), _loop
                                )
                            except RuntimeError:
                                pass

                        # --- Send alerts ----------------------------------
                        severity = incident_dict.get("severity", "MEDIUM")
                        location = current_domain

                        # Always alert owner
                        owner_result = alert_sender.alert_owner(
                            activity_type, severity, alert_message,
                        )
                        _record_alert_result(
                            activity_type, severity, "owner", owner_result,
                        )

                        # CRITICAL → alert police
                        if severity == "CRITICAL":
                            police_result = alert_sender.alert_police(
                                activity_type, severity, location, image_bytes,
                            )
                            _record_alert_result(
                                activity_type, severity, "police", police_result,
                            )

                        # Fall → alert emergency
                        if activity_type == "fall":
                            emergency_result = alert_sender.alert_emergency(
                                activity_type, location, image_bytes,
                            )
                            _record_alert_result(
                                activity_type, severity, "emergency", emergency_result,
                            )

                        # Set cooldown
                        loitering_tracker.set_cooldown(activity_type, current_domain)

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
