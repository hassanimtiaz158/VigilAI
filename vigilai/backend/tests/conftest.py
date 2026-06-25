"""Shared pytest fixtures for VigilAI backend tests."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture
async def client():
    """Yield an httpx.AsyncClient wired to the FastAPI app via ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def sample_frame():
    """Return a small blank BGR frame (360x640x3)."""
    return np.zeros((360, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_detection():
    """Return a valid Detection dict."""
    return {
        "label": "person",
        "confidence": 0.91,
        "bbox": [100, 100, 200, 300],
        "zone": "open_area",
    }


@pytest.fixture
def sample_incident():
    """Return a valid Incident dict."""
    return {
        "id": "abc12345",
        "timestamp": datetime.now().isoformat(),
        "domain": "school",
        "detections": [
            {
                "label": "person",
                "confidence": 0.91,
                "bbox": [100, 100, 200, 300],
                "zone": "open_area",
            }
        ],
        "duration_sec": 5.0,
        "severity": "CRITICAL",
        "summary": "Person detected in restricted zone",
        "recommended_action": "Dispatch security immediately",
        "false_positive_pct": 8,
    }


# --------------------------------------------------------------------------- #
# Mock landmark helpers for fall-detection unit tests
# --------------------------------------------------------------------------- #
def _make_fallen_landmarks():
    """Return a mock pose_result where the person has fallen (nose below hips)."""
    # Fallen: nose_y (0.8) > avg_hip_y ((0.3+0.3)/2 = 0.3)
    lm = {
        0: SimpleNamespace(y=0.8),   # nose
        23: SimpleNamespace(y=0.3),  # left hip
        24: SimpleNamespace(y=0.3),  # right hip
    }
    return SimpleNamespace(landmark=lm, pose_landmarks=None)


def _make_standing_landmarks():
    """Return a mock pose_result where the person is standing (nose above hips)."""
    # Standing: nose_y (0.2) < avg_hip_y ((0.6+0.6)/2 = 0.6)
    lm = {
        0: SimpleNamespace(y=0.2),   # nose
        23: SimpleNamespace(y=0.6),  # left hip
        24: SimpleNamespace(y=0.6),  # right hip
    }
    return SimpleNamespace(landmark=lm, pose_landmarks=None)


@pytest.fixture
def fallen_landmarks():
    return _make_fallen_landmarks()


@pytest.fixture
def standing_landmarks():
    return _make_standing_landmarks()
