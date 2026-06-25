# Technical Design Document (TDD)
## SafeWatch AI — Intelligent Multi-Domain Safety Platform
**Version:** 1.0  
**Author:** Hasan Ali (Malik)  
**Stack:** Python 3.11 · FastAPI · YOLOv8 · MediaPipe · Groq LLaMA 3 · React 18 · Tailwind CSS  

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VIDEO INPUT LAYER                        │
│          [.mp4 file / webcam / RTSP stream via OpenCV]          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Raw frames (numpy arrays)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INFERENCE ENGINE                            │
│   YOLOv8n (object detection) + MediaPipe Pose (fall/posture)   │
│   Domain Rule Filter → filters detections by active domain     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Filtered detection events
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM REASONING LAYER                           │
│        Groq API → LLaMA 3.3 70B (free, ~400ms latency)        │
│   Input: domain + detections + duration + zone                 │
│   Output: severity + summary + action + false_positive_%       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Structured incident JSON
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                              │
│   WebSocket /stream → pushes incidents to frontend in real-time│
│   REST /incidents → paginated incident log                     │
│   REST /domain → switch active detection domain                │
│   MJPEG /video_feed → annotated frame stream for UI            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  REACT + TAILWIND DASHBOARD                     │
│   LiveFeed · AlertPanel · IncidentLog · DomainSelector         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Project Structure

```
safewatch-ai/
├── backend/
│   ├── main.py                  # FastAPI app, routes, WebSocket
│   ├── detector.py              # CV inference engine (YOLO + MediaPipe)
│   ├── reasoning.py             # Groq LLM context analysis
│   ├── alert_manager.py         # Severity scoring, deduplication
│   ├── domain_rules.py          # Per-domain detection thresholds
│   ├── video_stream.py          # OpenCV capture + frame generator
│   ├── models.py                # Pydantic schemas
│   ├── requirements.txt
│   └── .env                     # GROQ_API_KEY
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── LiveFeed.jsx
│   │   │   ├── AlertPanel.jsx
│   │   │   ├── IncidentLog.jsx
│   │   │   ├── DomainSelector.jsx
│   │   │   └── StatsBar.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── demo/
│   └── samples/                 # .mp4 test videos per domain
└── README.md
```

---

## 3. Backend Implementation

### 3.1 Dependencies (`requirements.txt`)
```
fastapi==0.111.0
uvicorn==0.29.0
opencv-python==4.9.0.80
ultralytics==8.2.0
mediapipe==0.10.14
groq==0.9.0
python-dotenv==1.0.1
pydantic==2.7.0
numpy==1.26.4
```

### 3.2 Pydantic Models (`models.py`)
```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class Detection(BaseModel):
    label: str
    confidence: float
    bbox: list[int]           # [x1, y1, x2, y2]
    zone: str                 # "entrance", "floor", "machinery_zone"

class Incident(BaseModel):
    id: str
    timestamp: datetime
    domain: str
    detections: list[Detection]
    duration_sec: float
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    summary: str
    recommended_action: str
    false_positive_pct: int

class DomainSwitch(BaseModel):
    domain: Literal["school", "elderly", "construction", "public"]
```

### 3.3 Domain Rules (`domain_rules.py`)
```python
DOMAIN_RULES = {
    "school": {
        "target_labels": ["knife", "scissors", "person"],
        "forbidden_labels": ["knife", "scissors"],
        "confidence_threshold": 0.50,
        "pose_checks": ["running"],
        "zone_map": {"entrance": "high_risk", "cafeteria": "medium_risk"},
    },
    "elderly": {
        "target_labels": ["person"],
        "confidence_threshold": 0.60,
        "pose_checks": ["fall", "prolonged_stillness"],
        "stillness_threshold_sec": 30,
        "zone_map": {"floor": "critical", "bed": "low"},
    },
    "construction": {
        "target_labels": ["person", "helmet", "safety vest"],
        "missing_ppe_trigger": True,
        "confidence_threshold": 0.55,
        "proximity_zone": "machinery_zone",
        "zone_map": {"machinery_zone": "critical", "walkway": "medium"},
    },
    "public": {
        "target_labels": ["suitcase", "backpack", "handbag", "person"],
        "unattended_bag_threshold_sec": 300,
        "confidence_threshold": 0.50,
        "zone_map": {"transit_hub": "high_risk", "open_space": "medium"},
    },
}
```

