"""Activity tracking modules for VigilAI.

Provides three tracker classes that maintain state across frames to detect
temporal suspicious activities:
  - LoiteringTracker: detects persons stationary in the same zone > 300s
  - FightDetector: detects rapid overlapping bounding boxes (fight)
  - UnattendedBagTracker: detects bags with no person nearby > 120s
"""

from __future__ import annotations

import time
from typing import Optional


class LoiteringTracker:
    """Tracks person positions across frames to detect loitering.

    A person is considered loitering if they remain in the same zone
    (same approximate bounding box region) for more than 300 seconds.
    """

    LOITER_THRESHOLD_SEC: float = 300.0

    def __init__(self) -> None:
        self.tracked: dict[str, dict] = {}
        self.cooldowns: dict[str, float] = {}

    def update(self, person_id: str, bbox: list[int], timestamp: float) -> None:
        """Update position history for a tracked person.

        Args:
            person_id: Unique identifier for the person (e.g. tracking ID).
            bbox: Bounding box [x1, y1, x2, y2].
            timestamp: Current frame timestamp (time.time()).
        """
        zone_key = self._bbox_to_zone(bbox)

        if person_id not in self.tracked:
            self.tracked[person_id] = {
                "zone": zone_key,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "bbox": bbox,
            }
            return

        entry = self.tracked[person_id]
        prev_zone = entry["zone"]

        if zone_key != prev_zone:
            # Person moved to a different zone — reset timer
            entry["zone"] = zone_key
            entry["first_seen"] = timestamp
            entry["bbox"] = bbox
        else:
            # Same zone — update last seen and bbox
            entry["last_seen"] = timestamp
            entry["bbox"] = bbox

    def is_loitering(self, person_id: str) -> bool:
        """Check if a person has been stationary in the same zone too long.

        Args:
            person_id: Unique identifier for the person.

        Returns:
            True if person has been in the same zone > LOITER_THRESHOLD_SEC.
        """
        if person_id not in self.tracked:
            return False

        entry = self.tracked[person_id]
        elapsed = entry["last_seen"] - entry["first_seen"]
        return elapsed >= self.LOITER_THRESHOLD_SEC

    def is_cooldown_active(self, activity_type: str, zone_key: str) -> bool:
        """Check if a cooldown is active for a given activity+zone combination.

        Args:
            activity_type: Type of activity (e.g. 'loitering', 'fight').
            zone_key: Zone identifier string.

        Returns:
            True if the cooldown has not yet expired.
        """
        cooldown_key = f"{activity_type}:{zone_key}"
        if cooldown_key not in self.cooldowns:
            return False
        elapsed = time.time() - self.cooldowns[cooldown_key]
        return elapsed < 60.0  # default 60s cooldown

    def set_cooldown(self, activity_type: str, zone_key: str) -> None:
        """Set a cooldown timestamp for an activity+zone pair.

        Args:
            activity_type: Type of activity.
            zone_key: Zone identifier string.
        """
        cooldown_key = f"{activity_type}:{zone_key}"
        self.cooldowns[cooldown_key] = time.time()

    def reset(self, person_id: str) -> None:
        """Clear all tracking data for a person who has moved out of frame.

        Args:
            person_id: Unique identifier for the person to remove.
        """
        self.tracked.pop(person_id, None)

    def cleanup_stale(self, max_age_sec: float = 600.0) -> list[str]:
        """Remove tracked persons who haven't been seen recently.

        Args:
            max_age_sec: Maximum age in seconds before a track is removed.

        Returns:
            List of person_ids that were removed.
        """
        now = time.time()
        stale_ids = []
        for pid, entry in self.tracked.items():
            if now - entry["last_seen"] > max_age_sec:
                stale_ids.append(pid)
        for pid in stale_ids:
            del self.tracked[pid]
        return stale_ids

    @staticmethod
    def _bbox_to_zone(bbox: list[int]) -> str:
        """Convert a bounding box to a coarse zone key.

        Uses the horizontal center of the bbox to assign a zone:
          left   → 'left'
          center → 'center'
          right  → 'right'

        This provides a simple spatial bucketing without requiring
        a predefined zone map.
        """
        x1, _y1, x2, _y2 = bbox
        cx = (x1 + x2) / 2.0
        if cx < 0.33:
            return "left"
        elif cx > 0.66:
            return "right"
        return "center"

    def get_elapsed(self, person_id: str) -> float:
        """Get how long a person has been in their current zone.

        Args:
            person_id: Unique identifier for the person.

        Returns:
            Elapsed seconds in current zone, or 0.0 if not tracked.
        """
        if person_id not in self.tracked:
            return 0.0
        entry = self.tracked[person_id]
        return entry["last_seen"] - entry["first_seen"]


