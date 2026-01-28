"""
Surprise System - Darwin reacts to unexpected events
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class SurpriseLevel(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class SurpriseSystem:
    def __init__(self):
        self.surprises: List[Dict] = []
        self.expectations: Dict[str, any] = {}

    def set_expectation(self, key: str, expected_value: any):
        self.expectations[key] = expected_value

    def check_surprise(self, key: str, actual_value: any) -> Optional[Dict]:
        if key not in self.expectations:
            return None

        expected = self.expectations[key]

        if expected != actual_value:
            # Determine surprise level
            if isinstance(expected, (int, float)) and isinstance(actual_value, (int, float)):
                diff_percent = abs(actual_value - expected) / max(expected, 1) * 100

                if diff_percent > 100:
                    level = SurpriseLevel.EXTREME
                elif diff_percent > 50:
                    level = SurpriseLevel.HIGH
                elif diff_percent > 20:
                    level = SurpriseLevel.MODERATE
                else:
                    level = SurpriseLevel.MILD
            else:
                level = SurpriseLevel.MODERATE

            surprise = {
                'key': key,
                'expected': expected,
                'actual': actual_value,
                'level': level.value,
                'timestamp': datetime.now().isoformat()
            }

            self.surprises.append(surprise)
            return surprise

        return None

    def get_recent_surprises(self, limit: int = 10) -> List[Dict]:
        return self.surprises[-limit:]

    def get_statistics(self) -> Dict:
        from collections import Counter
        levels = Counter(s['level'] for s in self.surprises)

        return {
            'total_surprises': len(self.surprises),
            'by_level': dict(levels)
        }
