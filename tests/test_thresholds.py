import sys
import os
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thresholds.rules import ThresholdRule, ThresholdState, ThresholdOperator
from thresholds.evaluator import ThresholdEvaluator
from metrics.normalizer import Metric

class TestThresholdEngine(unittest.TestCase):
    def setUp(self):
        self.rules = [
            ThresholdRule(
                metric_name="test_metric",
                operator=ThresholdOperator.GT,
                warning_threshold=50,
                critical_threshold=80,
                samples_required=3
            ),
             ThresholdRule(
                metric_name="immediate_metric",
                operator=ThresholdOperator.GT,
                warning_threshold=50,
                critical_threshold=80,
                samples_required=1
            )
        ]
        self.evaluator = ThresholdEvaluator(self.rules)

    def create_metric(self, name, value):
        return Metric(
            name=name,
            value=value,
            unit="val",
            device_ip="192.168.1.1",
            timestamp=datetime.utcnow()
        )

    def test_basic_evaluation(self):
        # 1. OK state
        m = self.create_metric("test_metric", 10)
        result = self.evaluator.evaluate(m)
        self.assertIsNone(result) # No transition, starts OK.

        # 2. Warning range (60 > 50), but samples=3
        m = self.create_metric("test_metric", 60)
        
        # Sample 1
        result = self.evaluator.evaluate(m)
        self.assertIsNone(result)
        
        # Sample 2
        result = self.evaluator.evaluate(m)
        self.assertIsNone(result)
        
        # Sample 3 -> Transition to WARNING
        result = self.evaluator.evaluate(m)
        self.assertIsNotNone(result)
        self.assertEqual(result["old_state"], "OK")
        self.assertEqual(result["new_state"], "WARNING")

    def test_recovery(self):
        # Force to WARNING first
        m_warn = self.create_metric("test_metric", 60)
        for _ in range(3):
            self.evaluator.evaluate(m_warn)
            
        # Now recover to OK logic (1 sample required for OK?)
        # My logic defaults to 1 sample for OK.
        m_ok = self.create_metric("test_metric", 10)
        
        result = self.evaluator.evaluate(m_ok)
        self.assertIsNotNone(result)
        self.assertEqual(result["old_state"], "WARNING")
        self.assertEqual(result["new_state"], "OK")

    def test_critical_transition(self):
         # Force to WARNING first
        m_warn = self.create_metric("test_metric", 60)
        for _ in range(3):
            self.evaluator.evaluate(m_warn)
            
        # Now go to CRITICAL (90 > 80). Rule says 3 samples required.
        m_crit = self.create_metric("test_metric", 90)
        
        # Sample 1
        result = self.evaluator.evaluate(m_crit)
        self.assertIsNone(result)
        
         # Sample 2
        result = self.evaluator.evaluate(m_crit)
        self.assertIsNone(result)
        
         # Sample 3 -> Transition
        result = self.evaluator.evaluate(m_crit)
        self.assertIsNotNone(result)
        self.assertEqual(result["old_state"], "WARNING")
        self.assertEqual(result["new_state"], "CRITICAL")
        
    def test_interrupted_transition(self):
        # 2 samples of WARNING, then 1 sample of OK, then 1 sample of WARNING
        m_warn = self.create_metric("test_metric", 60)
        
        self.evaluator.evaluate(m_warn) # 1
        self.evaluator.evaluate(m_warn) # 2
        
        m_ok = self.create_metric("test_metric", 10)
        self.evaluator.evaluate(m_ok) # Reset count?
        
        # Now WARNING again. Should need 3 samples again.
        result = self.evaluator.evaluate(m_warn) # 1
        self.assertIsNone(result) 
        
        self.evaluator.evaluate(m_warn) # 2
        result = self.evaluator.evaluate(m_warn) # 3
        self.assertIsNotNone(result)
        self.assertEqual(result["new_state"], "WARNING")

    def test_immediate_transition(self):
        m = self.create_metric("immediate_metric", 60)
        result = self.evaluator.evaluate(m)
        self.assertIsNotNone(result)
        self.assertEqual(result["new_state"], "WARNING")

if __name__ == '__main__':
    unittest.main()
