#!/usr/bin/env python3
"""
Safety Event Monitor — Research dashboard for Darwin's alignment instrumentation.

Run: docker exec darwin-backend-1 python3 /app/monitor_safety.py
  or: docker exec darwin-backend-1 python3 /app/monitor_safety.py --hours 168  (last 7 days)
  or: docker exec darwin-backend-1 python3 /app/monitor_safety.py --live       (auto-refresh)
"""

import argparse
import json
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.bar import Bar
from rich.text import Text
from rich.live import Live
from rich.layout import Layout


DB_PATH = "./data/darwin.db"

# Friendly labels and colors for event types
EVENT_LABELS = {
    'routing_decision':          ('Routing Decision',          'cyan'),
    'model_fallback':            ('Model Fallback',            'yellow'),
    'truncation_retry':          ('Truncation Retry',          'yellow'),
    'early_stop':                ('Early Stop',                'green'),
    'tool_rejected':             ('Tool Rejected',             'red'),
    'protected_file_redirect':   ('Protected File Redirect',   'red'),
    'code_validation_fail':      ('Code Validation Fail',      'red'),
    'code_validation_corrected': ('Code Validation Corrected', 'yellow'),
    'prompt_rollback':           ('Prompt Rollback',           'red'),
    'prompt_promoted':           ('Prompt Promoted',           'green'),
}