### 3.4 Inference Engine (`detector.py`)
```python
import cv2
import mediapipe as mp
import numpy as np
from ultralytics import YOLO
from domain_rules import DOMAIN_RULES
from models import Detection

class SafeWatchDetector:
    def __init__(self):
        self.yolo = YOLO("yolov8n.pt")
        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )
        self.active_domain = "school"
        self.frame_count = 0

    def set_domain(self, domain: str):
        self.active_domain = domain

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]:
        self.frame_count += 1
        # Process every 3rd frame to reduce CPU load
        if self.frame_count % 3 != 0:
            return frame, []

        rules = DOMAIN_RULES[self.active_domain]
        detections = []

        # --- YOLO Object Detection ---
        results = self.yolo(frame, verbose=False, conf=rules["confidence_threshold"])
        for result in results:
            for box in result.boxes:
                label = self.yolo.names[int(box.cls[0])]
                if label not in rules["target_labels"]:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(Detection(
                    label=label, confidence=conf,
                    bbox=[x1, y1, x2, y2], zone=self._get_zone(x1, y1, frame)
                ))
                # Draw bounding box on frame
                color = (0, 0, 255) if label in rules.get("forbidden_labels", []) else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # --- Pose Estimation (Elderly + School) ---
        if self.active_domain in ["elderly", "school"]:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pose_result = self.pose.process(rgb)
            if pose_result.pose_landmarks:
                fall = self._check_fall(pose_result.pose_landmarks)
                if fall:
                    detections.append(Detection(
                        label="fall_detected", confidence=0.85,
                        bbox=[0, 0, frame.shape[1], frame.shape[0]],
                        zone="floor"
                    ))

        return frame, detections

    def _get_zone(self, x: int, y: int, frame: np.ndarray) -> str:
        h, w = frame.shape[:2]
        # Simple zone mapping based on frame quadrant
        if y < h * 0.3:
            return "entrance"
        elif y > h * 0.7:
            return "floor"
        return "open_area"

    def _check_fall(self, landmarks) -> bool:
        # Check if nose landmark is below hip level → indicates fall
        nose_y = landmarks.landmark[0].y
        left_hip_y = landmarks.landmark[23].y
        right_hip_y = landmarks.landmark[24].y
        avg_hip_y = (left_hip_y + right_hip_y) / 2
        return nose_y > avg_hip_y  # nose below hips = likely fallen
```

### 3.5 LLM Reasoning (`reasoning.py`)
```python
import json
from groq import Groq
from models import Detection, Incident
from datetime import datetime
import uuid
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Cache to avoid calling LLM for duplicate detection patterns
_reasoning_cache: dict[str, dict] = {}

def analyze_incident(
    detections: list[Detection],
    domain: str,
    duration_sec: float
) -> Incident:
    cache_key = f"{domain}:{sorted([d.label for d in detections])}:{int(duration_sec/10)*10}"
    
    if cache_key in _reasoning_cache:
        cached = _reasoning_cache[cache_key]
    else:
        detection_summary = [
            {"object": d.label, "confidence": f"{d.confidence:.2f}", "zone": d.zone}
            for d in detections
        ]
        prompt = f"""You are an AI safety analyst. Analyze this incident and respond ONLY with valid JSON.

Domain: {domain}
Detections: {json.dumps(detection_summary)}
Duration: {duration_sec:.1f} seconds

Return exactly this JSON structure:
{{
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "summary": "one sentence describing what is happening",
  "recommended_action": "one sentence describing what should be done",
  "false_positive_pct": integer 0-100
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        cached = json.loads(response.choices[0].message.content)
        _reasoning_cache[cache_key] = cached

    return Incident(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(),
        domain=domain,
        detections=detections,
        duration_sec=duration_sec,
        severity=cached["severity"],
        summary=cached["summary"],
        recommended_action=cached["recommended_action"],
        false_positive_pct=cached["false_positive_pct"],
    )
```

