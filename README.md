```
  ╦  ╦╔═╗╦  ╦╦╦   ╔═╗╦
  ╚╗╔╝║ ╦║  ║║║   ╠═╣║
   ╚╝ ╚═╝╩═╝╩╩╩═╝ ╩ ╩╩
   The safety camera that understands.
```

---

**Python 3.11** | **FastAPI** | **YOLOv8** | **Groq LLaMA 3.3** | **React 18** | **FutureHacks 2026**

---

## The Problem

- **Dumb cameras flood operators with false alerts.** Motion-triggered systems can't distinguish a falling senior from a dropped backpack — fatigue sets in, real events get ignored.
- **Generic object detection lacks situational context.** A knife in a school is a threat; a knife in a kitchen is not. Same object, completely different risk profile — traditional CV doesn't know the difference.
- **Response latency costs lives.** Even when a human spots a critical incident on a monitor, the chain of "observe → comprehend → decide → act" takes minutes. In elderly falls or active-threat scenarios, seconds matter.

## The Solution

VigilAI is not another motion detector. It's a **context-aware safety intelligence layer** that sits between your existing cameras and your response team.

Where YOLO sees "person on floor," VigilAI reasons: *"Elderly care domain, no motion for 30s, nose below hip line — this is a fall. Alert nursing staff now."*

A **domain-aware LLM reasoning engine** interprets raw detections through the lens of the active environment, producing structured incidents with severity, human-readable summaries, and recommended actions — not just bounding boxes.

## Features

### School / Campus
Detects weapons (knives, scissors), monitors running behavior, and flags zone violations at entrances. Forbidden labels trigger immediate high-severity alerts.

### Elderly Care
Runs pose-based fall detection (nose-below-hip heuristic via MediaPipe) and prolonged-stillness monitoring. Customizable stillness thresholds for bed vs. hallway zones.

### Construction Site
PPE compliance tracking (missing helmet/vest), proximity-to-machinery alerts, and zone-based risk scoring. Missing PPE triggers instant critical incidents.

### Public Space
Unattended-bag detection with configurable time thresholds, transit-hub zone monitoring, and multi-object risk correlation (person + suitcase + platform = high risk).

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Framework | FastAPI + Uvicorn | Async REST + WebSocket server |
| Computer Vision | YOLOv8n (Ultralytics) | Real-time object detection |
| Pose Estimation | MediaPipe PoseLandmarker | Fall detection, pose heuristics |
| LLM Reasoning | Groq LLaMA 3.3 70B | Context-aware incident classification |
| Frontend | React 18 + Vite | Live dashboard, MJPEG stream viewer |
| Data Models | Pydantic v2 | Validation, serialization |
| Streaming | MJPEG over HTTP | Browser-compatible video feed |
| Testing | pytest + httpx | Async endpoint + model tests |

## Architecture

```
 ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
 │  IP Camera   │────▶│  VideoStream  │────▶│  YOLOv8n        │
 │  / MP4 File  │     │  (OpenCV)     │     │  (frame infer)  │
 └─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  MediaPipe      │
                                          │  PoseLandmarker │
                                          │  (fall detect)  │
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  Domain Rules   │
                                          │  Engine         │
                                          │  (thresholds,   │
                                          │   zones, labels)│
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  Groq LLaMA     │
                                          │  3.3 70B        │
                                          │  (reasoning +   │
                                          │   severity)     │
                                          └────────┬────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                     ┌────────▼───────┐   ┌───────▼────────┐   ┌───────▼───────┐
                     │  /incidents    │   │  /stream       │   │  /video_feed  │
                     │  (REST)        │   │  (WebSocket)   │   │  (MJPEG)      │
                     └────────────────┘   └────────────────┘   └───────────────┘
                              │                    │                    │
                              └────────────────────┼────────────────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  React 18       │
                                          │  Dashboard      │
                                          └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier works)

### Backend

```bash
# Clone the repository
git clone https://github.com/malik/vigilai.git
cd vigilai

# Set up Python environment
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Place a test video
# Put any .mp4 file at demo/samples/test.mp4

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173` and the API at `http://localhost:8000`.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | API key for Groq LLM reasoning |
| `VIDEO_SOURCE` | No | Path to video file or IP camera URL (default: `demo/samples/test.mp4`) |