SAFETY_EVENTS = {
    'tool_rejected', 'protected_file_redirect', 'code_validation_fail',
    'prompt_rollback', 'model_fallback', 'truncation_retry',
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_events(hours=24):
    conn = get_conn()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT * FROM safety_events WHERE timestamp > ? ORDER BY timestamp DESC",
        (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_time_stats():
    conn = get_conn()
    rows = conn.execute(
        "SELECT event_type, COUNT(*) as count FROM safety_events GROUP BY event_type"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM safety_events").fetchone()[0]
    first = conn.execute("SELECT MIN(timestamp) FROM safety_events").fetchone()[0]
    conn.close()
    return {r['event_type']: r['count'] for r in rows}, total, first


def get_hourly_distribution(hours=24):
    conn = get_conn()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT timestamp, event_type FROM safety_events WHERE timestamp > ? ORDER BY timestamp",
        (since,)
    ).fetchall()
    conn.close()

    hourly = defaultdict(int)
    safety_hourly = defaultdict(int)
    for r in rows:
        hour = r['timestamp'][:13]  # YYYY-MM-DDTHH
        hourly[hour] += 1
        if r['event_type'] in SAFETY_EVENTS:
            safety_hourly[hour] += 1
    return hourly, safety_hourly


def get_model_distribution(hours=24):
    conn = get_conn()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT details FROM safety_events WHERE event_type = 'routing_decision' AND timestamp > ?",
        (since,)
    ).fetchall()
    conn.close()

    models = Counter()
    for r in rows:
        d = json.loads(r['details'])
        models[d.get('model', 'unknown')] += 1
    return models


def build_dashboard(hours=24):
    console = Console()
    events = get_events(hours)
    all_stats, total_ever, first_event = get_all_time_stats()
    hourly, safety_hourly = get_hourly_distribution(hours)
    model_dist = get_model_distribution(hours)

    # --- Header ---
    since_str = f"last {hours}h" if hours <= 48 else f"last {hours // 24} days"
    first_str = first_event[:19] if first_event else "no events"

    header = Text()
    header.append("DARWIN SAFETY MONITOR", style="bold white on blue")
    header.append(f"  |  {since_str}  |  ", style="dim")
    header.append(f"Total ever: {total_ever}", style="bold cyan")
    header.append(f"  |  Since: {first_str}", style="dim")

    console.print()
    console.print(Panel(header, expand=True))

    # --- Summary counts ---
    period_counts = Counter(e['event_type'] for e in events)

    summary_table = Table(title=f"Event Summary ({since_str})", expand=True)
    summary_table.add_column("Event Type", style="bold")
    summary_table.add_column("Count", justify="right")
    summary_table.add_column("All Time", justify="right", style="dim")
    summary_table.add_column("Bar", width=30)
    summary_table.add_column("Severity")

    max_count = max(period_counts.values()) if period_counts else 1

    for etype, (label, color) in EVENT_LABELS.items():
        count = period_counts.get(etype, 0)
        all_time = all_stats.get(etype, 0)
        bar_width = int((count / max_count) * 25) if max_count > 0 else 0
        bar_str = "█" * bar_width + "░" * (25 - bar_width)

        severity = "🔴 SAFETY" if etype in SAFETY_EVENTS else "🟢 info"
        if etype in ('early_stop', 'prompt_promoted', 'code_validation_corrected'):
            severity = "🟡 operational"

        summary_table.add_row(
            f"[{color}]{label}[/{color}]",
            str(count),
            str(all_time),
            f"[{color}]{bar_str}[/{color}]",
            severity,
        )

    console.print(summary_table)

    # --- Safety Score ---
    total_period = len(events)
    safety_count = sum(1 for e in events if e['event_type'] in SAFETY_EVENTS)
    operational_count = total_period - safety_count

    if total_period > 0:
        safety_pct = (safety_count / total_period) * 100
        health_score = max(0, 100 - safety_pct * 2)  # Penalize safety events
    else:
        safety_pct = 0
        health_score = 100

    score_color = "green" if health_score >= 80 else "yellow" if health_score >= 50 else "red"

    panels = []
    panels.append(Panel(
        f"[bold {score_color}]{health_score:.0f}%[/]\n[dim]higher = fewer safety triggers[/dim]",
        title="Health Score", width=25
    ))
    panels.append(Panel(
        f"[bold cyan]{total_period}[/]\n[dim]events in {since_str}[/dim]",
        title="Total Events", width=25
    ))
    panels.append(Panel(
        f"[bold red]{safety_count}[/]\n[dim]safety mechanism fires[/dim]",
        title="Safety Events", width=25
    ))
    panels.append(Panel(
        f"[bold green]{operational_count}[/]\n[dim]normal operations[/dim]",
        title="Operational", width=25
    ))

    console.print(Columns(panels, expand=True))

    # --- Model Distribution ---
    if model_dist:
        model_table = Table(title="Model Routing Distribution", expand=True)
        model_table.add_column("Model", style="bold")
        model_table.add_column("Requests", justify="right")
        model_table.add_column("Share", justify="right")
        model_table.add_column("Bar", width=30)

        total_routes = sum(model_dist.values())
        for model, count in model_dist.most_common():
            pct = (count / total_routes) * 100
            bar_width = int((count / total_routes) * 25)
            bar_str = "█" * bar_width + "░" * (25 - bar_width)
            color = "green" if 'ollama' in model else "yellow" if 'haiku' in model else "red"
            cost = "FREE" if 'ollama' in model else "$$$" if 'claude' in model else "$$"

            model_table.add_row(
                f"[{color}]{model}[/{color}]",
                str(count),
                f"{pct:.1f}% ({cost})",
                f"[{color}]{bar_str}[/{color}]",
            )

        console.print(model_table)

    # --- Hourly Activity (text-based chart) ---
    if hourly:
        console.print()
        console.print(f"[bold]Hourly Activity ({since_str}):[/bold]")

        sorted_hours = sorted(hourly.keys())[-min(24, len(hourly)):]
        max_h = max(hourly[h] for h in sorted_hours) if sorted_hours else 1

        for hour in sorted_hours:
            h_label = hour[11:13] + "h"  # Just HHh
            count = hourly[hour]
            s_count = safety_hourly.get(hour, 0)
            bar_width = int((count / max_h) * 40)
            s_width = int((s_count / max_h) * 40) if s_count > 0 else 0
            normal_width = bar_width - s_width

            bar = Text()
            bar.append(f"  {h_label} ", style="dim")
            bar.append("█" * normal_width, style="cyan")
            bar.append("█" * s_width, style="red")
            bar.append(f" {count}", style="dim")
            if s_count > 0:
                bar.append(f" ({s_count} safety)", style="red")
            console.print(bar)

        console.print("[dim]  cyan=normal  red=safety triggers[/dim]")

    # --- Recent Events ---
    recent_table = Table(title="Recent Events (last 15)", expand=True)
    recent_table.add_column("Time", style="dim", width=19)
    recent_table.add_column("Type", width=28)
    recent_table.add_column("Details", ratio=1)

    for e in events[:15]:
        etype = e['event_type']
        label, color = EVENT_LABELS.get(etype, (etype, 'white'))
        details = json.loads(e['details']) if isinstance(e['details'], str) else e['details']

        # Format details nicely
        if etype == 'routing_decision':
            detail_str = f"{details.get('model', '?')} | {details.get('complexity', '?')} | {details.get('task', '')[:40]}"
        elif etype == 'early_stop':
            detail_str = f"reason={details.get('reason', '?')} iter={details.get('iteration', '?')} | {details.get('goal', '')[:30]}"
        elif etype == 'model_fallback':
            detail_str = f"{details.get('from_model', '?')} → {details.get('to_model', '?')} | {details.get('error', '')[:30]}"
        elif etype == 'prompt_rollback':
            detail_str = f"slot={details.get('slot', '?')} score={details.get('active_score', '?')} < {details.get('original_score', '?')}*0.9"
        elif etype == 'tool_rejected':
            detail_str = f"tool={details.get('tool', '?')}"
        elif etype == 'protected_file_redirect':
            detail_str = f"file={details.get('file', '?')} | {details.get('insight', '')[:30]}"
        else:
            detail_str = json.dumps(details, default=str)[:60]

        recent_table.add_row(
            e['timestamp'][:19],
            f"[{color}]{label}[/{color}]",
            detail_str,
        )

    console.print(recent_table)

    # --- Early Stop Analysis ---
    early_stops = [e for e in events if e['event_type'] == 'early_stop']
    if early_stops:
        reasons = Counter()
        for e in early_stops:
            d = json.loads(e['details']) if isinstance(e['details'], str) else e['details']
            reasons[d.get('reason', 'unknown')] += 1

        console.print()
        stop_text = Text("Early Stop Reasons: ", style="bold")
        for reason, count in reasons.most_common():
            color = "green" if reason == 'done_signal' else "yellow" if reason == 'write_file' else "red"
            stop_text.append(f"{reason}={count} ", style=color)
        console.print(Panel(stop_text))


def live_mode(hours=24, interval=30):
    """Auto-refreshing dashboard."""
    console = Console()
    console.print(f"[bold]Live mode[/bold] — refreshing every {interval}s. Press Ctrl+C to exit.")

    try:
        while True:
            console.clear()
            build_dashboard(hours)
            console.print(f"\n[dim]Next refresh in {interval}s... (Ctrl+C to exit)[/dim]")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[bold]Stopped.[/bold]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Darwin Safety Event Monitor")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument("--live", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=30, help="Refresh interval in seconds (default: 30)")
    args = parser.parse_args()

    if args.live:
        live_mode(args.hours, args.interval)
    else:
        build_dashboard(args.hours)
