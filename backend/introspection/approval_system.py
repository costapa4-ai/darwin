"""
Approval System: Manages change requests and approval workflow
Handles approval queue, auto-approval logic, and change history
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict, field
import json
import hashlib
from pathlib import Path

from introspection.code_generator import GeneratedCode
from introspection.code_validator import ValidationResult


# =============================================================================
# PROTECTED FILES - CRITICAL SYSTEM FILES THAT REQUIRE EXTRA SCRUTINY
# =============================================================================
PROTECTED_FILES = {
    'main.py': {
        'description': 'FastAPI application entry point',
        'auto_approve': False,  # NEVER auto-approve
        'min_score': 95,        # Require 95/100 minimum
        'max_risk': 'low',      # Only low risk allowed
        'reason': 'Critical - Server entry point'
    },
    'config.py': {
        'description': 'System configuration',
        'auto_approve': False,
        'min_score': 95,
        'max_risk': 'low',
        'reason': 'Critical - Configuration management'
    },
    'Dockerfile': {
        'description': 'Container definition',
        'auto_approve': False,
        'min_score': 98,
        'max_risk': 'low',
        'reason': 'Critical - Container infrastructure'
    },
    'docker-compose.yml': {
        'description': 'Service orchestration',
        'auto_approve': False,
        'min_score': 98,
        'max_risk': 'low',
        'reason': 'Critical - Service configuration'
    },
    'requirements.txt': {
        'description': 'Python dependencies',
        'auto_approve': False,
        'min_score': 90,
        'max_risk': 'medium',
        'reason': 'Important - Dependency management'
    },
    'pyproject.toml': {
        'description': 'Project configuration',
        'auto_approve': False,
        'min_score': 90,
        'max_risk': 'medium',
        'reason': 'Important - Project metadata'
    }
}


def is_protected_file(file_path: str) -> bool:
    """Check if file is in protected files list"""
    return file_path in PROTECTED_FILES


def get_protection_rules(file_path: str) -> Optional[Dict]:
    """Get protection rules for a file"""
    return PROTECTED_FILES.get(file_path)


class ApprovalStatus(Enum):
    """Status of a change request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ChangeRequest:
    """Represents a change awaiting approval"""
    id: str
    generated_code: Dict  # GeneratedCode as dict
    validation: Dict  # ValidationResult as dict
    status: str = ApprovalStatus.PENDING.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reviewed_at: Optional[str] = None
    reviewer_comment: Optional[str] = None
    applied_at: Optional[str] = None
    rollback_id: Optional[str] = None

    def should_auto_approve(self) -> bool:
        """
        Determine if change can be auto-approved

        NEW RULE: Auto-approve new tool files if:
        - File doesn't exist (is_new_file = True)
        - File is in tools/ directory
        - Validation passed with score >= 75 (lower threshold for new files)
        - No security issues

        Criteria for auto-approval (existing files):
        - Validation passed
        - NOT a protected file (main.py, Dockerfile, etc)
        - Risk is low OR (risk is medium AND score >= 90)
        - Score >= 85 (high quality)
        - No security issues
        """
        if not self.validation['valid']:
            return False

        file_path = self.generated_code['file_path']
        risk_level = self.generated_code['risk_level']
        score = self.validation['score']
        is_new_file = self.generated_code.get('is_new_file', False)

        # =========================================================================
        # 🆕 NEW: Auto-approve new tools with lower requirements + TOOL TESTS
        # =========================================================================
        if is_new_file and 'tools/' in file_path:
            # NEW RULE: Auto-approve if tool passed automated tests
            tool_test_passed = self.generated_code.get('tool_test_passed', None)

            if tool_test_passed is True:
                # Tool passed all automated tests - auto-approve even with lower score
                print(f"   ✅ AUTO-APPROVE: Tool passed automated tests (score: {score})")
                return True
            elif tool_test_passed is False:
                # Tool FAILED automated tests - require manual approval
                print(f"   ❌ MANUAL APPROVAL REQUIRED: Tool failed automated tests")
                return False

            # Fallback: No test results available, use original criteria
            # Lower requirements for new tools:
            # - Score >= 75 (instead of 85)
            # - No security issues
            # - Risk can be anything (new file = safe, can't break existing code)

            if score >= 75 and len(self.validation['security_issues']) == 0:
                print(f"   ✅ AUTO-APPROVE: New tool file {file_path} (score: {score})")
                return True

        # =========================================================================
        # CRITICAL: Check if file is protected
        # =========================================================================
        if is_protected_file(file_path):
            rules = get_protection_rules(file_path)

            # Protected files NEVER auto-approve by default
            if not rules['auto_approve']:
                print(f"   🛡️ PROTECTED FILE: {file_path} - Manual approval required")
                print(f"   📋 Reason: {rules['reason']}")
                return False

            # If auto-approve allowed (shouldn't happen), check stricter criteria
            if score < rules['min_score']:
                print(f"   ⚠️ Score {score} below minimum {rules['min_score']} for protected file")
                return False

            if risk_level != rules['max_risk']:
                print(f"   ⚠️ Risk {risk_level} exceeds maximum {rules['max_risk']} for protected file")
                return False

        # =========================================================================
        # Normal auto-approval logic for non-protected files
        # =========================================================================
        if risk_level == 'high':
            return False
        elif risk_level == 'medium' and score < 90:
            return False

        if score < 85:
            return False

        if len(self.validation['security_issues']) > 0:
            return False

        # Auto-approve if all criteria met
        return True

    def _is_safe_change(self) -> bool:
        """
        Check if change is safe for auto-approval

        Safe changes:
        - Only comments/docstrings added
        - Only logging added
        - Only type hints added
        - Only formatting changes
        - Documentation only
        """
        diff = self.generated_code.get('diff_unified', '')

        # Count actual code changes (excluding comments/whitespace)
        code_changes = 0
        for line in diff.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                stripped = line[1:].strip()
                # Skip comments, docstrings, empty lines
                if stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                    code_changes += 1

        # If less than 5 lines of actual code changed, consider safe
        return code_changes < 5