class FightDetector:
    """Detects potential fights by checking bounding box proximity.

    A fight is flagged when 2+ person bounding boxes overlap significantly
    or their centers are within 50px of each other.
    """

    PROXIMITY_PX: float = 50.0
    OVERLAP_RATIO: float = 0.3

    def __init__(self) -> None:
        self._last_detections: list[dict] = []
        self._fight_frames: int = 0
        self._required_frames: int = 3  # require 3 consecutive frames

    def update(
        self,
        detections: list,
        pose_landmarks: Optional[list] = None,
    ) -> None:
        """Update detector with current frame's detections.

        Args:
            detections: List of Detection objects (must have .bbox attribute).
            pose_landmarks: Optional list of pose landmarks (unused, reserved).
        """
        self._last_detections = []
        for det in detections:
            bbox = getattr(det, "bbox", None)
            if bbox is None:
                continue
            self._last_detections.append({
                "label": getattr(det, "label", "person"),
                "bbox": bbox,
                "confidence": getattr(det, "confidence", 0.0),
            })

        # Check if fight condition persists
        if self._check_proximity():
            self._fight_frames = min(self._fight_frames + 1, self._required_frames)
        else:
            self._fight_frames = max(self._fight_frames - 1, 0)

    def is_fight(self) -> bool:
        """Check if a fight is currently detected.

        Returns:
            True if 2+ persons are in close proximity for enough frames.
        """
        return self._fight_frames >= self._required_frames

    def _check_proximity(self) -> bool:
        """Check if any two person detections are in close proximity.

        Returns:
            True if overlap ratio or center distance thresholds are exceeded.
        """
        persons = [d for d in self._last_detections if d["label"] == "person"]

        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                b1 = persons[i]["bbox"]
                b2 = persons[j]["bbox"]

                # Check center-to-center distance
                cx1 = (b1[0] + b1[2]) / 2.0
                cy1 = (b1[1] + b1[3]) / 2.0
                cx2 = (b2[0] + b2[2]) / 2.0
                cy2 = (b2[1] + b2[3]) / 2.0
                dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5

                if dist <= self.PROXIMITY_PX:
                    return True

                # Check IoU overlap
                overlap_x = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
                overlap_y = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
                overlap_area = overlap_x * overlap_y

                b1_area = (b1[2] - b1[0]) * (b1[3] - b1[1])
                b2_area = (b2[2] - b2[0]) * (b2[3] - b2[1])
                min_area = min(b1_area, b2_area) if min(b1_area, b2_area) > 0 else 1

                iou = overlap_area / min_area
                if iou >= self.OVERLAP_RATIO:
                    return True

        return False

    def reset(self) -> None:
        """Reset fight detection state."""
        self._fight_frames = 0
        self._last_detections = []


