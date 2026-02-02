import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional

class EventSeverity(Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

@dataclass
class Event:
    """
    Represents a system event generated from a threshold transition.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_ip: str = ""
    metric_name: str = ""
    severity: EventSeverity = EventSeverity.OK
    message: str = ""
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "device_ip": self.device_ip,
            "metric_name": self.metric_name,
            "severity": self.severity.value,
            "message": self.message,
            "value": self.value,
            "timestamp": self.timestamp.isoformat()
        }
