#!/usr/bin/env python3
"""
Script to remove all approval requests with validation scores below 40
"""
import json
from pathlib import Path

# Path to approval queue
APPROVAL_FILE = Path("/app/data/approvals/approval_queue.json")

def cleanup_low_quality_approvals():
    """Remove all approvals with score < 40"""

    if not APPROVAL_FILE.exists():
        print(f"❌ Approval file not found: {APPROVAL_FILE}")
        return

    # Load current state
    with open(APPROVAL_FILE, 'r') as f:
        state = json.load(f)

    pending = state.get('pending', [])
    history = state.get('history', [])

    print(f"📊 Current state:")
    print(f"   Pending: {len(pending)}")
    print(f"   History: {len(history)}")

    # Filter pending - remove those with score < 40
    filtered_pending = []
    removed_pending = 0

    for change in pending:
        validation = change.get('validation', {})
        score = validation.get('score', 0)
        file_path = change.get('generated_code', {}).get('file_path', 'unknown')

        if score < 40:
            print(f"   🗑️ Removing from pending: {file_path} (score: {score})")
            removed_pending += 1
        else:
            filtered_pending.append(change)

    # Filter history - remove those with score < 40 that are not applied
    filtered_history = []
    removed_history = 0

    for change in history:
        validation = change.get('validation', {})
        score = validation.get('score', 0)
        status = change.get('status', 'unknown')
        file_path = change.get('generated_code', {}).get('file_path', 'unknown')

        # Keep if score >= 40 OR if already applied/auto_approved
        keep_statuses = ['applied', 'auto_approved']

        if score < 40 and status not in keep_statuses:
            print(f"   🗑️ Removing from history: {file_path} (score: {score}, status: {status})")
            removed_history += 1
        else:
            filtered_history.append(change)

    # Save cleaned state
    cleaned_state = {
        'pending': filtered_pending,
        'history': filtered_history
    }

    with open(APPROVAL_FILE, 'w') as f:
        json.dump(cleaned_state, f, indent=2)

    print(f"\n✅ Cleanup complete!")
    print(f"   Removed from pending: {removed_pending}")
    print(f"   Removed from history: {removed_history}")
    print(f"   New pending count: {len(filtered_pending)}")
    print(f"   New history count: {len(filtered_history)}")

if __name__ == '__main__':
    cleanup_low_quality_approvals()
