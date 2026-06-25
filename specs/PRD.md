# Product Requirements Document (PRD)
## SafeWatch AI — Intelligent Multi-Domain Safety Platform
**Version:** 1.0  
**Author:** Hasan Ali (Malik)  
**Hackathon:** FutureHacks 2026  
**Date:** June 2026  

---

## 1. Product Overview

### 1.1 Problem Statement
Traditional surveillance cameras record everything but understand nothing. Security personnel monitoring multiple feeds simultaneously miss up to 45% of critical events after just 20 minutes. Alerts arrive too late, lack context, and generate excessive false positives — causing alert fatigue that renders entire systems ineffective.

### 1.2 Product Vision
SafeWatch AI is a context-aware, multi-domain intelligent safety platform that combines computer vision with LLM reasoning to transform raw video footage into structured, actionable incident intelligence — delivered through a real-time dashboard.

**Core Thesis:** The world doesn't need more cameras. It needs cameras that understand.

### 1.3 Target Users
| User | Role | Pain Point |
|---|---|---|
| School Administrators | Monitor campus safety | Cannot watch 20+ feeds simultaneously |
| Elder Care Facility Managers | Resident safety | Falls go undetected for critical minutes |
| Construction Site Supervisors | PPE compliance | Manual inspections are slow and incomplete |
| Smart City Operators | Public space safety | No contextual understanding of incidents |

---

## 2. Goals & Success Metrics

### 2.1 Hackathon Goals
- Demonstrate a fully functional end-to-end pipeline (video → detection → reasoning → dashboard)
- Show multi-domain switching in a live or recorded demo
- Produce a polished UI that judges can interact with

### 2.2 Key Success Metrics
| Metric | Target |
|---|---|
| Detection latency (frame → alert) | < 3 seconds |
| LLM reasoning response time | < 2 seconds (Groq) |
| Domains supported | 4 (School, Elderly, Construction, Public) |
| Dashboard real-time update rate | 1–2 fps minimum |
| False positive reduction vs. raw detection | > 30% via context filtering |

---

## 3. Features & Requirements

### 3.1 Core Features (Must Have — MVP)

#### F1: Multi-Domain CV Detection Engine
- **F1.1** YOLOv8n object detection for weapons, persons, PPE (helmet, vest)
- **F1.2** MediaPipe Pose estimation for fall detection and prolonged stillness
- **F1.3** Domain-specific rule sets (configurable thresholds per domain)
- **F1.4** Video file input support (`.mp4`, `.avi`) + webcam (`device 0`)

#### F2: LLM Context Reasoning Layer
- **F2.1** Groq API integration (LLaMA 3.3 70B — free tier)
- **F2.2** Per-detection context prompt with domain, object, duration, location zone
- **F2.3** Structured JSON output: severity, summary, recommended action, false positive likelihood
- **F2.4** Severity classification: LOW / MEDIUM / HIGH / CRITICAL

#### F3: FastAPI Backend
- **F3.1** `/stream` WebSocket endpoint for real-time detection events
- **F3.2** `/incidents` REST endpoint — GET paginated incident log
- **F3.3** `/domain` REST endpoint — POST to switch active domain
- **F3.4** `/health` endpoint for system status
- **F3.5** CORS enabled for React frontend

#### F4: React + Tailwind Dashboard
- **F4.1** Live camera feed panel with bounding box overlay (MJPEG stream)
- **F4.2** Real-time alert panel — color-coded by severity
- **F4.3** Incident log table with timestamp, domain, AI summary, action
- **F4.4** Domain selector (School / Elderly / Construction / Public / All)
- **F4.5** Severity heatmap / stats bar
- **F4.6** Dark theme UI with red/amber/green severity color system

### 3.2 Secondary Features (Nice to Have)
- **S1** Email/webhook alert dispatch for CRITICAL events
- **S2** Confidence score visualization per detection
- **S3** Export incident log as CSV
- **S4** Zone-based spatial heatmap overlay on video feed

### 3.3 Out of Scope (Hackathon)
- User authentication / multi-user support
- Cloud video storage / DVR functionality
- Mobile app
- Custom model fine-tuning
- Multi-camera support (> 1 simultaneous stream)

---

## 4. Technical Constraints

| Constraint | Decision |
|---|---|
| LLM API Cost | Groq free tier (LLaMA 3.3 70B) — 14,400 req/day |
| Hardware | Runs on CPU (no GPU required); YOLOv8n is CPU-optimized |
| Deployment | Backend: Railway/Render free tier. Frontend: Vercel |
| No live camera required | Demo uses pre-recorded `.mp4` video files |
| Build time | 3 days total |

---

## 5. Domain Rules Specification

### School / Campus
- **Trigger objects:** knife, scissors, person (in restricted zone after hours)
- **Pose triggers:** running (high speed person movement in corridors)
- **Context:** Time of day matters — knife near cafeteria at lunch vs. entrance at dismissal

### Elderly Care
- **Pose triggers:** Fall posture (horizontal body on floor), motionless > 30s
- **Object triggers:** wheelchair out of bounds zone
- **Context:** Duration is the key variable — same posture for 5s vs. 45s

### Construction Site
- **Object triggers:** Person detected without helmet, without safety vest
- **Zone triggers:** Person within 2m radius of hazard zone marker
- **Context:** Proximity to machinery elevates severity

### Public Space
- **Object triggers:** Unattended bag/luggage (object without nearby person > 5min)
- **Crowd triggers:** Density exceeding threshold in confined space
- **Context:** Location and time determine severity

---

## 6. User Stories

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-01 | Safety operator | See live camera feed with detections overlaid | I know what the system is analyzing |
| US-02 | Safety operator | Receive color-coded alerts instantly | I can prioritize critical events |
| US-03 | Safety operator | Read an AI-generated incident summary | I understand context without reviewing footage |
| US-04 | Facility manager | Switch between safety domains | One platform covers all our locations |
| US-05 | Safety operator | See full incident history with timestamps | I can review and report past events |
| US-06 | Admin | Know the recommended action per incident | I can respond immediately without interpretation |

---

## 7. Build Timeline

| Day | Milestone |
|---|---|
| Day 2 (Today) | FastAPI skeleton, YOLOv8 detector, Groq reasoning integration, WebSocket endpoint |
| Day 3 | React dashboard (all 4 components), WebSocket connection, domain switcher, alert panel |
| Day 4 (Sunday) | Polish UI, record demo video, write Devpost description, deploy |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Groq API rate limit hit | Cache reasoning results per detection type; don't call LLM every frame |
| WebSocket instability | Fallback to polling `/incidents` endpoint every 2s |
| YOLOv8 too slow on CPU | Use YOLOv8n (nano) — optimized for CPU; process every 3rd frame |
| Live camera not available | Use pre-recorded sample `.mp4` files for demo |
| Demo looks unpolished | Scripted demo video > live demo for submission |
