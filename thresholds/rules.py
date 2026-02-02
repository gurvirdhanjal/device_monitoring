from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Callable
import operator

class ThresholdState(Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class ThresholdOperator(Enum):
    GT = ">"
    LT = "<"
    GE = ">="
    LE = "<="
    EQ = "=="
    NE = "!="

    def evaluate(self, value: Any, threshold: Any) -> bool:
        ops = {
            self.GT: operator.gt,
            self.LT: operator.lt,
            self.GE: operator.ge,
            self.LE: operator.le,
            self.EQ: operator.eq,
            self.NE: operator.ne,
        }
        return ops[self](value, threshold)

@dataclass
class ThresholdRule:
    """
    Defines a threshold rule for a specific metric.
    """
    metric_name: str
    operator: ThresholdOperator
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    samples_required: int = 1
    
    def evaluate_state(self, value: float) -> ThresholdState:
        """
        Evaluate a single value against the thresholds to determine the tentative state.
        This does NOT account for multi-sample history, only the immediate value.
        """
        # CRITICAL check implies severity > WARNING, so check CRITICAL first if logical
        # But it depends on the operator.
        # e.g. for Latency > 100 (Warn), > 200 (Crit)
        # 150 > 200 False, 150 > 100 True -> Warning.
        # 250 > 200 True -> Critical.
        
        # We need to handle different operator logic.
        # Simple heuristic: Check Critical first.
        
        if self.critical_threshold is not None:
            if self.operator.evaluate(value, self.critical_threshold):
                return ThresholdState.CRITICAL
                
        if self.warning_threshold is not None:
            if self.operator.evaluate(value, self.warning_threshold):
                return ThresholdState.WARNING
                
        return ThresholdState.OK
