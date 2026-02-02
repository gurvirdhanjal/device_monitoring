from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple
from thresholds.rules import ThresholdState, ThresholdRule

@dataclass
class MetricState:
    """
    Tracks the state of a single metric for a single device.
    """
    current_state: ThresholdState = ThresholdState.OK
    pending_state: Optional[ThresholdState] = None
    consecutive_breach_count: int = 0
    last_update: datetime = field(default_factory=datetime.utcnow)
    last_value: Optional[float] = None

class ThresholdStateManager:
    """
    Manages state transitions for metrics.
    """
    def __init__(self):
        # Key: (device_ip, metric_name) -> MetricState
        self._states: Dict[Tuple[str, str], MetricState] = {}

    def get_state(self, device_ip: str, metric_name: str) -> MetricState:
        key = (device_ip, metric_name)
        if key not in self._states:
            self._states[key] = MetricState()
        return self._states[key]

    def update_state(self, device_ip: str, metric_name: str, 
                     tentative_state: ThresholdState, 
                     rule: ThresholdRule,
                     value: float) -> Optional[Tuple[ThresholdState, ThresholdState]]:
        """
        Update the state based on new observation.
        Returns None if no transition, or (old_state, new_state) if transition occurred.
        """
        state_obj = self.get_state(device_ip, metric_name)
        current = state_obj.current_state
        
        # Logic for state transition with hysteresis/consecutive requirements.
        
        # If tentative matches current, we are stable.
        if tentative_state == current:
            state_obj.pending_state = None
            state_obj.consecutive_breach_count = 0
            state_obj.last_value = value
            state_obj.last_update = datetime.utcnow()
            return None
            
        # If tentative is different from current.
        # Check if it matches the pending state we are building up.
        if tentative_state == state_obj.pending_state:
            state_obj.consecutive_breach_count += 1
        else:
            # New potential state, reset count to 1
            state_obj.pending_state = tentative_state
            state_obj.consecutive_breach_count = 1
            
        # Check if we met the requirement
        # If transitioning TO OK (Recovery), usually immediate?
        # User said: "Support multi-sample evaluation (e.g. 3 consecutive breaches)"
        # This implies breaches (Bad states) need multi-sample.
        # Let's assume OK (Recovery) is immediate for now to be safe, OR follow the same rule.
        # The rule has `samples_required`.
        
        target_samples = rule.samples_required
        
        # If we are transitioning FROM a worse state TO a better state (Recovery), 
        # often needed to be stable? 
        # Requirement says "3 consecutive breaches". Doesn't satisfy "3 consecutive recoveries".
        # I'll default to 1 sample for recovery to OK unless otherwise specified.
        # But if transitioning Warning -> Critical (worse), we need samples.
        # If transitioning Critical -> Warning (better), maybe immediate?
        
        # Heuristic:
        # If tentative_state == OK, require 1 sample (immediate recovery).
        # Else, use rule.samples_required.
        
        if tentative_state == ThresholdState.OK:
            required = 1
        else:
            required = target_samples
            
        if state_obj.consecutive_breach_count >= required:
            # Transition!
            old_state = current
            state_obj.current_state = tentative_state
            state_obj.pending_state = None
            state_obj.consecutive_breach_count = 0
            state_obj.last_update = datetime.utcnow()
            state_obj.last_value = value
            return (old_state, tentative_state)
            
        return None
