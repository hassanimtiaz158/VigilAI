"""Per-domain detection thresholds and rule sets for VigilAI.

Each domain defines:
  - target_labels: YOLO classes the detector should keep
  - confidence_threshold: minimum confidence to accept a detection
  - pose_checks: which MediaPipe pose heuristics to run
  - zone_map: mapping from logical zone names to risk levels
  - domain-specific extras (forbidden_labels, stillness, PPE, unattended bags)
"""

from __future__ import annotations

from typing import Literal

ZoneRisk = Literal["low", "medium", "high_risk", "critical"]
PoseCheck = Literal["running", "fall", "prolonged_stillness"]

__all__ = ["DOMAIN_RULES"]

DOMAIN_RULES: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    #  SCHOOL / CAMPUS
    # ------------------------------------------------------------------ #
    "school": {
        "target_labels": ["knife", "scissors", "person"],
        "forbidden_labels": ["knife", "scissors"],
        "confidence_threshold": 0.50,
        "pose_checks": ["running"],
        "zone_map": {
            "entrance": "high_risk",
            "cafeteria": "medium_risk",
            "corridor": "medium_risk",
            "open_area": "low",
        },
    },
    # ------------------------------------------------------------------ #
    #  ELDERLY CARE
    # ------------------------------------------------------------------ #
    "elderly": {
        "target_labels": ["person"],
        "confidence_threshold": 0.60,
        "pose_checks": ["fall", "prolonged_stillness"],
        "stillness_threshold_sec": 30,
        "zone_map": {
            "floor": "critical",
            "bed": "low",
            "room": "medium_risk",
            "hallway": "medium_risk",
        },
    },
    # ------------------------------------------------------------------ #
    #  CONSTRUCTION SITE
    # ------------------------------------------------------------------ #
    "construction": {
        "target_labels": ["person", "helmet", "safety vest"],
        "missing_ppe_trigger": True,
        "confidence_threshold": 0.55,
        "proximity_zone": "machinery_zone",
        "zone_map": {
            "machinery_zone": "critical",
            "walkway": "medium_risk",
            "entrance": "medium_risk",
            "open_area": "low",
        },
    },
    # ------------------------------------------------------------------ #
    #  PUBLIC SPACE
    # ------------------------------------------------------------------ #
    "public": {
        "target_labels": ["suitcase", "backpack", "handbag", "person"],
        "unattended_bag_threshold_sec": 300,
        "confidence_threshold": 0.50,
        "zone_map": {
            "transit_hub": "high_risk",
            "open_space": "medium_risk",
            "entrance": "medium_risk",
            "platform": "high_risk",
        },
    },
}
