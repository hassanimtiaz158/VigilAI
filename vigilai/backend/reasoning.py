"""LLM context reasoning via Groq API.

Builds a structured prompt from detection context and asks LLaMA 3.3 70B
(via Groq free tier) to classify severity, summarize the incident, and
recommend an action. Results are cached by detection pattern to avoid
redundant API calls.
"""

from __future__ import annotations

import json
import os
import uuid
import warnings
from collections import OrderedDict
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq

from models import Detection, Incident

# Load .env from project root (one level up from backend/)
load_dotenv()

# --------------------------------------------------------------------------- #
# Groq client
# --------------------------------------------------------------------------- #
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    warnings.warn(
        "[VigilAI] GROQ_API_KEY not set — LLM reasoning disabled, "
        "falling back to automated analysis."
    )
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --------------------------------------------------------------------------- #
# Cache — avoids calling LLM for duplicate detection patterns (bounded)
# --------------------------------------------------------------------------- #
_MAX_CACHE_SIZE = 200
_reasoning_cache: OrderedDict[str, dict] = OrderedDict()


def _cache_get(key: str) -> dict | None:
    if key in _reasoning_cache:
        _reasoning_cache.move_to_end(key)
        return _reasoning_cache[key]
    return None


def _cache_put(key: str, value: dict) -> None:
    if key in _reasoning_cache:
        _reasoning_cache.move_to_end(key)
    _reasoning_cache[key] = value
    while len(_reasoning_cache) > _MAX_CACHE_SIZE:
        _reasoning_cache.popitem(last=False)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 200
_TEMPERATURE = 0.1


def _build_prompt(
    domain: str,
    detection_summary: list[dict],
    duration_sec: float,
) -> str:
    """Construct the user prompt sent to the LLM.

    The prompt is strictly anchored to the active domain so the LLM
    cannot hallucinate references to other domains (e.g. saying
    "school entrance" when the domain is "construction").
    """
    domain_contexts = {
        "construction": (
            "You are monitoring a construction site. Focus on PPE compliance, "
            "missing helmets or safety vests, and worker safety hazards. "
            "Construction workers require proper protective equipment at all times."
        ),
        "school": (
            "You are monitoring a school campus. Focus on unauthorized persons, "
            "weapons, crowd density, and student safety. Schools must maintain "
            "a safe environment for children and staff."
        ),
        "elderly": (
            "You are monitoring an elderly care facility. Focus on falls, "
            "prolonged stillness, wandering, and resident wellbeing. "
            "Elderly residents are vulnerable and require prompt response."
        ),
        "child": (
            "You are monitoring child safety. Focus on unattended children, "
            "falls, restricted zone entry, and children near roads. "
            "Children require faster response than adults."
        ),
        "public": (
            "You are monitoring a public space. Focus on unattended bags, "
            "crowd anomalies, loitering, and suspicious activity. "
            "Public areas require vigilance for potential threats."
        ),
    }

    context = domain_contexts.get(
        domain,
        f"You are monitoring a {domain} environment.",
    )

    return (
        f"DOMAIN: {domain.upper()}\n"
        f"{context}\n"
        f"Analyze ONLY in the context of {domain}. "
        f"Never reference any other domain.\n\n"
        f"DETECTIONS: {json.dumps(detection_summary)}\n"
        f"DURATION: {duration_sec:.1f} seconds\n\n"
        f"RULES:\n"
        f"- Describe what is happening specifically in the {domain} context.\n"
        f"- Do NOT mention any location or context from a different domain.\n"
        f"- Severity: CRITICAL if immediate danger, HIGH if risk, "
        f"MEDIUM if caution needed, LOW if informational only.\n"
        f"- False positive %: how likely this is a misclassification.\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
        '  "summary": "one sentence describing the incident in the domain context",\n'
        '  "recommended_action": "one sentence for what should be done",\n'
        '  "false_positive_pct": integer 0-100\n'
        "}"
    )


