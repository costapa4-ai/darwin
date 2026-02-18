"""
CuriosityEngine — Human-aligned curiosity-driven exploration cycle.

Replaces random goal selection with structured thinking:
  Curiosity Item -> Plan -> Execute -> Analyze -> Satisfy or Spawn Sub-Items

Knowledge is stored at any meaningful satisfaction level (>= 20%).
Adaptive thresholds per depth: broad (50%), specific (65%), narrow (80%).
The queue self-cleans as items are explored.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)

_local = threading.local()


class CuriosityEngine:
    """Manages Darwin's curiosity-driven exploration cycle."""

    MAX_QUEUE_SIZE = 50
    MAX_DEPTH = 3
    EXPIRY_DAYS = 7
    MAX_SUB_ITEMS = 3

    # Adaptive satisfaction thresholds per depth:
    # depth 0 (broad) = 50%, depth 1 (specific) = 65%, depth 2 (narrow) = 80%
    DEFAULT_THRESHOLDS = {0: 50, 1: 65, 2: 80}

    def __init__(self, db_path: str = "./data/darwin.db"):
        self.db_path = db_path
        self.satisfaction_thresholds = dict(self.DEFAULT_THRESHOLDS)
        self._init_db()
        self._load_thresholds()
        stats = self.get_queue_stats()
        logger.info(f"CuriosityEngine initialized ({stats['pending']} pending, {stats['exploring']} exploring)")

    def get_threshold(self, depth: int) -> int:
        """Get satisfaction threshold for a given depth."""
        # Use the threshold for the depth, or the highest defined for deeper levels
        if depth in self.satisfaction_thresholds:
            return self.satisfaction_thresholds[depth]
        max_defined = max(self.satisfaction_thresholds.keys())
        return self.satisfaction_thresholds[max_defined]

    def set_thresholds(self, thresholds: Dict[int, int]) -> Dict[int, int]:
        """Update satisfaction thresholds. Returns the new thresholds."""
        for depth, value in thresholds.items():
            if 0 <= depth <= self.MAX_DEPTH and 10 <= value <= 100:
                self.satisfaction_thresholds[int(depth)] = int(value)
        self._save_thresholds()
        logger.info(f"Satisfaction thresholds updated: {self.satisfaction_thresholds}")
        return self.satisfaction_thresholds

    def _load_thresholds(self):
        """Load thresholds from SQLite settings."""
        try:
            conn = self._get_conn()
            conn.execute("""CREATE TABLE IF NOT EXISTS curiosity_settings (
                key TEXT PRIMARY KEY, value TEXT
            )""")
            conn.commit()
            row = conn.execute(
                "SELECT value FROM curiosity_settings WHERE key = 'satisfaction_thresholds'"
            ).fetchone()
            if row:
                self.satisfaction_thresholds = {int(k): int(v) for k, v in json.loads(row['value']).items()}
        except Exception as e:
            logger.debug(f"Loading thresholds failed, using defaults: {e}")

    def _save_thresholds(self):
        """Persist thresholds to SQLite."""
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO curiosity_settings (key, value) VALUES (?, ?)",
                ('satisfaction_thresholds', json.dumps(self.satisfaction_thresholds))
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"Saving thresholds failed: {e}")

    def get_exploration_metrics(self) -> Dict[str, Any]:
        """Get detailed exploration metrics per depth for observatory."""
        conn = self._get_conn()

        metrics = {'by_depth': {}, 'totals': {}, 'thresholds': self.satisfaction_thresholds}

        for depth in range(self.MAX_DEPTH):
            threshold = self.get_threshold(depth)
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_explored,
                    SUM(CASE WHEN satisfaction >= ? THEN 1 ELSE 0 END) as reached_threshold,
                    SUM(CASE WHEN knowledge_stored = 1 THEN 1 ELSE 0 END) as knowledge_stored,
                    ROUND(AVG(CASE WHEN satisfaction > 0 THEN satisfaction END), 1) as avg_satisfaction,
                    MAX(satisfaction) as max_satisfaction,
                    MIN(CASE WHEN satisfaction > 0 THEN satisfaction END) as min_satisfaction
                FROM curiosity_items
                WHERE depth = ? AND explored_at != ''
            """, (threshold, depth)).fetchone()

            pending = conn.execute(
                "SELECT COUNT(*) as c FROM curiosity_items WHERE depth = ? AND status = 'pending'",
                (depth,)
            ).fetchone()['c']

            exploring = conn.execute(
                "SELECT COUNT(*) as c FROM curiosity_items WHERE depth = ? AND status = 'exploring'",
                (depth,)
            ).fetchone()['c']

            depth_label = {0: 'broad', 1: 'specific', 2: 'narrow'}.get(depth, f'depth_{depth}')
            metrics['by_depth'][depth] = {
                'label': depth_label,
                'threshold': threshold,
                'total_explored': row['total_explored'] or 0,
                'reached_threshold': row['reached_threshold'] or 0,
                'threshold_rate': round((row['reached_threshold'] or 0) / max(row['total_explored'] or 1, 1) * 100, 1),
                'knowledge_stored': row['knowledge_stored'] or 0,
                'avg_satisfaction': row['avg_satisfaction'] or 0,
                'max_satisfaction': row['max_satisfaction'] or 0,
                'min_satisfaction': row['min_satisfaction'] or 0,
                'pending': pending,
                'exploring': exploring,
            }

        # Totals
        totals = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'satisfied' THEN 1 ELSE 0 END) as satisfied,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'exploring' THEN 1 ELSE 0 END) as exploring,
                SUM(CASE WHEN knowledge_stored = 1 THEN 1 ELSE 0 END) as total_knowledge_stored
            FROM curiosity_items
        """).fetchone()
        metrics['totals'] = {
            'total_items': totals['total'] or 0,
            'satisfied': totals['satisfied'] or 0,
            'expired': totals['expired'] or 0,
            'pending': totals['pending'] or 0,
            'exploring': totals['exploring'] or 0,
            'total_knowledge_stored': totals['total_knowledge_stored'] or 0,
        }

        # Recent explorations (last 10)
        recent = conn.execute("""
            SELECT id, substr(question, 1, 60) as question, depth, satisfaction,
                   knowledge_stored, status, explored_at
            FROM curiosity_items WHERE explored_at != ''
            ORDER BY explored_at DESC LIMIT 10
        """).fetchall()
        metrics['recent'] = [
            {
                'id': r['id'], 'question': r['question'], 'depth': r['depth'],
                'satisfaction': r['satisfaction'], 'knowledge_stored': bool(r['knowledge_stored']),
                'status': r['status'], 'explored_at': r['explored_at'],
                'met_threshold': r['satisfaction'] >= self.get_threshold(r['depth']),
            }
            for r in recent
        ]

        return metrics

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(_local, 'curiosity_conn') or _local.curiosity_conn is None:
            _local.curiosity_conn = sqlite3.connect(self.db_path)
            _local.curiosity_conn.row_factory = sqlite3.Row
            _local.curiosity_conn.execute("PRAGMA journal_mode=WAL")
        return _local.curiosity_conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS curiosity_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                topic TEXT DEFAULT '',
                source TEXT DEFAULT 'self',
                parent_id INTEGER DEFAULT NULL,
                depth INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                satisfaction INTEGER DEFAULT 0,
                priority REAL DEFAULT 0.5,
                plan TEXT DEFAULT '',
                findings TEXT DEFAULT '',
                knowledge_stored INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                explored_at TEXT DEFAULT '',
                satisfied_at TEXT DEFAULT '',
                expires_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_curiosity_status ON curiosity_items(status);
            CREATE INDEX IF NOT EXISTS idx_curiosity_parent ON curiosity_items(parent_id);
        """)
        conn.commit()

    # ── Queue Management ──────────────────────────────────────────────

    def add_item(
        self,
        question: str,
        topic: str = "",
        source: str = "self",
        parent_id: Optional[int] = None,
        priority: Optional[float] = None,
    ) -> int:
        """Add a new curiosity item. Returns item ID."""
        if not question or len(question.strip()) < 5:
            return 0

        # Calculate depth from parent
        depth = 0
        if parent_id:
            parent = self.get_item(parent_id)
            if parent:
                depth = parent['depth'] + 1
            if depth > self.MAX_DEPTH:
                logger.debug(f"Skipping sub-item at depth {depth} (max {self.MAX_DEPTH})")
                return 0

        # Check for duplicate questions (exact + fuzzy)
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM curiosity_items WHERE question = ? AND status IN ('pending', 'exploring')",
            (question.strip(),)
        ).fetchone()
        if existing:
            return existing['id']

        # Fuzzy dedup: skip if a similar question already exists (same key words)
        q_words = set(w.lower() for w in question.split() if len(w) > 4)
        if q_words and not parent_id:
            recent = conn.execute(
                "SELECT id, question FROM curiosity_items WHERE status IN ('pending', 'exploring', 'satisfied') ORDER BY id DESC LIMIT 50"
            ).fetchall()
            for row in recent:
                existing_words = set(w.lower() for w in row['question'].split() if len(w) > 4)
                if existing_words and len(q_words & existing_words) / max(len(q_words), 1) > 0.6:
                    logger.debug(f"Fuzzy dedup: '{question[:40]}' too similar to #{row['id']}")
                    return 0

        # Calculate priority
        if priority is None:
            priority = self._calculate_priority(source, depth)

        now = datetime.utcnow().isoformat()
        expires = (datetime.utcnow() + timedelta(days=self.EXPIRY_DAYS)).isoformat()

        cursor = conn.execute(
            """INSERT INTO curiosity_items
               (question, topic, source, parent_id, depth, status, priority, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (question.strip(), topic, source, parent_id, depth, priority, now, expires)
        )
        conn.commit()
        item_id = cursor.lastrowid

        logger.info(f"Curiosity #{item_id}: \"{question[:60]}\" (source={source}, depth={depth}, priority={priority:.2f})")
        return item_id

    def get_item(self, item_id: int) -> Optional[Dict]:
        """Get a single item by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM curiosity_items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None

    def get_next_item(self) -> Optional[Dict]:
        """Get the highest-priority pending item."""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT * FROM curiosity_items
               WHERE status = 'pending'
               ORDER BY priority DESC, depth ASC, created_at ASC
               LIMIT 1"""
        ).fetchone()
        return dict(row) if row else None

    def update_item(self, item_id: int, **kwargs) -> None:
        """Update fields on a curiosity item."""
        if not kwargs:
            return
        allowed = {'status', 'satisfaction', 'plan', 'findings', 'knowledge_stored',
                    'explored_at', 'satisfied_at', 'priority'}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return

        sets = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [item_id]

        conn = self._get_conn()
        conn.execute(f"UPDATE curiosity_items SET {sets} WHERE id = ?", values)
        conn.commit()

    def get_children(self, parent_id: int) -> List[Dict]:
        """Get all sub-items of a parent."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM curiosity_items WHERE parent_id = ? ORDER BY created_at ASC",
            (parent_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_queue_stats(self) -> Dict[str, Any]:
        """Return counts by status."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM curiosity_items GROUP BY status"
        ).fetchall()
        stats = {r['status']: r['count'] for r in rows}
        return {
            'pending': stats.get('pending', 0),
            'exploring': stats.get('exploring', 0),
            'satisfied': stats.get('satisfied', 0),
            'expired': stats.get('expired', 0),
            'total': sum(stats.values()),
        }

    def _calculate_priority(self, source: str, depth: int) -> float:
        """Calculate priority for a new curiosity item."""
        base = {
            'chat': 0.9,
            'finding': 0.7,
            'sleep': 0.6,
            'self': 0.5,
            'sub_item': 0.5,
        }.get(source, 0.5)

        # Depth penalty: deeper items are lower priority
        depth_factor = 1.0 - (depth * 0.15)
        return round(min(1.0, max(0.1, base * depth_factor)), 2)

    # ── Seeding ───────────────────────────────────────────────────────

    def seed_from_interests(self, interest_graph) -> int:
        """Create curiosity items from active interests (if queue nearly empty)."""
        stats = self.get_queue_stats()
        if stats['pending'] >= 5:
            return 0

        seeded = 0
        try:
            active = interest_graph.active_interests
            for topic, interest in active.items():
                # Convert internal slug to readable name
                readable = topic.replace('_', ' ').replace('(', '(').strip()
                depth = getattr(interest, 'depth', 0)
                if depth < 3:
                    question = f"What are the key concepts and recent developments in {readable}?"
                elif depth < 6:
                    question = f"What advanced techniques or open problems exist in {readable}?"
                else:
                    question = f"What are the frontier research questions in {readable}?"

                item_id = self.add_item(question, topic=topic, source='self', priority=0.5)
                if item_id:
                    seeded += 1
        except Exception as e:
            logger.debug(f"Seed from interests failed: {e}")

        return seeded

    def seed_from_intentions(self, intention_store) -> int:
        """Convert pending intentions into curiosity items."""
        seeded = 0
        try:
            pending = intention_store.get_pending(limit=5)
            for intent in pending:
                text = intent.get('intent', '') if isinstance(intent, dict) else str(intent)
                if text and len(text) > 10:
                    item_id = self.add_item(text, source='chat', priority=0.8)
                    if item_id:
                        seeded += 1
        except Exception as e:
            logger.debug(f"Seed from intentions failed: {e}")

        return seeded

    def add_from_sleep_plan(self, thought: str) -> int:
        """Convert a sleep 'plan' mode thought into a curiosity item."""
        if not thought or len(thought.strip()) < 15:
            return 0

        # Use first sentence or whole thought as question
        sentences = thought.strip().split('.')
        question = sentences[0].strip()
        if len(question) < 10 and len(sentences) > 1:
            question = f"{sentences[0].strip()}. {sentences[1].strip()}"

        return self.add_item(question[:200], source='sleep', priority=0.6)

    # ── Cleanup ───────────────────────────────────────────────────────

    def cleanup(self) -> int:
        """Run queue cleanup. Returns number of items cleaned."""
        cleaned = 0
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()

        # 1. Expire old pending items (> EXPIRY_DAYS)
        cursor = conn.execute(
            "UPDATE curiosity_items SET status = 'expired' WHERE status = 'pending' AND expires_at < ?",
            (now,)
        )
        cleaned += cursor.rowcount

        # 2. Propagate satisfaction: if all children of an 'exploring' parent are satisfied, satisfy parent
        parents = conn.execute(
            """SELECT DISTINCT parent_id FROM curiosity_items
               WHERE parent_id IS NOT NULL AND status != 'expired'"""
        ).fetchall()

        for row in parents:
            pid = row['parent_id']
            children = conn.execute(
                "SELECT status FROM curiosity_items WHERE parent_id = ? AND status != 'expired'",
                (pid,)
            ).fetchall()
            if children and all(c['status'] == 'satisfied' for c in children):
                # Parent satisfied via children — get parent's depth for threshold
                parent_row = conn.execute("SELECT depth FROM curiosity_items WHERE id = ?", (pid,)).fetchone()
                parent_threshold = self.get_threshold(parent_row['depth']) if parent_row else 65
                cursor = conn.execute(
                    """UPDATE curiosity_items SET status = 'satisfied', satisfaction = ?, satisfied_at = ?
                       WHERE id = ? AND status = 'exploring'""",
                    (parent_threshold, now, pid)
                )
                cleaned += cursor.rowcount

        # 3. Delete old satisfied/expired items (> 48h)
        cutoff = (datetime.utcnow() - timedelta(hours=48)).isoformat()
        cursor = conn.execute(
            "DELETE FROM curiosity_items WHERE status IN ('satisfied', 'expired') AND created_at < ?",
            (cutoff,)
        )
        cleaned += cursor.rowcount

        # 4. Enforce MAX_QUEUE_SIZE
        pending_count = conn.execute(
            "SELECT COUNT(*) as c FROM curiosity_items WHERE status IN ('pending', 'exploring')"
        ).fetchone()['c']

        if pending_count > self.MAX_QUEUE_SIZE:
            excess = pending_count - self.MAX_QUEUE_SIZE
            conn.execute(
                """UPDATE curiosity_items SET status = 'expired'
                   WHERE id IN (
                       SELECT id FROM curiosity_items
                       WHERE status = 'pending'
                       ORDER BY priority ASC, created_at ASC
                       LIMIT ?
                   )""",
                (excess,)
            )
            cleaned += excess

        conn.commit()

        if cleaned > 0:
            logger.info(f"Curiosity cleanup: {cleaned} items cleaned")

        return cleaned

    # ── Core Exploration Cycle ────────────────────────────────────────

    async def explore_item(
        self,
        item: Dict,
        router,
        tool_manager,
        hierarchical_memory,
    ) -> Dict[str, Any]:
        """
        Full curiosity cycle for one item:
        1. PLAN: How to investigate
        2. EXECUTE: Run the plan
        3. ANALYZE: Evaluate satisfaction
        4. STORE or SPAWN
        """
        item_id = item['id']

        # Mark as exploring
        self.update_item(item_id, status='exploring', explored_at=datetime.utcnow().isoformat())

        # Phase 1: PLAN
        plan = await self._plan_exploration(item, router)
        self.update_item(item_id, plan=plan)

        # Phase 2: EXECUTE
        execution = await self._execute_plan(plan, item, router, tool_manager)
        narrative = execution.get('narrative', '')
        # Reject XML/tool-call garbage as findings
        narrative = self._clean_narrative(narrative)
        self.update_item(item_id, findings=narrative[:500])

        # Phase 3: ANALYZE
        analysis = await self._analyze_result(item, plan, execution, router)
        satisfaction = analysis.get('satisfaction', 50)
        sub_questions = analysis.get('sub_questions', [])
        summary = analysis.get('summary', narrative[:200])

        self.update_item(item_id, satisfaction=satisfaction)

        # Phase 4: STORE and optionally SPAWN
        # Key insight: ALWAYS store knowledge when there are meaningful findings.
        # The satisfaction threshold controls spawning, not storage.
        knowledge_stored = False
        sub_items_created = 0

        # Store knowledge at ANY satisfaction level if findings are meaningful
        has_findings = narrative and len(narrative.strip()) > 50
        if has_findings and satisfaction >= 20:
            await self._store_knowledge(item, summary, narrative, satisfaction, hierarchical_memory)
            knowledge_stored = True

        threshold = self.get_threshold(item['depth'])
        if satisfaction >= threshold:
            # Satisfied for this depth level — mark done
            self.update_item(
                item_id,
                status='satisfied',
                knowledge_stored=1 if knowledge_stored else 0,
                satisfied_at=datetime.utcnow().isoformat()
            )
            logger.info(f"Curiosity #{item_id} satisfied ({satisfaction}% >= {threshold}% for depth {item['depth']})")
        else:
            # Not fully satisfied — try to spawn sub-items for deeper exploration
            can_spawn = (
                sub_questions
                and item['depth'] < self.MAX_DEPTH
                and satisfaction >= 15  # Below 15% = dead end
                and not (item['depth'] >= 2 and satisfaction < 30)
            )
            if can_spawn:
                sub_items_created = self._spawn_sub_items(item, sub_questions)

            if sub_items_created > 0:
                self.update_item(item_id, knowledge_stored=1 if knowledge_stored else 0)
                stored_msg = ", partial knowledge stored" if knowledge_stored else ""
                logger.info(f"Curiosity #{item_id} ({satisfaction}%), spawned {sub_items_created} sub-questions{stored_msg}")
            else:
                # Can't go deeper — mark satisfied with what we have
                self.update_item(
                    item_id,
                    status='satisfied',
                    knowledge_stored=1 if knowledge_stored else 0,
                    satisfied_at=datetime.utcnow().isoformat()
                )

        return {
            'item_id': item_id,
            'satisfaction': satisfaction,
            'knowledge_stored': knowledge_stored,
            'sub_items_created': sub_items_created,
            'narrative': narrative,
            'summary': summary,
        }

    async def _plan_exploration(self, item: Dict, router) -> str:
        """Phase 1: LLM generates an exploration plan."""
        question = item['question']
        topic = item.get('topic', '')
        findings = item.get('findings', '')

        prompt = f"""You want to answer this question: {question}
{f'Topic area: {topic}' if topic else ''}
{f'Previous findings: {findings}' if findings else ''}

Available tools:
1. web_search (search the internet, fetch URLs) — USE THIS for factual/historical/scientific questions
2. file_operations (read/list/search files) — ONLY for questions about Darwin's own code or data
3. script_executor (run Python) — for calculations or data processing

Write a brief plan (2-3 steps) for how to investigate this question.
Start with web_search unless the question is about Darwin's own system.

Plan:"""

        try:
            result = await router.generate(
                task_description="curiosity exploration planning",
                prompt=prompt,
                system_prompt="You are Darwin planning how to investigate a question. For factual questions about the world, always plan to use web_search first. Only use file_operations for questions about your own code/data.",
                context={'activity_type': 'curiosity_planning'},
                preferred_model='haiku',
                max_tokens=250,
                temperature=0.6,
            )
            plan = result.get('result', '').strip()
            return plan if plan else f"Investigate: {question}"
        except Exception as e:
            logger.warning(f"Plan generation failed: {e}")
            return f"Investigate: {question}"

    @staticmethod
    def _clean_narrative(narrative: str) -> str:
        """Strip XML tool blocks and other non-content from narrative."""
        if not narrative:
            return ''
        import re
        # Remove XML invoke/tool blocks that models sometimes emit
        cleaned = re.sub(r'<invoke\b[^>]*>.*?</invoke>', '', narrative, flags=re.DOTALL)
        cleaned = re.sub(r'<tool_call\b[^>]*>.*?</tool_call>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<function_calls?\b[^>]*>.*?</function_calls?>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<search\b[^>]*>.*?</search>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<parameter\b[^>]*>.*?</parameter>', '', cleaned, flags=re.DOTALL)
        # Remove ```tool_call blocks that weren't executed
        cleaned = re.sub(r'```tool_call.*?```', '', cleaned, flags=re.DOTALL)
        # Collapse whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        return cleaned

    async def _execute_plan(self, plan: str, item: Dict, router, tool_manager) -> Dict:
        """Phase 2: Execute the plan via autonomous loop."""
        from consciousness.autonomous_loop import run_autonomous_loop

        goal = f"Question: {item['question']}\n\nPlan:\n{plan}"

        system_prompt = """You are Darwin, an AI exploring a curiosity question.
Follow the plan to investigate. Use the available tools to gather real information.

AVAILABLE TOOLS (in order of preference):
1. web_search_tool.search — args: query (string), max_results (int, default 5)
   USE THIS FIRST for any factual, historical, scientific, or external knowledge question.
2. web_search_tool.fetch_url — args: url (string)
   Fetch a specific URL found in search results.
3. file_operations_tool.read_file — args: file_path (string)
   ONLY for questions about Darwin's own code or data files.
4. file_operations_tool.list_directory — args: dir_path (string), pattern (string, default "*")
5. file_operations_tool.search_files — args: dir_path (string), text (string)
6. script_executor_tool.execute_python — args: code (string), description (string)
   For calculations, data analysis, or processing search results.

FORMAT — you MUST use this exact format:
```tool_call
{"tool": "web_search_tool.search", "args": {"query": "your search query"}}
```

RULES:
1. ALWAYS start with a ```tool_call block — never answer from memory alone
2. DEFAULT to web_search_tool.search for any question about the world, history, science, people, places, concepts, or current events
3. ONLY use file_operations_tool when the question is specifically about Darwin's own code/data/configuration
4. Use script_executor_tool.execute_python for math, calculations, or data processing
5. After gathering information, write a factual summary WITHOUT tool_call blocks
6. NEVER just describe what you would do — actually call the tools
7. If web_search returns no results, try rephrasing the query before giving up"""

        try:
            result = await run_autonomous_loop(
                goal=goal,
                system_prompt=system_prompt,
                router=router,
                tool_manager=tool_manager,
                max_iterations=5,
                max_tokens=2000,
                preferred_model='haiku',
                timeout=45,
            )
            return result
        except Exception as e:
            logger.warning(f"Execution failed: {e}")
            return {'narrative': f'Execution failed: {e}', 'tool_results': [], 'iterations': 0}

    async def _analyze_result(self, item: Dict, plan: str, execution: Dict, router) -> Dict:
        """Phase 3: LLM evaluates satisfaction and generates sub-questions."""
        narrative = execution.get('narrative', '')
        tool_results = execution.get('tool_results', [])
        tools_used = len(tool_results)

        # Build a richer context: narrative + actual tool outputs
        tool_summary = ''
        if tool_results:
            # Include successful tool results (the actual data)
            successes = [r for r in tool_results if r.startswith('✅')]
            if successes:
                tool_summary = '\nTool outputs:\n' + '\n'.join(s[:300] for s in successes[:3])

        findings = self._clean_narrative(narrative)[:400] + tool_summary[:400]

        prompt = f"""You wanted to answer: {item['question']}
Your plan was: {plan[:200]}
What you found ({tools_used} tools used): {findings}

Rate how well the question was answered:
- 80-100: The question is substantially answered with concrete facts or insights
- 50-79: Partial answer — some useful information but significant gaps remain
- 20-49: Minimal useful information obtained
- 0-19: No useful information found

Reply with ONLY valid JSON:
{{"satisfaction": <int>, "sub_questions": ["...if below 80, 1-3 specific follow-up questions"], "summary": "what was actually learned (2-3 sentences of FACTS, not process)"}}
JSON:"""

        try:
            result = await router.generate(
                task_description="curiosity satisfaction analysis",
                prompt=prompt,
                system_prompt="You are evaluating whether a question was adequately answered. Be honest about gaps. Return only JSON.",
                context={'activity_type': 'curiosity_analysis'},
                preferred_model='haiku',
                max_tokens=300,
                temperature=0.3,
            )
            text = result.get('result', '').strip()

            # Parse JSON from response
            # Try to find JSON in the response
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(text[json_start:json_end])
                return {
                    'satisfaction': max(0, min(100, int(data.get('satisfaction', 50)))),
                    'sub_questions': data.get('sub_questions', [])[:self.MAX_SUB_ITEMS],
                    'summary': str(data.get('summary', narrative[:200]))[:300],
                }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f"Analysis JSON parse failed: {e}")
        except Exception as e:
            logger.warning(f"Analysis failed: {e}")

        # Fallback: moderate satisfaction, no sub-questions
        return {
            'satisfaction': 50 if narrative else 20,
            'sub_questions': [],
            'summary': narrative[:200] if narrative else 'No findings.',
        }

    async def _store_knowledge(
        self,
        item: Dict,
        summary: str,
        narrative: str,
        satisfaction: int,
        hierarchical_memory,
    ) -> None:
        """Store knowledge immediately in hierarchical memory."""
        from core.hierarchical_memory import EpisodeCategory

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        item_id = item['id']

        # Extract topic words for tags
        words = {w.lower() for w in item['question'].split() if len(w) > 4}
        tags = {'curiosity_exploration', item.get('source', 'self')}
        if item.get('topic'):
            tags.add(item['topic'].lower().replace(' ', '_'))
        tags.update(list(words)[:5])

        # Store as episode
        episode_id = f"curiosity_{item_id}_{timestamp}"
        try:
            hierarchical_memory.add_episode(
                episode_id=episode_id,
                category=EpisodeCategory.LEARNING,
                description=f"Explored: {item['question'][:120]}",
                content={
                    'question': item['question'],
                    'summary': summary,
                    'narrative': narrative[:500],
                    'satisfaction': satisfaction,
                    'source': item.get('source', 'self'),
                },
                success=satisfaction >= self.get_threshold(item.get('depth', 0)),
                emotional_valence=0.6 if satisfaction >= 50 else 0.3,
                importance=0.8,
                tags=tags,
            )
        except Exception as e:
            logger.debug(f"Episode storage failed: {e}")

        # Store as semantic knowledge (immediate!)
        knowledge_id = f"curiosity_knowledge_{item_id}_{timestamp}"
        concept = item['question'][:80]
        description = f"{summary}\n\nExplored via: {item.get('source', 'self')} (satisfaction: {satisfaction}%)"

        try:
            hierarchical_memory.add_semantic_knowledge(
                knowledge_id=knowledge_id,
                concept=concept,
                description=description,
                confidence=satisfaction / 100.0,
                source_episodes=[episode_id],
                tags=tags,
            )
            hierarchical_memory._save_state()
            logger.info(f"Knowledge stored: \"{concept[:50]}\" (confidence={satisfaction/100:.1f})")
        except Exception as e:
            logger.debug(f"Knowledge storage failed: {e}")

    def _spawn_sub_items(self, item: Dict, sub_questions: List[str]) -> int:
        """Create sub-curiosity-items from analysis gaps."""
        created = 0
        for q in sub_questions[:self.MAX_SUB_ITEMS]:
            if not q or len(q.strip()) < 10:
                continue
            item_id = self.add_item(
                question=q.strip(),
                topic=item.get('topic', ''),
                source='sub_item',
                parent_id=item['id'],
            )
            if item_id:
                created += 1
        return created
