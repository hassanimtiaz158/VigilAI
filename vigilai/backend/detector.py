"""CV inference engine for VigilAI — YOLOv8n + MediaPipe PoseLandmarker.

Pipeline per frame:
  1. Increment frame counter; skip 2 of every 3 frames (CPU budget).
  2. Run YOLOv8n, keep only detections whose label is in the active
     domain's *target_labels* AND whose confidence >= the domain threshold.
  3. Draw bounding boxes on the frame — green for normal, red for forbidden.
  4. For 'elderly' and 'school' domains, run MediaPipe PoseLandmarker and
     check for falls (nose below hips).
  5. Return the annotated frame + list of Detection models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import cv2
import mediapipe as mp
import numpy as np
from ultralytics import YOLO

from domain_rules import DOMAIN_RULES
from models import Detection

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

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[np.ndarray, list[Detection]]:
        """Process a single video frame.

        Returns (annotated_frame, detections).
        """
        self.frame_count += 1

        # --- CPU budget: process 1 of every 3 frames -------------------
        # Process on frames 1, 4, 7, ... (skip 2 after each processed frame)
        if (self.frame_count - 1) % 3 != 0:
            return frame, []

        # --- Guard: empty / None frame ---------------------------------
        if frame is None or frame.size == 0:
            return frame, []

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

                # Clamp to frame bounds (safety against off-frame boxes)
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

                # --- Draw bbox + label --------------------------------
                color = (
                    _COLOR_ALERT
                    if label in forbidden_labels
                    else _COLOR_NORMAL
                )
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, _THICKNESS)

                text = f"{label} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(
                    text, _FONT, _FONT_SCALE, _FONT_THICKNESS
                )
                # Label background
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
        if "fall" in pose_checks:
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
                # Visual indicator for fall
                cv2.putText(
                    frame,
                    "FALL DETECTED",
                    (10, 30),
                    _FONT,
                    0.8,
                    _COLOR_ALERT,
                    2,
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
        # Support both real MediaPipe results (pose_landmarks list)
        # and simple dict-based mocks (landmark dict).
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
