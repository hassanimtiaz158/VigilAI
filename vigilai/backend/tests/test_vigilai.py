"""Complete test suite for the VigilAI backend.

Run with:  pytest tests/test_vigilai.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from domain_rules import DOMAIN_RULES
from models import Detection, Incident
from reasoning import _reasoning_cache


# --------------------------------------------------------------------------- #
# 1. Health endpoint
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_health_endpoint(client):
    """GET /health returns 200 with expected keys."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "active_domain" in data
    assert data["status"] == "ok"


# --------------------------------------------------------------------------- #
# 2. Domain switch — valid
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_domain_switch_valid(client):
    """POST /domain with a valid domain returns 200 and echoes the domain."""
    response = await client.post("/domain", json={"domain": "elderly"})
    assert response.status_code == 200

    data = response.json()
    assert data["active_domain"] == "elderly"


# --------------------------------------------------------------------------- #
# 3. Domain switch — invalid
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_domain_switch_invalid(client):
    """POST /domain with an unknown domain returns 422 (Pydantic validation)."""
    response = await client.post("/domain", json={"domain": "mars"})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# 4. Incidents endpoint — empty
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_incidents_empty(client):
    """GET /incidents returns 200 with an 'incidents' list."""
    response = await client.get("/incidents")
    assert response.status_code == 200

    data = response.json()
    assert "incidents" in data
    assert isinstance(data["incidents"], list)


# --------------------------------------------------------------------------- #
# 5. Domain rules coverage
# --------------------------------------------------------------------------- #
def test_domain_rules_coverage():
    """DOMAIN_RULES has all 4 required keys, each with target_labels + threshold."""
    required_keys = {"school", "elderly", "construction", "public"}
    assert required_keys.issubset(set(DOMAIN_RULES.keys()))

    for domain, rules in DOMAIN_RULES.items():
        assert "target_labels" in rules, f"{domain} missing target_labels"
        assert "confidence_threshold" in rules, (
            f"{domain} missing confidence_threshold"
        )
        assert isinstance(rules["target_labels"], list)
        assert isinstance(rules["confidence_threshold"], float)


# --------------------------------------------------------------------------- #
# 6. Detection model validation
# --------------------------------------------------------------------------- #
def test_detection_model_validation():
    """Detection accepts valid data and rejects missing/invalid fields."""
    # Valid
    det = Detection(
        label="person",
        confidence=0.91,
        bbox=[100, 100, 200, 300],
        zone="open_area",
    )
    assert det.label == "person"
    assert det.confidence == 0.91
    assert det.bbox == [100, 100, 200, 300]
    assert det.zone == "open_area"

    # Missing required field (label)
    with pytest.raises(ValidationError):
        Detection(confidence=0.5, bbox=[0, 0, 1, 1], zone="open_area")

    # Invalid bbox (x2 < x1)
    with pytest.raises(ValidationError):
        Detection(label="person", confidence=0.5, bbox=[200, 0, 100, 100], zone="z")

    # Confidence out of range
    with pytest.raises(ValidationError):
        Detection(label="person", confidence=1.5, bbox=[0, 0, 1, 1], zone="z")


# --------------------------------------------------------------------------- #
# 7. Incident model — severity Literal validation
# --------------------------------------------------------------------------- #
def test_incident_model_severity_literal():
    """Incident rejects invalid severity Literal values, accepts valid ones."""
    base = dict(
        id="test123",
        timestamp="2026-06-25T12:00:00",
        domain="school",
        detections=[
            {
                "label": "person",
                "confidence": 0.9,
                "bbox": [0, 0, 10, 10],
                "zone": "open_area",
            }
        ],
        duration_sec=1.0,
        summary="Test incident",
        recommended_action="Do something",
        false_positive_pct=10,
    )

    # Invalid severity
    with pytest.raises(ValidationError):
        Incident(**{**base, "severity": "INVALID"})

    # Valid severity
    inc = Incident(**{**base, "severity": "CRITICAL"})
    assert inc.severity == "CRITICAL"


# --------------------------------------------------------------------------- #
# 8. Fall detection logic (unit test)
# --------------------------------------------------------------------------- #
def test_fall_detection_logic(fallen_landmarks, standing_landmarks):
    """SafeWatchDetector._check_fall returns True when nose is below hips."""
    # Import here to avoid loading heavy models at module import time
    from detector import SafeWatchDetector

    # We only need the method — instantiate without running __init__'s
    # heavy model loading by calling the method on a bare instance.
    detector = SafeWatchDetector.__new__(SafeWatchDetector)

    # Fallen person → True
    assert detector._check_fall(fallen_landmarks) is True

    # Standing person → False
    assert detector._check_fall(standing_landmarks) is False


# --------------------------------------------------------------------------- #
# 9. Reasoning cache
# --------------------------------------------------------------------------- #
def test_reasoning_cache():
    """_reasoning_cache is an OrderedDict and starts empty."""
    from collections import OrderedDict
    assert isinstance(_reasoning_cache, OrderedDict)
    assert len(_reasoning_cache) == 0


# --------------------------------------------------------------------------- #
# 10. Video feed returns stream
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_video_feed_returns_stream(client):
    """GET /video_feed returns 200 with multipart/x-mixed-replace content type.

    The MJPEG stream is an infinite generator, so we only read the headers
    (the first few bytes) and then cancel the request.
    """
    async with client.stream("GET", "/video_feed") as response:
        assert response.status_code == 200
        content_type = response.headers.get("content-Type", "")
        assert "multipart/x-mixed-replace" in content_type

        # Read just the first chunk to confirm the stream produces JPEG data
        chunk = await response.aread(1024)
        assert b"--frame" in chunk or b"\xff\xd8" in chunk  # JPEG boundary or SOI marker
