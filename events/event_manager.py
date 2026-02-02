from datetime import datetime
from typing import List, Dict, Optional
from events.event_model import Event, EventSeverity

class EventManager:
    """
    Manages the creation and storage of system events from state transitions.
    """
    def __init__(self, max_history: int = 1000):
        self._events: List[Event] = []
        self._max_history = max_history

    def add_transition(self, transition: Dict) -> Event:
        """
        Converts a state transition dictionary into an Event object.
        
        Args:
            transition: A dictionary containing transition details:
                {
                    "device_ip": str,
                    "metric_name": str,
                    "old_state": str,
                    "new_state": str,
                    "value": float,
                    "timestamp": str (isoformat) or datetime
                }
                
        Returns:
            The created Event object.
            
        Raises:
            ValueError: If the transition dictionary is invalid or missing keys.
        """
        required_keys = ["device_ip", "metric_name", "new_state", "value"]
        missing = [key for key in required_keys if key not in transition]
        if missing:
            raise ValueError(f"Invalid transition data. Missing keys: {missing}")

        try:
            # Parse severity from new_state
            # Assuming new_state matches EventSeverity values (OK, WARNING, CRITICAL)
            severity_str = transition["new_state"]
            try:
                severity = EventSeverity(severity_str)
            except ValueError:
                # Fallback or strict fail? 
                # User wants "Fail fast", so let's allow it to bubble up if it's a completely unknown state,
                # but maybe the ThresholdEngine uses strings that match exactly.
                # Let's trust the input per instructions "Severity should come from new_state only".
                raise ValueError(f"Invalid severity state: {severity_str}")

            # Create message deterministically
            metric_name = transition["metric_name"]
            value = transition["value"]
            message = f"{metric_name} entered {severity_str} state (value={value})"

            # Timestamp handling
            ts = transition.get("timestamp", datetime.utcnow())
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.utcnow() # Fallback if parsing fails? Or strictly fail?
                    # valid isoformat is expected from threshold engine.
                    
            event = Event(
                device_ip=transition["device_ip"],
                metric_name=metric_name,
                severity=severity,
                message=message,
                value=float(value),
                timestamp=ts
            )
            
            self._add_event(event)
            return event

        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"Failed to process transition: {str(e)}")

    def _add_event(self, event: Event):
        """Internal method to add event and maintain history limit."""
        self._events.append(event)
        
        # Maintain max history
        if len(self._events) > self._max_history:
            # Remove oldest
            self._events.pop(0)

    def get_recent_events(self, limit: int = 50) -> List[Event]:
        """
        Get recent events sorted by timestamp descending.
        
        Args:
            limit: Maximum number of events to return.
            
        Returns:
            List of Event objects.
        """
        # Sort by timestamp descending
        sorted_events = sorted(self._events, key=lambda e: e.timestamp, reverse=True)
        return sorted_events[:limit]
