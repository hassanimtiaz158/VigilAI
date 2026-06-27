"""CV inference engine for VigilAI — YOLOv8n + MediaPipe PoseLandmarker.

Pipeline per frame:
  1. Increment frame counter; skip 2 of every 3 frames (CPU budget).
  2. Run YOLOv8n, keep only detections whose label is in the active
     domain's *target_labels* AND whose confidence >= the domain threshold.
  3. Check detections against SUSPICIOUS_ACTIVITIES rules.
  4. Draw bounding boxes on the frame — green for normal, red for suspicious.
  5. For 'elderly' and 'school' domains, run MediaPipe PoseLandmarker and
     check for falls (nose below hips).
  6. Return annotated frame + list of Detection models only if suspicious.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import cv2
import mediapipe as mp
import numpy as np
import torch

# Patch torch.load for PyTorch 2.6+ compatibility with ultralytics 8.x
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load

from ultralytics import YOLO

from domain_rules import DOMAIN_RULES
from models import Detection
from suspicious_rules import SUSPICIOUS_ACTIVITIES

# --------------------------------------------------------------------------- #
# Drawing constants
# --------------------------------------------------------------------------- #
_COLOR_NORMAL = (0, 255, 0)     # green
_COLOR_ALERT = (0, 0, 255)      # red
_THICKNESS = 2
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.5
_FONT_THICKNESS = 1
_LABEL_PAD = 8                  # pixels above the bbox for the label text

# --------------------------------------------------------------------------- #
# MediaPipe landmark indices (same for legacy + Tasks API)
# --------------------------------------------------------------------------- #
_NOSE = 0
_LEFT_HIP = 23
_RIGHT_HIP = 24

# Path to the PoseLandmarker model asset (downloaded once at startup)
_POSE_MODEL_PATH = Path(__file__).parent / "pose_landmarker_lite.task"


class SafeWatchDetector:
    """Multi-domain frame processor combining YOLO + MediaPipe."""

    def __init__(self, pose_model_path: str | Path = _POSE_MODEL_PATH) -> None:
        self.yolo = YOLO("yolov8n.pt")

        # --- MediaPipe PoseLandmarker (Tasks API, >=0.10.0) ------------
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import (
            PoseLandmarker,
            PoseLandmarkerOptions,
            RunningMode,
        )

        base_opts = BaseOptions(model_asset_path=str(pose_model_path))
        options = PoseLandmarkerOptions(
            base_options=base_opts,
            running_mode=RunningMode.IMAGE,
            min_pose_detection_confidence=0.6,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose = PoseLandmarker.create_from_options(options)

        self.active_domain: str = "school"
        self.frame_count: int = 0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_domain(self, domain: str) -> None:
        """Switch the active detection domain."""
        self.active_domain = domain

    def is_suspicious(
        self, detections: list[Detection], frame: np.ndarray
    ) -> Tuple[bool, str, str]:
        """Check whether any detection matches a suspicious activity rule.

        Returns:
            (is_suspicious, activity_type, message)
            - Normal person detection alone → (False, '', '')
            - Suspicious activity found    → (True, '<rule_key>', '<message>')
        """
        if not detections:
            return False, "", ""

        labels = [d.label for d in detections]
        bboxes = [d.bbox for d in detections]
        zones = [d.zone for d in detections]
        h, w = frame.shape[:2]

        # --- WEAPONS: knife / gun / scissors with conf > threshold -------
        weapon_labels = SUSPICIOUS_ACTIVITIES["weapons"]["labels"]
        weapon_threshold = SUSPICIOUS_ACTIVITIES["weapons"]["confidence_threshold"]
        for det in detections:
            if det.label in weapon_labels and det.confidence >= weapon_threshold:
                return (
                    True,
                    "weapons",
                    SUSPICIOUS_ACTIVITIES["weapons"]["message"],
                )

        # --- FIGHT: 2+ persons in close proximity with rapid movement ---
        person_dets = [d for d in detections if d.label == "person"]
        if len(person_dets) >= 2:
            for i in range(len(person_dets)):
                for j in range(i + 1, len(person_dets)):
                    b1 = person_dets[i].bbox
                    b2 = person_dets[j].bbox
                    # Check overlap or close proximity (within 80px)
                    overlap_x = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
                    overlap_y = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
                    overlap_area = overlap_x * overlap_y
                    b1_area = (b1[2] - b1[0]) * (b1[3] - b1[1])
                    b2_area = (b2[2] - b2[0]) * (b2[3] - b2[1])
                    min_area = min(b1_area, b2_area) if min(b1_area, b2_area) > 0 else 1
                    # Significant overlap (IoU > 0.1) or very close centers
                    cx1, cy1 = (b1[0] + b1[2]) / 2, (b1[1] + b1[3]) / 2
                    cx2, cy2 = (b2[0] + b2[2]) / 2, (b2[1] + b2[3]) / 2
                    dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
                    iou = overlap_area / min_area if min_area > 0 else 0
                    if iou > 0.1 or dist < 80:
                        return (
                            True,
                            "fight",
                            SUSPICIOUS_ACTIVITIES["fight"]["message"],
                        )

        # --- FALL: person horizontal on floor > 10s --------------------
        # Already handled by MediaPipe pose check below; skip here.

        # --- UNATTENDED BAG: bag present with no nearby person ----------
        bag_labels = SUSPICIOUS_ACTIVITIES["unattended_bag"]["labels"]
        bag_threshold = SUSPICIOUS_ACTIVITIES["unattended_bag"]["confidence_threshold"]
        bags = [
            d for d in detections
            if d.label in bag_labels and d.confidence >= bag_threshold
        ]
        if bags and not person_dets:
            return (
                True,
                "unattended_bag",
                SUSPICIOUS_ACTIVITIES["unattended_bag"]["message"],
            )

        # --- TRESPASSING: person in restricted/entrance zone ------------
        restricted_zones = {"entrance", "restricted", "floor"}
        for det in detections:
            if det.label == "person" and det.zone in restricted_zones:
                return (
                    True,
                    "trespassing",
                    SUSPICIOUS_ACTIVITIES["trespassing"]["message"],
                )

        # --- LOITERING: handled by LoiteringTracker in main.py ----------
        # Not checked here — temporal tracking required (300s threshold).

        # --- NO PPE: person in construction zone without helmet/vest ----
        if self.active_domain == "construction":
            has_person = any(d.label == "person" for d in detections)
            has_helmet = any(d.label == "helmet" for d in detections)
            has_vest = any(d.label == "safety vest" for d in detections)
            if has_person and not (has_helmet and has_vest):
                return (
                    True,
                    "no_ppe",
                    SUSPICIOUS_ACTIVITIES["no_ppe"]["message"],
                )

        # --- CHILD UNATTENDED: small person alone -----------------------
        if self.active_domain == "child":
            if len(person_dets) == 1:
                det = person_dets[0]
                bbox = det.bbox
                person_h = bbox[3] - bbox[1]
                # Child: height < 40% of frame height
                if person_h < h * 0.4:
                    return (
                        True,
                        "child_unattended",
                        SUSPICIOUS_ACTIVITIES["child_unattended"]["message"],
                    )

        # --- Normal activity: walking, standing, sitting ----------------
        return False, "", ""

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[np.ndarray, list[Detection]]:
        """Process a single video frame.

        Returns:
            (annotated_frame, detections) where detections is empty if
            the scene contains only normal activity.
        """
        self.frame_count += 1

        # --- CPU budget: process 1 of every 3 frames -------------------
        if (self.frame_count - 1) % 3 != 0:
            return frame, []

        # --- Guard: empty / None frame ---------------------------------
        if frame is None or frame.size == 0:
            return frame, []

        frame = frame.copy()

        h, w = frame.shape[:2]
        rules = DOMAIN_RULES.get(self.active_domain, {})
        target_labels: list[str] = rules.get("target_labels", [])
        forbidden_labels: list[str] = rules.get("forbidden_labels", [])
        conf_threshold: float = rules.get("confidence_threshold", 0.5)
        pose_checks: list[str] = rules.get("pose_checks", [])

        detections: list[Detection] = []

        # --------------------------- YOLO -----------------------------
        results = self.yolo(frame, verbose=False, conf=conf_threshold)

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                idx = int(box.cls[0])
                label: str = self.yolo.names[idx]

                if label not in target_labels:
                    continue

                conf: float = float(box.conf[0])
                if conf < conf_threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].flatten())

                # Clamp to frame bounds
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(w - 1, x2)
                y2 = min(h - 1, y2)

                zone = self._get_zone(x1, y1, frame)

                detections.append(
                    Detection(
                        label=label,
                        confidence=conf,
                        bbox=[x1, y1, x2, y2],
                        zone=zone,
                    )
                )

                # --- Draw bbox + label (default green) -----------------
                color = _COLOR_NORMAL
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, _THICKNESS)

                text = f"{label} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(
                    text, _FONT, _FONT_SCALE, _FONT_THICKNESS
                )
                cv2.rectangle(
                    frame,
                    (x1, y1 - th - _LABEL_PAD),
                    (x1 + tw + 2, y1),
                    color,
                    -1,
                )
                cv2.putText(
                    frame,
                    text,
                    (x1 + 1, y1 - _LABEL_PAD // 2),
                    _FONT,
                    _FONT_SCALE,
                    (255, 255, 255),
                    _FONT_THICKNESS,
                )

        # --------------------- MediaPipe Pose -------------------------
        run_pose = "fall" in pose_checks or rules.get("pose_always", False)
        if run_pose:
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB, data=frame
            )
            pose_result = self.pose.detect(mp_image)

            if self._check_fall(pose_result):
                detections.append(
                    Detection(
                        label="fall_detected",
                        confidence=0.85,
                        bbox=[0, 0, w, h],
                        zone="floor",
                    )
                )
                cv2.putText(
                    frame,
                    "FALL DETECTED",
                    (10, 30),
                    _FONT,
                    0.8,
                    _COLOR_ALERT,
                    2,
                )

        # --------------------- Suspicious check -----------------------
        # NOTE: is_suspicious() is called by main.py video_feed generator.
        # process_frame() returns all detections for the caller to evaluate.

        # Check if detections are suspicious to set bbox colors
        suspicious, activity_type, _message = self.is_suspicious(detections, frame)

        if suspicious:
            # Re-draw all bounding boxes in red for suspicious detections
            for det in detections:
                x1, y1, x2, y2 = det.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), _COLOR_ALERT, _THICKNESS)
                text = f"{det.label} {det.confidence:.2f}"
                (tw, th), _ = cv2.getTextSize(
                    text, _FONT, _FONT_SCALE, _FONT_THICKNESS
                )
                cv2.rectangle(
                    frame,
                    (x1, y1 - th - _LABEL_PAD),
                    (x1 + tw + 2, y1),
                    _COLOR_ALERT,
                    -1,
                )
                cv2.putText(
                    frame,
                    text,
                    (x1 + 1, y1 - _LABEL_PAD // 2),
                    _FONT,
                    _FONT_SCALE,
                    (255, 255, 255),
                    _FONT_THICKNESS,
                )
            # Overlay suspicious activity banner
            banner = f"ALERT: {activity_type.upper()}"
            cv2.putText(
                frame, banner, (10, h - 20), _FONT, 0.7, _COLOR_ALERT, 2,
            )

        return frame, detections

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _get_zone(self, x: int, y: int, frame: np.ndarray) -> str:
        """Map a point to a vertical zone (top / middle / bottom third)."""
        h = frame.shape[0]
        third = h / 3

        if y < third:
            return "entrance"
        elif y > third * 2:
            return "floor"
        return "open_area"

    def _check_fall(self, pose_result) -> bool:
        """Return True if the nose is below the average hip level.

        MediaPipe landmark indices:
          0  = nose
          23 = left hip
          24 = right hip
        In image-space y increases downward, so a fallen person has
        nose_y > hip_y.
        """
        poses = getattr(pose_result, "pose_landmarks", None)
        if poses:
            landmarks = poses[0]
        else:
            landmarks = getattr(pose_result, "landmark", None)
        if not landmarks:
            return False

        nose_y = landmarks[_NOSE].y
        left_hip_y = landmarks[_LEFT_HIP].y
        right_hip_y = landmarks[_RIGHT_HIP].y
        avg_hip_y = (left_hip_y + right_hip_y) / 2.0
        return nose_y > avg_hip_y

    def capture_alert_frame(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        activity_type: str,
    ) -> bytes:
        """Capture an annotated screenshot of the current alert frame.

        Draws red bounding boxes around suspicious detections, adds a
        timestamp, alert banner, and red border. Encodes as JPEG bytes
        suitable for email attachment.

        Args:
            frame: The current video frame (will be copied, not modified).
            detections: List of Detection objects to highlight.
            activity_type: Suspicious activity type string (e.g. 'weapons').

        Returns:
            JPEG-encoded bytes of the annotated frame.
        """
        img = frame.copy()
        h, w = img.shape[:2]

        # Red border (5px) around entire frame
        cv2.rectangle(img, (0, 0), (w - 1, h - 1), _COLOR_ALERT, 5)

        # Draw red bounding boxes around suspicious detections
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), _COLOR_ALERT, _THICKNESS)

            text = f"{det.label} {det.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(
                text, _FONT, _FONT_SCALE, _FONT_THICKNESS
            )
            cv2.rectangle(
                img,
                (x1, y1 - th - _LABEL_PAD),
                (x1 + tw + 2, y1),
                _COLOR_ALERT,
                -1,
            )
            cv2.putText(
                img,
                text,
                (x1 + 1, y1 - _LABEL_PAD // 2),
                _FONT,
                _FONT_SCALE,
                (255, 255, 255),
                _FONT_THICKNESS,
            )

        # Alert banner top-left
        banner = f"VIGILAI ALERT — {activity_type.upper()}"
        cv2.putText(img, banner, (12, 30), _FONT, 0.7, _COLOR_ALERT, 2)

        # Timestamp bottom-right
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        (tw, th), _ = cv2.getTextSize(
            timestamp, _FONT, _FONT_SCALE, _FONT_THICKNESS
        )
        cv2.putText(
            img, timestamp, (w - tw - 12, h - 12), _FONT, _FONT_SCALE, _COLOR_ALERT, 1,
        )

        # Encode as JPEG bytes
        _, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return encoded.tobytes()