def _parse_llm_response(raw: str) -> dict:
    """Parse the LLM's JSON response, tolerating markdown fences.

    Returns a dict with keys: severity, summary, recommended_action,
    false_positive_pct.
    """
    text = raw.strip()

    # Strip optional markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first (```json) and last (```) lines
        text = "\n".join(lines[1:-1]).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first {...} block from the text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {raw[:200]}")


def _fallback_incident(
    domain: str,
    detections: list[Detection],
    duration_sec: float,
    reason: str,
) -> Incident:
    """Return a safe MEDIUM-severity fallback when the LLM is unavailable.

    If `detections` is empty, a placeholder Detection is used so the
    Incident still satisfies Pydantic's min_length=1 constraint.
    """
    safe_detections = detections or [
        Detection(label="unknown", confidence=0.0, bbox=[0, 0, 1, 1], zone="unknown")
    ]
    return Incident(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(),
        domain=domain,
        detections=safe_detections,
        duration_sec=duration_sec,
        severity="MEDIUM",
        summary=f"Automated analysis unavailable ({reason}). Manual review recommended.",
        recommended_action="Review footage manually to assess the situation.",
        false_positive_pct=50,
    )


def analyze_incident(
    detections: list[Detection],
    domain: str,
    duration_sec: float,
) -> Incident:
    """Analyze a set of detections and return a structured Incident.

    Checks the cache first. On cache miss, calls the Groq LLM, parses the
    JSON response, caches the result, and returns a fully constructed
    Incident.
    """
    # --- Build cache key (BUG 5 fix: domain is always included) ----------
    cache_key = (
        f"{domain}:{sorted([d.label for d in detections])}:"
        f"{int(duration_sec / 10) * 10}"
    )

    cached = _cache_get(cache_key)
    if cached is not None:
        # Validate cached values before constructing Incident
        severity = cached["severity"]
        if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            severity = "MEDIUM"
        fp = max(0, min(100, int(cached["false_positive_pct"])))
        return Incident(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            domain=domain,
            detections=detections,
            duration_sec=duration_sec,
            severity=severity,
            summary=cached["summary"],
            recommended_action=cached["recommended_action"],
            false_positive_pct=fp,
        )

    # --- Guard: no client configured -------------------------------------
    if client is None:
        return _fallback_incident(
            domain, detections, duration_sec, "GROQ_API_KEY not set"
        )

    # --- Build detection summary for the prompt --------------------------
    detection_summary = [
        {
            "object": d.label,
            "confidence": f"{d.confidence:.2f}",
            "zone": d.zone,
        }
        for d in detections
    ]

    prompt = _build_prompt(domain, detection_summary, duration_sec)

    # --- Call Groq LLM ----------------------------------------------------
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 — catch any Groq/network error
        return _fallback_incident(
            domain, detections, duration_sec, f"LLM error: {exc}"
        )

    # --- Parse response ---------------------------------------------------
    try:
        parsed = _parse_llm_response(raw)
        result = {
            "severity": parsed["severity"],
            "summary": parsed["summary"],
            "recommended_action": parsed["recommended_action"],
            "false_positive_pct": int(parsed["false_positive_pct"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        return _fallback_incident(
            domain, detections, duration_sec, f"parse error: {exc}"
        )

    # --- Validate severity enum ------------------------------------------
    valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if result["severity"] not in valid_severities:
        result["severity"] = "MEDIUM"

    # --- Clamp false_positive_pct ----------------------------------------
    result["false_positive_pct"] = max(0, min(100, result["false_positive_pct"]))

    # --- Cache the validated result ---------------------------------------
    _cache_put(cache_key, result)

    # --- Return full Incident ---------------------------------------------
    return Incident(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(),
        domain=domain,
        detections=detections,
        duration_sec=duration_sec,
        severity=result["severity"],
        summary=result["summary"],
        recommended_action=result["recommended_action"],
        false_positive_pct=result["false_positive_pct"],
    )
