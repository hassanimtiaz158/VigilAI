"""Pydantic v2 schemas for VigilAI."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DomainLiteral = Literal["school", "elderly", "construction", "public", "child"]


class Detection(BaseModel):
    """Single detection event from YOLO / MediaPipe on one frame."""

    label: str = Field(min_length=1, description="YOLO class label")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence 0-1")
    bbox: list[int] = Field(
        min_length=4,
        max_length=4,
        description="[x1, y1, x2, y2] pixel coordinates",
    )
    zone: str = Field(min_length=1, description="Logical zone name")

    @field_validator("bbox")
    @classmethod
    def bbox_must_be_valid(cls, v: list[int]) -> list[int]:
        x1, y1, x2, y2 = v
        if x2 < x1 or y2 < y1:
            raise ValueError(
                f"bbox must satisfy x2>=x1 and y2>=y1, got [{x1},{y1},{x2},{y2}]"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_reasonable(cls, v: float) -> float:
        if v > 1.0:
            raise ValueError("confidence cannot exceed 1.0")
        return round(v, 4)


class Incident(BaseModel):
    """Structured incident produced by LLM reasoning over one or more detections."""

    id: str = Field(min_length=1, description="Short unique incident ID")
    timestamp: datetime = Field(description="UTC time the incident was raised")
    domain: str = Field(min_length=1, description="Active detection domain")
    detections: list[Detection] = Field(
        min_length=1, description="Detections that triggered this incident"
    )
    duration_sec: float = Field(ge=0.0, description="Event duration in seconds")
    severity: Severity
    summary: str = Field(min_length=1, description="One-sentence human summary")
    recommended_action: str = Field(
        min_length=1, description="One-sentence recommended response"
    )
    false_positive_pct: int = Field(
        ge=0, le=100, description="Estimated false-positive likelihood 0-100"
    )

    @field_validator("summary", "recommended_action")
    @classmethod
    def strip_and_validate_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("field must not be empty or whitespace-only")
        return stripped


class DomainSwitch(BaseModel):
    """Request body for switching the active detection domain."""

    domain: DomainLiteral
