# SafeWatch AI

Intelligent multi-domain safety platform — FutureHacks 2026.

## Stack

- **Backend:** Python 3.11 · FastAPI · YOLOv8n · MediaPipe · Groq LLaMA 3.3 70B
- **Frontend:** React 18 · Tailwind CSS · Vite

## Domains

- School / Campus
- Elderly Care
- Construction Site
- Public Space

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System status |
| `GET` | `/video_feed` | MJPEG annotated stream |
| `GET` | `/incidents` | Incident log |
| `POST` | `/domain` | Switch domain |
| `WS` | `/stream` | Real-time alerts |
