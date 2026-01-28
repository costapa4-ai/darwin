"""
Governance Agent: Bounded Autonomy and Policy Enforcement

Monitors Darwin's actions for policy compliance and provides
safety guardrails as Darwin becomes more autonomous.

Based on research:
- "Bounded autonomy" architectures with operational limits
- Escalation paths to humans for high-stakes decisions
- Comprehensive audit trails

Key features:
1. Policy-based action validation
2. Cost and resource limits
3. Security constraints
4. Audit logging
5. Anomaly detection
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class PolicySeverity(Enum):
    """Severity levels for policy violations"""
    INFO = "info"          # Logged, no action
    WARNING = "warning"    # Logged, user notified
    BLOCK = "block"        # Action blocked
    CRITICAL = "critical"  # Action blocked, system alert


class ActionCategory(Enum):
    """Categories of actions for policy matching"""
    CODE_CHANGE = "code_change"
    FILE_OPERATION = "file_operation"
    NETWORK = "network"
    DATABASE = "database"
    TOOL_USE = "tool_use"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"


@dataclass
class Policy:
    """A governance policy"""
    name: str
    description: str
    category: ActionCategory
    condition: str  # Python expression to evaluate
    severity: PolicySeverity
    action: str  # What to do: "block", "warn", "log", "escalate"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['category'] = self.category.value
        result['severity'] = self.severity.value
        return result


@dataclass
class AuditEntry:
    """An entry in the audit log"""
    timestamp: datetime
    action_type: str
    action_details: Dict[str, Any]
    governance_decision: str  # approved, blocked, warned
    policy_triggered: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class GovernanceAgent:
    """
    Governance Agent for policy enforcement and bounded autonomy.

    Monitors Darwin's actions, enforces limits, and maintains
    comprehensive audit trails.
    """

    # Default policies for safe autonomous operation
    DEFAULT_POLICIES = {
        # Resource limits
        "max_file_changes": Policy(
            name="max_file_changes",
            description="Limit file changes per wake cycle",
            category=ActionCategory.CODE_CHANGE,
            condition="context.get('file_changes_this_cycle', 0) > 10",
            severity=PolicySeverity.BLOCK,
            action="block"
        ),
        "max_daily_api_calls": Policy(
            name="max_daily_api_calls",
            description="Limit API calls per day",
            category=ActionCategory.EXTERNAL_API,
            condition="context.get('daily_api_calls', 0) > 1000",
            severity=PolicySeverity.WARNING,
            action="warn"
        ),
        "max_hourly_api_calls": Policy(
            name="max_hourly_api_calls",
            description="Limit API calls per hour",
            category=ActionCategory.EXTERNAL_API,
            condition="context.get('hourly_api_calls', 0) > 100",
            severity=PolicySeverity.BLOCK,
            action="block"
        ),

        # Security constraints
        "no_production_data": Policy(
            name="no_production_data",
            description="Block access to production data",
            category=ActionCategory.DATABASE,
            condition="'production' in str(action.get('target', '')).lower()",
            severity=PolicySeverity.CRITICAL,
            action="block"
        ),
        "no_credentials": Policy(
            name="no_credentials",
            description="Block operations involving credentials",
            category=ActionCategory.FILE_OPERATION,
            condition="any(w in str(action).lower() for w in ['password', 'secret', 'credential', 'api_key', '.env'])",
            severity=PolicySeverity.CRITICAL,
            action="block"
        ),
        "no_destructive": Policy(
            name="no_destructive",
            description="Block destructive operations",
            category=ActionCategory.SYSTEM,
            condition="any(w in str(action).lower() for w in ['rm -rf', 'drop table', 'delete *', 'format', 'truncate'])",
            severity=PolicySeverity.CRITICAL,
            action="block"
        ),

        # Approval requirements
        "require_approval_architecture": Policy(
            name="require_approval_architecture",
            description="Require human approval for architecture changes",
            category=ActionCategory.CODE_CHANGE,
            condition="action.get('is_architecture_change', False)",
            severity=PolicySeverity.WARNING,
            action="escalate"
        ),
        "require_approval_security": Policy(
            name="require_approval_security",
            description="Require human approval for security-related changes",
            category=ActionCategory.CODE_CHANGE,
            condition="'security' in str(action.get('tags', [])).lower()",
            severity=PolicySeverity.WARNING,
            action="escalate"
        ),

        # Rate limiting
        "rate_limit_tool_creation": Policy(
            name="rate_limit_tool_creation",
            description="Limit tool creation rate",
            category=ActionCategory.TOOL_USE,
            condition="context.get('tools_created_today', 0) > 5",
            severity=PolicySeverity.WARNING,
            action="warn"
        )
    }

    def __init__(
        self,
        custom_policies: Optional[Dict[str, Policy]] = None,
        audit_retention_days: int = 30,
        max_audit_entries: int = 10000
    ):
        """
        Initialize the Governance Agent.

        Args:
            custom_policies: Additional policies to apply
            audit_retention_days: Days to retain audit entries
            max_audit_entries: Maximum audit entries to keep
        """
        # Merge default and custom policies
        self.policies = dict(self.DEFAULT_POLICIES)
        if custom_policies:
            self.policies.update(custom_policies)

        # Audit log
        self.audit_log: List[AuditEntry] = []
        self.audit_retention_days = audit_retention_days
        self.max_audit_entries = max_audit_entries

        # Runtime counters (reset periodically)
        self.counters = defaultdict(int)
        self.counter_reset_times: Dict[str, datetime] = {}

        # Statistics
        self.total_validations = 0
        self.blocks = 0
        self.warnings = 0
        self.escalations = 0

    async def validate_action(
        self,
        action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate an action against governance policies.

        Args:
            action: The action to validate
            context: Runtime context (counters, state)

        Returns:
            Tuple of (approved: bool, reason: str, policy_name: Optional[str])
        """
        self.total_validations += 1
        context = context or {}

        # Merge runtime counters into context
        full_context = {**context, **dict(self.counters)}

        # Check each policy
        for policy_name, policy in self.policies.items():
            if not policy.enabled:
                continue

            try:
                # Evaluate policy condition
                triggered = eval(
                    policy.condition,
                    {"action": action, "context": full_context}
                )

                if triggered:
                    # Log the trigger
                    await self._audit(
                        action_type=str(policy.category.value),
                        action_details=action,
                        decision=policy.action,
                        policy_triggered=policy_name
                    )

                    if policy.action == "block":
                        self.blocks += 1
                        return False, f"Blocked by policy: {policy.description}", policy_name

                    elif policy.action == "warn":
                        self.warnings += 1
                        logger.warning(f"Policy warning: {policy.description}")
                        # Continue but log warning

                    elif policy.action == "escalate":
                        self.escalations += 1
                        return False, f"Requires approval: {policy.description}", policy_name

            except Exception as e:
                logger.error(f"Policy evaluation error ({policy_name}): {e}")
                continue

        # Action approved
        await self._audit(
            action_type=action.get('type', 'unknown'),
            action_details=action,
            decision="approved"
        )

        return True, "Action approved", None

    async def _audit(
        self,
        action_type: str,
        action_details: Dict[str, Any],
        decision: str,
        policy_triggered: Optional[str] = None
    ):
        """Add an entry to the audit log"""
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            action_type=action_type,
            action_details=action_details,
            governance_decision=decision,
            policy_triggered=policy_triggered
        )

        self.audit_log.append(entry)

        # Cleanup old entries
        await self._cleanup_audit_log()

    async def _cleanup_audit_log(self):
        """Remove old audit entries"""
        if len(self.audit_log) > self.max_audit_entries:
            # Keep most recent entries
            self.audit_log = self.audit_log[-self.max_audit_entries:]

        # Remove entries older than retention period
        cutoff = datetime.utcnow() - timedelta(days=self.audit_retention_days)
        self.audit_log = [
            e for e in self.audit_log
            if e.timestamp > cutoff
        ]

    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a runtime counter"""
        self.counters[counter_name] += amount

    def reset_counter(self, counter_name: str):
        """Reset a runtime counter"""
        self.counters[counter_name] = 0
        self.counter_reset_times[counter_name] = datetime.utcnow()

    def reset_hourly_counters(self):
        """Reset counters that should reset hourly"""
        hourly_counters = [
            'hourly_api_calls',
            'file_changes_this_hour'
        ]
        for counter in hourly_counters:
            self.reset_counter(counter)

    def reset_daily_counters(self):
        """Reset counters that should reset daily"""
        daily_counters = [
            'daily_api_calls',
            'file_changes_today',
            'tools_created_today'
        ]
        for counter in daily_counters:
            self.reset_counter(counter)

    def reset_cycle_counters(self):
        """Reset counters at the start of each wake/sleep cycle"""
        cycle_counters = [
            'file_changes_this_cycle',
            'api_calls_this_cycle'
        ]
        for counter in cycle_counters:
            self.reset_counter(counter)

    def add_policy(self, name: str, policy: Policy):
        """Add or update a policy"""
        self.policies[name] = policy
        logger.info(f"Policy added/updated: {name}")

    def disable_policy(self, name: str):
        """Disable a policy"""
        if name in self.policies:
            self.policies[name].enabled = False
            logger.info(f"Policy disabled: {name}")

    def enable_policy(self, name: str):
        """Enable a policy"""
        if name in self.policies:
            self.policies[name].enabled = True
            logger.info(f"Policy enabled: {name}")

    def get_audit_log(
        self,
        limit: int = 100,
        decision_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent audit entries"""
        entries = self.audit_log

        if decision_filter:
            entries = [e for e in entries if e.governance_decision == decision_filter]

        return [e.to_dict() for e in entries[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """Get governance statistics"""
        return {
            "total_validations": self.total_validations,
            "blocks": self.blocks,
            "warnings": self.warnings,
            "escalations": self.escalations,
            "approval_rate": (
                (self.total_validations - self.blocks) / self.total_validations
                if self.total_validations > 0 else 1.0
            ),
            "policies_count": len(self.policies),
            "enabled_policies": sum(1 for p in self.policies.values() if p.enabled),
            "audit_entries": len(self.audit_log),
            "counters": dict(self.counters)
        }

    def get_policies(self) -> Dict[str, Dict]:
        """Get all policies"""
        return {name: policy.to_dict() for name, policy in self.policies.items()}


# Convenience decorator for governance-wrapped functions
def governed(category: ActionCategory = ActionCategory.SYSTEM):
    """Decorator to wrap functions with governance validation"""
    def decorator(func):
        async def wrapper(*args, governance_agent: Optional[GovernanceAgent] = None, **kwargs):
            if governance_agent:
                action = {
                    "type": func.__name__,
                    "category": category.value,
                    "args": str(args)[:200],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                }

                approved, reason, policy = await governance_agent.validate_action(action)

                if not approved:
                    return {"success": False, "blocked": True, "reason": reason, "policy": policy}

            return await func(*args, **kwargs)
        return wrapper
    return decorator
