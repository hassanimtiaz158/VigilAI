"""Severity scoring and alert deduplication."""

from models import Incident


class AlertManager:
    def __init__(self):
        self.recent_alerts: list[Incident] = []

    def should_emit(self, incident: Incident) -> bool:
        # TODO: implement deduplication logic
        return True

    def score_severity(self, incident: Incident) -> Incident:
        # TODO: implement severity scoring override
        return incident