### 3.6 FastAPI App (`main.py`)
```python
import asyncio, cv2, base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from detector import SafeWatchDetector
from reasoning import analyze_incident
from models import DomainSwitch, Incident
from collections import deque
import numpy as np

app = FastAPI(title="SafeWatch AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

detector = SafeWatchDetector()
incident_log: deque[dict] = deque(maxlen=100)
active_clients: list[WebSocket] = []
VIDEO_SOURCE = "demo/samples/construction.mp4"  # swap per domain

cap = cv2.VideoCapture(VIDEO_SOURCE)

async def broadcast(incident: dict):
    for ws in active_clients.copy():
        try:
            await ws.send_json(incident)
        except:
            active_clients.remove(ws)

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    active_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # keep connection alive
    except WebSocketDisconnect:
        active_clients.remove(websocket)

@app.get("/video_feed")
def video_feed():
    def generate():
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            frame = cv2.resize(frame, (640, 360))
            annotated, detections = detector.process_frame(frame)
            if detections:
                incident = analyze_incident(detections, detector.active_domain, 1.0)
                incident_log.appendleft(incident.model_dump())
                asyncio.run(broadcast(incident.model_dump()))
            _, buffer = cv2.imencode(".jpg", annotated)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                   buffer.tobytes() + b"\r\n")
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")

@app.get("/incidents")
def get_incidents():
    return {"incidents": list(incident_log)}

@app.post("/domain")
def switch_domain(body: DomainSwitch):
    detector.set_domain(body.domain)
    return {"active_domain": body.domain}

@app.get("/health")
def health():
    return {"status": "ok", "domain": detector.active_domain, "incidents": len(incident_log)}
```

---

## 4. Frontend Implementation

### 4.1 Dependencies (`package.json` key deps)
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "axios": "^1.7.0",
    "lucide-react": "^0.383.0"
  },
  "devDependencies": {
    "vite": "^5.2.0",
    "@vitejs/plugin-react": "^4.3.0"
  }
}
```

### 4.2 WebSocket Hook (`useWebSocket.js`)
```javascript
import { useEffect, useState, useRef } from "react";

export function useWebSocket(url) {
  const [incidents, setIncidents] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket(url);
    ws.current.onmessage = (e) => {
      const incident = JSON.parse(e.data);
      setIncidents(prev => [incident, ...prev].slice(0, 50));
    };
    return () => ws.current?.close();
  }, [url]);

  return incidents;
}
```

### 4.3 Severity Color System
```javascript
export const SEVERITY_STYLES = {
  CRITICAL: { bg: "bg-red-900/40",    border: "border-red-500",   text: "text-red-400",   badge: "bg-red-600" },
  HIGH:     { bg: "bg-orange-900/30", border: "border-orange-500", text: "text-orange-400", badge: "bg-orange-600" },
  MEDIUM:   { bg: "bg-yellow-900/30", border: "border-yellow-500", text: "text-yellow-400", badge: "bg-yellow-600" },
  LOW:      { bg: "bg-green-900/20",  border: "border-green-600",  text: "text-green-400",  badge: "bg-green-700" },
};
```

---

## 5. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System status + active domain |
| `GET` | `/video_feed` | MJPEG annotated video stream |
| `GET` | `/incidents` | Last 100 incidents (JSON) |
| `POST` | `/domain` | Switch active detection domain |
| `WS` | `/stream` | Real-time incident WebSocket push |

---

## 6. Deployment

### Backend (Railway — free tier)
```bash
# Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend (Vercel)
```bash
npm run build
vercel --prod
```

### Environment Variables
```env
GROQ_API_KEY=your_groq_key_here
VIDEO_SOURCE=demo/samples/construction.mp4
```

---

## 7. Performance Optimizations

| Optimization | Implementation |
|---|---|
| Frame skipping | Process every 3rd frame only |
| LLM caching | Cache reasoning results by detection pattern |
| YOLOv8 nano | Use `yolov8n.pt` (smallest, fastest model) |
| Async WebSocket | Non-blocking broadcast via asyncio |
| MJPEG streaming | No heavy WebRTC setup needed |
| Deque incident log | Fixed-size in-memory store (no DB needed for hackathon) |