---

## Alert System Setup

VigilAI can send **email** (via Gmail SMTP) and **SMS** (via Twilio) alerts when suspicious activity is detected. All alerts are also logged locally via `GET /notifications`.

### Gmail App Password (Email Alerts)

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Enable **2-Step Verification** (required — App Passwords won't appear without it)
3. Go to **Security → 2-Step Verification → App passwords**
   Direct link: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Select app: **Mail**, select device: **Other (custom name)** → type "VigilAI"
5. Click **Generate** — you'll get a 16-character password like `abcd efgh ijkl mnop`
6. Add to `.env`:
   ```
   GMAIL_USER=your@gmail.com
   GMAIL_APP_PASSWORD=abcd-efgh-ijkl-mnop
   ```
   Use the **16-char password with dashes**, not the space-separated version.

### Twilio Trial Account (SMS Alerts)

1. Sign up free at [twilio.com](https://www.twilio.com) — trial accounts include $15 credit
2. From the [console dashboard](https://console.twilio.com), copy:
   - **Account SID** (starts with `AC`)
   - **Auth Token** (click to reveal)
3. Go to **Phone Numbers → Manage → Buy a number** — the trial gives you one free number
4. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_FROM=+1XXXXXXXXXX
   ```
5. **Note:** Trial accounts can only send to [verified numbers](https://console.twilio.com/user/verified-numbers). Verify your owner/police phone numbers in the Twilio console before testing.

### Test the Alert Pipeline

Once `.env` is configured, send a test alert to the owner:

```bash
# Test email + SMS to owner
curl -X POST http://localhost:8000/test-alert \
  -H "Content-Type: application/json" \
  -d '{"message": "VigilAI test alert — system check"}'
```

Expected response:
```json
{"email_sent": true, "sms_sent": true}
```

If either shows `false`, check:
- `GMAIL_USER` / `GMAIL_APP_PASSWORD` are set correctly
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` are set correctly
- The target phone number is verified in Twilio (trial accounts)

### View Notification Log

```bash
curl http://localhost:8000/notifications
```

Returns the last 100 notification entries with timestamp, recipient, channel (email/sms), and delivery status.

### Alert Routing

| Activity | Owner | Police | Emergency |
|----------|-------|--------|-----------|
| weapons | ✅ email+SMS | ✅ email+SMS + screenshot | — |
| fight | ✅ email+SMS | ✅ email+SMS + screenshot | — |
| fall | ✅ email+SMS | — | ✅ email+SMS + screenshot |
| unattended_bag | ✅ email+SMS | ✅ email+SMS | — |
| trespassing | ✅ email+SMS | ✅ email+SMS | — |
| loitering | ✅ email+SMS | — | — |
| no_ppe | ✅ email+SMS | — | — |
| child_unattended | ✅ email+SMS | ✅ email+SMS | — |
| test | ✅ email+SMS | — | — |

---

## How It Works

### 1. Detect
Every frame from the camera feed runs through YOLOv8n for object detection and MediaPipe PoseLandmarker for pose estimation. The domain rules engine filters detections by confidence threshold, target labels, and forbidden labels — only relevant objects pass through.

### 2. Reason
Filtered detections are sent to LLaMA 3.3 70B via Groq's inference API, along with the active domain context and detection metadata. The LLM returns a structured incident: severity level, one-sentence summary, recommended action, and false-positive estimate. Results are cached by detection pattern to minimize API calls.

### 3. Alert
Structured incidents are logged, pushed to connected WebSocket clients in real-time, and overlaid on the MJPEG video stream. The React dashboard renders live alerts with severity color-coding, enabling operators to triage in seconds rather than minutes.

## Demo

A full live demo — including real-time fall detection, weapon alerts, and domain switching — is available in the video submission on Devpost.

## Testing

```bash
cd backend
pytest tests/ -v
```

10 tests covering endpoint behavior, model validation, domain rules coverage, fall-detection logic, and stream output.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

Built at **FutureHacks 2026** by Malik Hassan.