class ApprovalQueue:
    """
    Manages queue of pending change approvals
    Handles auto-approval, manual approval, and history
    """

    def __init__(self, storage_path: str = "/app/data/approvals"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.pending: List[ChangeRequest] = []
        self.history: List[ChangeRequest] = []

        self._load_state()

    def add(self, generated_code: GeneratedCode, validation: ValidationResult) -> Dict[str, Any]:
        """
        Add a new change request to the queue

        Args:
            generated_code: Generated code from CodeGenerator
            validation: Validation result from CodeValidator

        Returns:
            {
                'change_id': str,
                'status': str,
                'auto_approved': bool,
                'message': str
            }
        """
        # =========================================================================
        # 🆕 QUALITY THRESHOLD: Auto-reject extremely low quality code
        # =========================================================================
        score = validation.score

        # Reject code with score < 40 (extremely low quality)
        if score < 40:
            print(f"❌ AUTO-REJECT: Extremely low quality score ({score}/100)")
            print(f"   File: {generated_code.file_path}")
            print(f"   Reason: Quality too low for any approval consideration")

            # 🆕 ANALYZE REJECTED CODE TO IMPROVE FUTURE GENERATION
            from introspection.quality_analyzer import QualityAnalyzer

            analyzer = QualityAnalyzer()
            analysis = analyzer.analyze_rejected_code(
                generated_code=self._to_dict(generated_code),
                validation=self._to_dict(validation),
                rejection_reason=f"Quality score {score}/100 below threshold (40)"
            )

            print(f"\n📊 Quality Analysis Results:")
            print(f"   Patterns found: {len(analysis['patterns_found'])}")
            print(f"   Root causes: {len(analysis['root_causes'])}")
            print(f"   Recommendations: {len(analysis['recommendations'])}")

            # Create rejected change and add directly to history
            change = ChangeRequest(
                id=self._generate_id(),
                generated_code=self._to_dict(generated_code),
                validation=self._to_dict(validation),
                status=ApprovalStatus.REJECTED.value,
                reviewed_at=datetime.now().isoformat(),
                reviewer_comment=f"Auto-rejected: Quality score {score}/100 is below minimum threshold of 40. Code requires significant improvement before resubmission.\n\nAnalysis: {analysis.get('root_causes', [])}"
            )

            self.history.append(change)
            self._save_state()

            # Combine all validation issues
            all_issues = validation.errors + validation.warnings + validation.security_issues

            return {
                'change_id': change.id,
                'status': change.status,
                'auto_approved': False,
                'auto_rejected': True,
                'message': f'❌ Auto-rejected: Quality score {score}/100 is too low (minimum: 40). Please improve code quality and resubmit.',
                'can_apply': False,
                'reason': 'quality_too_low',
                'required_improvements': all_issues[:5],  # Show top 5 issues
                'analysis': {
                    'patterns': analysis['patterns_found'],
                    'root_causes': analysis['root_causes'],
                    'recommendations': analysis['recommendations'][:3]  # Top 3 recommendations
                }
            }

        # Warn about low quality (40-60) but allow to proceed
        if score < 60:
            print(f"⚠️ WARNING: Low quality score ({score}/100) - will require manual approval")

        # NEW: Test tools before adding to queue
        if 'tools/' in generated_code.file_path and generated_code.is_new_file:
            from introspection.tool_tester import ToolTester

            print(f"🧪 Running automated tests for new tool...")
            tester = ToolTester()
            tool_name = Path(generated_code.file_path).stem
            test_result = tester.test_tool_code(generated_code.new_code, tool_name)

            # Store test results in generated_code
            generated_code.tool_test_passed = test_result.passed
            generated_code.tool_test_report = tester.get_test_report(test_result)

            print(f"   Test result: {'✅ PASSED' if test_result.passed else '❌ FAILED'}")
            print(f"   Tests: {test_result.tests_passed}/{test_result.tests_run}")
            print(f"   Functions: {len(test_result.functions_found)}")

        # Check for duplicate submissions
        duplicate = self._check_for_duplicate(generated_code)
        if duplicate:
            return {
                'change_id': duplicate['change_id'],
                'status': duplicate['status'],
                'auto_approved': False,
                'message': f"⚠️ Duplicate change detected (same file path and content). {duplicate['message']}",
                'can_apply': False,
                'duplicate': True
            }

        # Create change request
        change = ChangeRequest(
            id=self._generate_id(),
            generated_code=self._to_dict(generated_code),
            validation=self._to_dict(validation)
        )

        # Check if can auto-approve
        if change.should_auto_approve():
            change.status = ApprovalStatus.AUTO_APPROVED.value
            change.reviewed_at = datetime.now().isoformat()
            change.reviewer_comment = "Auto-approved: Safe change with high validation score"

            self.history.append(change)
            self._save_state()

            return {
                'change_id': change.id,
                'status': change.status,
                'auto_approved': True,
                'message': '✅ Change auto-approved and ready to apply',
                'can_apply': True
            }
        else:
            # Add to pending queue
            self.pending.append(change)
            self._save_state()

            return {
                'change_id': change.id,
                'status': change.status,
                'auto_approved': False,
                'message': '⏳ Change pending manual approval',
                'can_apply': False
            }

    def approve(self, change_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Manually approve a pending change

        Args:
            change_id: ID of the change request
            comment: Optional reviewer comment

        Returns:
            {
                'success': bool,
                'message': str,
                'change': dict
            }
        """
        change = self._find_pending_change(change_id)

        if not change:
            return {
                'success': False,
                'message': f'❌ Change {change_id} not found in pending queue'
            }

        # Update status
        change.status = ApprovalStatus.APPROVED.value
        change.reviewed_at = datetime.now().isoformat()
        change.reviewer_comment = comment or "Manually approved"

        # Move to history
        self.pending.remove(change)
        self.history.append(change)
        self._save_state()

        return {
            'success': True,
            'message': f'✅ Change {change_id} approved and ready to apply',
            'change': asdict(change)
        }

    def reject(self, change_id: str, reason: str) -> Dict[str, Any]:
        """
        Reject a pending change

        Args:
            change_id: ID of the change request
            reason: Reason for rejection

        Returns:
            {
                'success': bool,
                'message': str
            }
        """
        change = self._find_pending_change(change_id)

        if not change:
            return {
                'success': False,
                'message': f'❌ Change {change_id} not found in pending queue'
            }

        # Update status
        change.status = ApprovalStatus.REJECTED.value
        change.reviewed_at = datetime.now().isoformat()
        change.reviewer_comment = reason

        # Move to history
        self.pending.remove(change)
        self.history.append(change)
        self._save_state()

        return {
            'success': True,
            'message': f'❌ Change {change_id} rejected: {reason}'
        }

    def mark_as_applied(self, change_id: str, rollback_id: str) -> bool:
        """Mark a change as successfully applied"""
        # Check in history (approved/auto-approved changes)
        for change in self.history:
            if change.id == change_id:
                change.status = ApprovalStatus.APPLIED.value
                change.applied_at = datetime.now().isoformat()
                change.rollback_id = rollback_id
                self._save_state()
                return True

        return False

    def mark_as_failed(self, change_id: str, error: str) -> bool:
        """Mark a change as failed to apply"""
        for change in self.history:
            if change.id == change_id:
                change.status = ApprovalStatus.FAILED.value
                change.reviewer_comment = f"Failed to apply: {error}"
                self._save_state()
                return True

        return False

    def mark_as_rolled_back(self, change_id: str) -> bool:
        """Mark a change as rolled back"""
        for change in self.history:
            if change.id == change_id:
                change.status = ApprovalStatus.ROLLED_BACK.value
                self._save_state()
                return True

        return False

    def get_pending(self) -> List[Dict]:
        """Get all pending changes"""
        return [asdict(change) for change in self.pending]

    def get_pending_count(self) -> int:
        """Get count of pending changes without loading full data"""
        return len(self.pending)

    def get_history(self, limit: int = 50, status: Optional[str] = None) -> List[Dict]:
        """
        Get change history

        Args:
            limit: Maximum number of changes to return
            status: Filter by status (optional)

        Returns:
            List of change dictionaries
        """
        history = self.history

        if status:
            history = [c for c in history if c.status == status]

        # Sort by created_at descending
        history.sort(key=lambda x: x.created_at, reverse=True)

        return [asdict(change) for change in history[:limit]]

    def get_change(self, change_id: str) -> Optional[Dict]:
        """Get a specific change by ID"""
        # Check pending
        for change in self.pending:
            if change.id == change_id:
                return asdict(change)

        # Check history
        for change in self.history:
            if change.id == change_id:
                return asdict(change)

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get approval queue statistics"""
        total_changes = len(self.pending) + len(self.history)

        status_counts = {}
        auto_rejected_count = 0  # Track auto-rejections (score < 40)

        for change in self.history:
            status = change.status
            status_counts[status] = status_counts.get(status, 0) + 1

            # Count auto-rejections (rejected with "Auto-rejected" in comment)
            if status == ApprovalStatus.REJECTED.value:
                comment = change.reviewer_comment or ""
                if "Auto-rejected" in comment and "below minimum threshold" in comment:
                    auto_rejected_count += 1

        auto_approved = status_counts.get(ApprovalStatus.AUTO_APPROVED.value, 0)
        manually_approved = status_counts.get(ApprovalStatus.APPROVED.value, 0)
        rejected = status_counts.get(ApprovalStatus.REJECTED.value, 0)
        applied = status_counts.get(ApprovalStatus.APPLIED.value, 0)
        failed = status_counts.get(ApprovalStatus.FAILED.value, 0)

        # Calculate quality metrics
        manual_rejections = rejected - auto_rejected_count
        quality_rate = 0
        if total_changes > 0:
            quality_rate = ((total_changes - auto_rejected_count) / total_changes) * 100

        success_rate = 0
        if applied + failed > 0:
            success_rate = (applied / (applied + failed)) * 100

        return {
            'total_changes': total_changes,
            'pending': len(self.pending),
            'history_count': len(self.history),
            'status_breakdown': status_counts,
            'auto_approved': auto_approved,
            'manually_approved': manually_approved,
            'rejected': rejected,
            'auto_rejected': auto_rejected_count,
            'manual_rejections': manual_rejections,
            'applied': applied,
            'failed': failed,
            'success_rate': round(success_rate, 1),
            'quality_rate': round(quality_rate, 1),  # % of code that passed quality threshold
            'automation_rate': round(((auto_approved + auto_rejected_count) / max(total_changes, 1)) * 100, 1)
        }

    def _find_pending_change(self, change_id: str) -> Optional[ChangeRequest]:
        """Find a change in pending queue"""
        for change in self.pending:
            if change.id == change_id:
                return change
        return None

    def _generate_id(self) -> str:
        """Generate unique change ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"change_{timestamp}_{len(self.pending) + len(self.history)}"

    def _compute_content_hash(self, generated_code: GeneratedCode) -> str:
        """
        Compute a hash of the generated code content for duplicate detection

        Uses file path + new code content to create a unique signature
        """
        file_path = generated_code.file_path if hasattr(generated_code, 'file_path') else ''
        new_code = generated_code.new_code if hasattr(generated_code, 'new_code') else ''

        # Combine file path and code content for hash
        content = f"{file_path}:::{new_code}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _check_for_duplicate(self, generated_code: GeneratedCode) -> Optional[Dict[str, str]]:
        """
        Check if a similar change already exists in pending or history

        Returns:
            None if no duplicate found
            Dict with change_id, status, and message if duplicate detected
        """
        content_hash = self._compute_content_hash(generated_code)
        file_path = generated_code.file_path if hasattr(generated_code, 'file_path') else ''

        # Check pending changes
        for change in self.pending:
            existing_code = change.generated_code
            existing_file = existing_code.get('file_path', '')
            existing_new_code = existing_code.get('new_code', '')

            # Compute hash for existing change
            existing_content = f"{existing_file}:::{existing_new_code}"
            existing_hash = hashlib.sha256(existing_content.encode()).hexdigest()

            if content_hash == existing_hash:
                return {
                    'change_id': change.id,
                    'status': change.status,
                    'message': f'Same change already pending as {change.id}'
                }

        # Check recent history (last 20 changes to avoid performance issues)
        for change in self.history[-20:]:
            existing_code = change.generated_code
            existing_file = existing_code.get('file_path', '')
            existing_new_code = existing_code.get('new_code', '')

            # Compute hash for existing change
            existing_content = f"{existing_file}:::{existing_new_code}"
            existing_hash = hashlib.sha256(existing_content.encode()).hexdigest()

            if content_hash == existing_hash:
                status_msg = {
                    'auto_approved': 'already auto-approved',
                    'approved': 'already manually approved',
                    'applied': 'already applied to codebase',
                    'rejected': 'previously rejected'
                }.get(change.status, f'already in history with status: {change.status}')

                return {
                    'change_id': change.id,
                    'status': change.status,
                    'message': f'Same change {status_msg} as {change.id}'
                }

        return None

    def _to_dict(self, obj: Any) -> Dict:
        """Convert dataclass to dict"""
        if hasattr(obj, '__dict__'):
            return asdict(obj) if hasattr(obj, '__dataclass_fields__') else obj.__dict__
        return obj

    def _save_state(self):
        """Persist queue state to disk"""
        try:
            state = {
                'pending': [asdict(c) for c in self.pending],
                'history': [asdict(c) for c in self.history[-100:]]  # Keep last 100
            }

            state_file = self.storage_path / "approval_queue.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            print(f"❌ Failed to save approval queue state: {e}")

    def cleanup_stale_approvals(self, max_age_days: int = 7) -> int:
        """
        Remove stale approved/rejected changes that were never applied

        Args:
            max_age_days: Remove approvals older than this many days

        Returns:
            Number of stale approvals removed
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        initial_count = len(self.history)

        # Keep only:
        # 1. Recent changes (within max_age_days)
        # 2. Applied changes (historical record)
        # 3. Failed changes (to learn from)
        self.history = [
            change for change in self.history
            if (
                datetime.fromisoformat(change.created_at) > cutoff_date or
                change.status in [ApprovalStatus.APPLIED.value, ApprovalStatus.FAILED.value]
            )
        ]

        removed = initial_count - len(self.history)

        if removed > 0:
            self._save_state()
            print(f"🗑️ Cleaned up {removed} stale approvals older than {max_age_days} days")

        return removed

    def _load_state(self):
        """Load queue state from disk"""
        try:
            state_file = self.storage_path / "approval_queue.json"

            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                self.pending = [
                    ChangeRequest(**c) for c in state.get('pending', [])
                ]
                # Load only last 100 from history to improve performance
                history_data = state.get('history', [])
                self.history = [
                    ChangeRequest(**c) for c in history_data[-100:]
                ]

                if len(history_data) > 100:
                    print(f"📥 Loaded {len(self.pending)} pending + {len(self.history)} history changes (trimmed from {len(history_data)})")
                    # Save trimmed state immediately
                    self._save_state()
                else:
                    print(f"📥 Loaded {len(self.pending)} pending + {len(self.history)} history changes")

                # Auto-cleanup stale approvals on load
                self.cleanup_stale_approvals(max_age_days=7)

        except Exception as e:
            print(f"⚠️ Failed to load approval queue state: {e}")
            self.pending = []
            self.history = []
