from typing import List, Dict, Optional, Tuple
from thresholds.rules import ThresholdRule, ThresholdState
from thresholds.state_manager import ThresholdStateManager
from metrics.normalizer import Metric

class ThresholdEvaluator:
    """
    Evaluates metrics against rules and manages state transitions.
    """
    def __init__(self, rules: List[ThresholdRule]):
        self.rules_map: Dict[str, ThresholdRule] = {r.metric_name: r for r in rules}
        self.state_manager = ThresholdStateManager()
        
    def evaluate(self, metric: Metric) -> Optional[Dict]:
        """
        Evaluate a metric and return state transition info if any.
        Returns None if no rule exists or no transition occurred.
        Return dict: {
            "device_ip": str,
            "metric_name": str,
            "old_state": str,
            "new_state": str,
            "value": float,
            "timestamp": str
        }
        """
        if metric.name not in self.rules_map:
            return None
            
        rule = self.rules_map[metric.name]
        
        # Determine tentative state based on value alone
        tentative_state = rule.evaluate_state(metric.value)
        
        # Update state manager
        transition = self.state_manager.update_state(
            device_ip=metric.device_ip,
            metric_name=metric.name,
            tentative_state=tentative_state,
            rule=rule,
            value=metric.value
        )
        
        if transition:
            old_state, new_state = transition
            return {
                "device_ip": metric.device_ip,
                "metric_name": metric.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat()
            }
            
        return None
