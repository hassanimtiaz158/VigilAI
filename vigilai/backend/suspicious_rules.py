"""Suspicious activity detection rules for VigilAI.

Defines a dictionary of suspicious activities with their detection criteria,
severity levels, and alert actions. Normal human behavior (walking, standing,
sitting) is explicitly excluded from triggering alerts.
"""

from __future__ import annotations

from typing import Literal

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

__all__ = ["SUSPICIOUS_ACTIVITIES", "SuspiciousActivity"]

SuspiciousActivity = dict


SUSPICIOUS_ACTIVITIES: dict[str, SuspiciousActivity] = {
    # ------------------------------------------------------------------ #
    #  WEAPONS DETECTION
    # ------------------------------------------------------------------ #
    "weapons": {
        "labels": ["knife", "gun", "scissors"],
        "confidence_threshold": 0.55,
        "severity": "CRITICAL",
        "message": "Weapon detected in the area — immediate threat to safety.",
        "alert_police": True,
        "alert_emergency": False,
        "cooldown_sec": 30,
    },
    # ------------------------------------------------------------------ #
    #  FIGHT / VIOLENT ALTERCATION
    # ------------------------------------------------------------------ #
    "fight": {
        "labels": ["person"],
        "confidence_threshold": 0.60,
        "severity": "CRITICAL",
        "message": "Fight detected — multiple persons in rapid close proximity.",
        "alert_police": True,
        "alert_emergency": False,
        "cooldown_sec": 45,
    },
    # ------------------------------------------------------------------ #
    #  FALL DETECTION
    # ------------------------------------------------------------------ #
    "fall": {
        "labels": ["person"],
        "confidence_threshold": 0.55,
        "severity": "HIGH",
        "message": "Person has fallen and remains on the floor for over 10 seconds.",
        "alert_police": False,
        "alert_emergency": True,
        "cooldown_sec": 60,
    },
    # ------------------------------------------------------------------ #
    #  UNATTENDED BAG / OBJECT
    # ------------------------------------------------------------------ #
    "unattended_bag": {
        "labels": ["backpack", "suitcase", "handbag"],
        "confidence_threshold": 0.50,
        "severity": "HIGH",
        "message": "Unattended bag detected — no person nearby for over 120 seconds.",
        "alert_police": True,
        "alert_emergency": False,
        "cooldown_sec": 90,
    },
    # ------------------------------------------------------------------ #
    #  TRESPASSING — RESTRICTED ZONE AFTER HOURS
    # ------------------------------------------------------------------ #
    "trespassing": {
        "labels": ["person"],
        "confidence_threshold": 0.55,
        "severity": "HIGH",
        "message": "Person detected in a restricted zone outside of permitted hours.",
        "alert_police": True,
        "alert_emergency": False,
        "cooldown_sec": 120,
    },
    # ------------------------------------------------------------------ #
    #  LOITERING — PROLONGED STATIONARY BEHAVIOR
    # ------------------------------------------------------------------ #
    "loitering": {
        "labels": ["person"],
        "confidence_threshold": 0.50,
        "severity": "MEDIUM",
        "message": "Person stationary in the same location for over 300 seconds.",
        "alert_police": False,
        "alert_emergency": False,
        "cooldown_sec": 300,
    },
    # ------------------------------------------------------------------ #
    #  NO PPE — MISSING HELMET OR SAFETY VEST
    # ------------------------------------------------------------------ #
    "no_ppe": {
        "labels": ["person", "helmet", "safety vest"],
        "confidence_threshold": 0.55,
        "severity": "HIGH",
        "message": "Worker in construction zone missing required PPE (helmet or vest).",
        "alert_police": False,
        "alert_emergency": False,
        "cooldown_sec": 60,
    },
    # ------------------------------------------------------------------ #
    #  CHILD UNATTENDED
    # ------------------------------------------------------------------ #
    "child_unattended": {
        "labels": ["person"],
        "confidence_threshold": 0.55,
        "severity": "CRITICAL",
        "message": "Small person (child) alone for over 60 seconds — no guardian detected.",
        "alert_police": True,
        "alert_emergency": False,
        "cooldown_sec": 60,
    },
}