class UnattendedBagTracker:
    """Tracks bags and checks if they are left unattended.

    A bag is considered unattended if no person is within 200px for > 120s.
    """

    BAG_PROXIMITY_PX: float = 200.0
    UNATTENDED_THRESHOLD_SEC: float = 120.0

    def __init__(self) -> None:
        self._bags: dict[str, dict] = {}

    def update(
        self,
        bag_bbox: list[int],
        person_bboxes: list[list[int]],
        timestamp: float,
    ) -> None:
        """Update bag tracking with current frame data.

        Args:
            bag_bbox: Bounding box of the bag [x1, y1, x2, y2].
            person_bboxes: List of person bounding boxes in the frame.
            timestamp: Current frame timestamp (time.time()).
        """
        bag_id = self._bbox_to_id(bag_bbox)
        bag_center = self._bbox_center(bag_bbox)

        # Check if any person is nearby
        person_nearby = False
        for pb in person_bboxes:
            person_center = self._bbox_center(pb)
            dist = (
                (bag_center[0] - person_center[0]) ** 2
                + (bag_center[1] - person_center[1]) ** 2
            ) ** 0.5
            if dist <= self.BAG_PROXIMITY_PX:
                person_nearby = True
                break

        if bag_id not in self._bags:
            # New bag — start tracking
            self._bags[bag_id] = {
                "bbox": bag_bbox,
                "first_unattended": timestamp if not person_nearby else None,
                "last_seen": timestamp,
                "person_nearby": person_nearby,
            }
            return

        entry = self._bags[bag_id]

        if person_nearby:
            # Person is near — reset unattended timer
            entry["first_unattended"] = None
            entry["person_nearby"] = True
            entry["bbox"] = bag_bbox
        else:
            # No person nearby
            if entry["first_unattended"] is None:
                # Just became unattended — start timer
                entry["first_unattended"] = timestamp
            entry["person_nearby"] = False
            entry["bbox"] = bag_bbox

        entry["last_seen"] = timestamp

    def is_unattended(self, bag_id: str) -> bool:
        """Check if a bag has been unattended for too long.

        Args:
            bag_id: Unique identifier for the bag.

        Returns:
            True if no person nearby for > UNATTENDED_THRESHOLD_SEC.
        """
        if bag_id not in self._bags:
            return False

        entry = self._bags[bag_id]
        if entry["first_unattended"] is None:
            return False

        elapsed = time.time() - entry["first_unattended"]
        return elapsed >= self.UNATTENDED_THRESHOLD_SEC

    def get_elapsed(self, bag_id: str) -> float:
        """Get how long a bag has been unattended.

        Args:
            bag_id: Unique identifier for the bag.

        Returns:
            Seconds the bag has been unattended, or 0.0 if not tracked or attended.
        """
        if bag_id not in self._bags:
            return 0.0
        entry = self._bags[bag_id]
        if entry["first_unattended"] is None:
            return 0.0
        return time.time() - entry["first_unattended"]

    def remove_bag(self, bag_id: str) -> None:
        """Remove a bag from tracking (e.g. when it leaves the frame).

        Args:
            bag_id: Unique identifier for the bag to remove.
        """
        self._bags.pop(bag_id, None)

    def cleanup_stale(self, max_age_sec: float = 300.0) -> list[str]:
        """Remove bags that haven't been seen recently.

        Args:
            max_age_sec: Maximum age in seconds before a bag track is removed.

        Returns:
            List of bag_ids that were removed.
        """
        now = time.time()
        stale_ids = []
        for bid, entry in self._bags.items():
            if now - entry["last_seen"] > max_age_sec:
                stale_ids.append(bid)
        for bid in stale_ids:
            del self._bags[bid]
        return stale_ids

    @staticmethod
    def _bbox_to_id(bbox: list[int]) -> str:
        """Generate a deterministic ID for a bag from its bounding box.

        Uses the top-left corner and approximate size as a stable identifier.
        """
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        # Quantize to 10px grid for stability across small movements
        qx = (x1 // 10) * 10
        qy = (y1 // 10) * 10
        qw = (w // 10) * 10
        qh = (h // 10) * 10
        return f"bag_{qx}_{qy}_{qw}_{qh}"

    @staticmethod
    def _bbox_center(bbox: list[int]) -> tuple[float, float]:
        """Get the center point of a bounding box.

        Args:
            bbox: Bounding box [x1, y1, x2, y2].

        Returns:
            (center_x, center_y) tuple.
        """
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
