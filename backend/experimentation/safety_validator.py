"""
Safety Validator - Validates Experiments for Safety

Ensures experiments are safe to run by checking for:
- Dangerous operations
- Resource abuse
- Security risks
"""

import re
from typing import Dict, Any, List

from utils.logger import get_logger

logger = get_logger(__name__)


class SafetyValidator:
    """Validates experiment safety"""

    def __init__(self):
        # Dangerous patterns
        self.dangerous_imports = [
            'subprocess', 'os.system', 'eval', 'exec',
            'compile', '__import__', 'open.*w', 'shutil.rmtree'
        ]

        self.dangerous_operations = [
            r'os\.remove', r'os\.unlink', r'shutil\.rmtree',
            r'subprocess\.', r'eval\(', r'exec\(',
            r'__import__\(', r'open\(.*["\']w',
            r'socket\.', r'urllib\.request', r'requests\.',
            r'pickle\.load', r'yaml\.load\(', r'input\('
        ]

        logger.info("SafetyValidator initialized")

    def validate(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate experiment safety

        Args:
            experiment: Experiment to validate

        Returns:
            Validation result
        """
        result = {
            'safe': True,
            'risk_level': 'low',
            'warnings': [],
            'blocked_patterns': []
        }

        code = experiment.get('code', '')

        # Check for dangerous patterns
        for pattern in self.dangerous_operations:
            if re.search(pattern, code, re.IGNORECASE):
                result['blocked_patterns'].append(pattern)
                result['safe'] = False
                result['risk_level'] = 'high'

        # Check for suspicious loops
        if 'while True' in code or 'while 1' in code:
            result['warnings'].append("Infinite loop detected")
            result['risk_level'] = 'medium' if result['risk_level'] == 'low' else result['risk_level']

        # Check code length
        if len(code) > 10000:
            result['warnings'].append("Very long code (>10k chars)")
            result['risk_level'] = 'medium' if result['risk_level'] == 'low' else result['risk_level']

        return result
