"""
CuriosityEngine — Human-aligned curiosity-driven exploration cycle.

Replaces random goal selection with structured thinking:
  Curiosity Item -> Plan -> Execute -> Analyze -> Satisfy or Spawn Sub-Items

Knowledge is stored immediately on satisfaction (>= 80%).
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
    SATISFACTION_THRESHOLD = 80
    EXPIRY_DAYS = 7
    MAX_SUB_ITEMS = 3

    def __init__(self, db_path: str = "./data/darwin.db"):
        self.db_path = db_path
        self._init_db()
        stats = self.get_queue_stats()
        logger.info(f"CuriosityEngine initialized ({stats['pending']} pending, {stats['exploring']} exploring)")

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

        # Check for duplicate questions
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM curiosity_items WHERE question = ? AND status IN ('pending', 'exploring')",
            (question.strip(),)
        ).fetchone()
        if existing:
            return existing['id']

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
                depth = getattr(interest, 'depth', 0)
                if depth < 3:
                    question = f"What are the key concepts and recent developments in {topic}?"
                elif depth < 6:
                    question = f"What advanced techniques or open problems exist in {topic}?"
                else:
                    question = f"What are the frontier research questions in {topic}?"

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
                cursor = conn.execute(
                    """UPDATE curiosity_items SET status = 'satisfied', satisfaction = 80, satisfied_at = ?
                       WHERE id = ? AND status = 'exploring'""",
                    (now, pid)
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

        # Phase 4: STORE or SPAWN
        knowledge_stored = False
        sub_items_created = 0

        if satisfaction >= self.SATISFACTION_THRESHOLD:
            # Satisfied! Store knowledge immediately
            await self._store_knowledge(item, summary, narrative, satisfaction, hierarchical_memory)
            self.update_item(
                item_id,
                status='satisfied',
                knowledge_stored=1,
                satisfied_at=datetime.utcnow().isoformat()
            )
            knowledge_stored = True
            logger.info(f"Curiosity #{item_id} satisfied ({satisfaction}%), knowledge stored")
        else:
            # Not satisfied — spawn sub-items (but not for dead ends)
            # Skip spawning if satisfaction is very low (question is unanswerable)
            # or if we're already at depth 2+ with low satisfaction
            can_spawn = (
                sub_questions
                and item['depth'] < self.MAX_DEPTH
                and satisfaction >= 15  # Below 15% means the question is a dead end
                and not (item['depth'] >= 2 and satisfaction < 30)
            )
            if can_spawn:
                sub_items_created = self._spawn_sub_items(item, sub_questions)

            if sub_items_created > 0:
                # Parent stays 'exploring' — will be satisfied when children are done
                logger.info(f"Curiosity #{item_id} not satisfied ({satisfaction}%), spawned {sub_items_created} sub-questions")
            else:
                # Can't go deeper — store what we have
                if narrative and len(narrative.strip()) > 30:
                    await self._store_knowledge(item, summary, narrative, satisfaction, hierarchical_memory)
                    self.update_item(
                        item_id,
                        status='satisfied',
                        knowledge_stored=1,
                        satisfied_at=datetime.utcnow().isoformat()
                    )
                    knowledge_stored = True
                else:
                    self.update_item(item_id, status='satisfied')

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

Available tools: file_operations (read/write/list/search files), web_search (search/fetch URLs), script_executor (run Python)

Write a brief plan (2-3 steps) for how to investigate this question.
Be specific about what files to read, what to search for, or what to run.

Plan:"""

        try:
            result = await router.generate(
                task_description="curiosity exploration planning",
                prompt=prompt,
                system_prompt="You are Darwin planning how to investigate a question. Be concrete and actionable. Use the tools available.",
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

AVAILABLE TOOLS:
- file_operations_tool.read_file — args: file_path (string)
- file_operations_tool.list_directory — args: dir_path (string), pattern (string, default "*")
- file_operations_tool.search_files — args: dir_path (string), text (string)
- script_executor_tool.execute_python — args: code (string), description (string)
- web_search_tool.search — args: query (string), max_results (int, default 5)
- web_search_tool.fetch_url — args: url (string)

FORMAT — you MUST use this exact format to call tools:
```tool_call
{"tool": "web_search_tool.search", "args": {"query": "your search query"}}
```

RULES:
1. ALWAYS start your response with a ```tool_call block to gather information
2. Use web_search_tool.search for factual/external questions
3. Use file_operations_tool for questions about Darwin's own code or data
4. Use script_executor_tool.execute_python for calculations or data analysis
5. When you have enough information, write a summary WITHOUT tool_call blocks
6. NEVER just describe what you would do — actually call the tools"""

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
        tools_used = len(execution.get('tool_results', []))

        prompt = f"""You wanted to answer: {item['question']}
Your plan was: {plan[:300]}
What you found ({tools_used} tools used): {narrative[:600]}

Evaluate:
1. How satisfied are you with the answer? (0-100, where 100 means fully answered)
2. If below 80, what 1-3 specific sub-questions would help fill the gaps?
3. Brief summary of what you learned (1-2 sentences).

Reply with ONLY valid JSON:
{{"satisfaction": <int>, "sub_questions": ["..."], "summary": "..."}}
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
                success=satisfaction >= self.SATISFACTION_THRESHOLD,
                emotional_valence=0.6 if satisfaction >= self.SATISFACTION_THRESHOLD else 0.2,
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
