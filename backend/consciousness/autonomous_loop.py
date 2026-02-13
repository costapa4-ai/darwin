"""
Autonomous Loop — Shared agentic tool execution for chat and consciousness cycles.

Provides:
- Tool call parsing (```tool_call blocks)
- Tool execution with safety whitelist
- run_autonomous_loop() — LLM → tools → results → LLM → repeat

Used by:
- consciousness_routes.py (chat agentic loop)
- consciousness_engine.py (autonomous wake cycle goals)
"""

import json
import re

from utils.logger import get_logger as _get_logger

logger = _get_logger(__name__)

# Pattern to match ```tool_call ... ``` blocks in LLM responses
TOOL_CALL_RE = re.compile(r'```tool_call\s*\n?(.*?)\n?```', re.DOTALL)

# Phrases that signal the goal is complete (case-insensitive check)
DONE_SIGNALS = [
    'goal complete', 'goal achieved', 'task complete', 'task done',
    'summary:', '## summary', '## findings', '## conclusion',
    'i have completed', 'i\'ve completed', 'investigation complete',
    'analysis complete', 'exploration complete',
]

# Tools allowed for execution (chat + autonomous)
ALLOWED_TOOLS = {
    'backup_tool.create_full_backup',
    'backup_tool.list_backups',
    'backup_tool.verify_backup',
    'file_operations_tool.read_file',
    'file_operations_tool.write_file',
    'file_operations_tool.append_file',
    'file_operations_tool.list_directory',
    'file_operations_tool.file_info',
    'file_operations_tool.search_files',
    'script_executor_tool.execute_python',
}


def get_tool_manager():
    """Get the ToolManager instance for executing tools."""
    try:
        from app.lifespan import get_service
        registry = get_service('tool_registry')
        if registry:
            return getattr(registry, 'tool_manager', None)
    except Exception:
        pass
    return None


def parse_tool_call(raw: str) -> dict:
    """Parse a tool call JSON string, with repair for truncated JSON."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        repaired = raw.rstrip(',')
        if repaired.count('"') % 2 == 1:
            repaired += '"'
        while repaired.count('{') > repaired.count('}'):
            repaired += '}'
        while repaired.count('[') > repaired.count(']'):
            repaired += ']'
        return json.loads(repaired)


async def execute_tool(tool_name: str, args: dict, tm) -> str:
    """Execute a single tool and return formatted result string."""
    if tool_name not in ALLOWED_TOOLS:
        return f"⚠️ Tool '{tool_name}' not available"

    func = tm.tool_functions.get(tool_name)
    if not func:
        return f"⚠️ Tool '{tool_name}' not found"

    try:
        import asyncio
        if asyncio.iscoroutinefunction(func):
            result = await func(**args)
        else:
            result = func(**args)

        if isinstance(result, dict):
            if result.get('success', True):
                # Give file reads more content so Darwin can actually analyze code
                max_content = 4000 if 'read_file' in tool_name else 1000
                display = {k: v for k, v in result.items()
                           if k != 'content' or len(str(v)) < max_content}
                if 'content' in result and len(str(result['content'])) >= max_content:
                    display['content'] = str(result['content'])[:max_content] + '... [truncated]'
                return f"✅ {tool_name}: {json.dumps(display, indent=2, default=str)}"
            else:
                return f"❌ {tool_name}: {result.get('error', 'Unknown error')}"
        return f"✅ {tool_name}: {str(result)[:1000]}"

    except Exception as e:
        return f"❌ {tool_name} error: {e}"


async def extract_and_execute_tools(response_text: str, tm) -> tuple:
    """
    Extract tool_call blocks from response, execute them, return (clean_text, results_list).
    Returns (original_text, []) if no tool calls found.
    """
    matches = TOOL_CALL_RE.findall(response_text)
    if not matches:
        return response_text, []

    results = []
    for match in matches:
        raw = match.strip()
        try:
            call = parse_tool_call(raw)
            tool_name = call.get('tool', '')
            if 'args' in call:
                args = call['args'] if isinstance(call['args'], dict) else {}
            else:
                args = {k: v for k, v in call.items() if k != 'tool'}

            result_str = await execute_tool(tool_name, args, tm)
            results.append(result_str)

        except json.JSONDecodeError:
            results.append(f"⚠️ Invalid JSON: {raw[:100]}")
        except Exception as e:
            results.append(f"❌ Error: {e}")

    clean_text = TOOL_CALL_RE.sub('', response_text).strip()
    return clean_text, results


async def run_autonomous_loop(
    goal: str,
    system_prompt: str,
    router,
    tool_manager=None,
    max_iterations: int = 5,
    max_tokens: int = 1500,
    preferred_model: str = 'haiku',
    timeout: int = 45,
) -> dict:
    """
    LLM-driven autonomous action loop.

    Darwin pursues a goal by generating actions, executing tools,
    and iterating until the goal is addressed or max iterations reached.

    Returns: {
        "narrative": str,      # What Darwin decided/learned
        "tool_results": list,  # Results from tools executed
        "iterations": int,     # How many loops completed
    }
    """
    tm = tool_manager or get_tool_manager()

    collected_narrative = []
    collected_results = []
    iterations = 0

    for iteration in range(max_iterations):
        iterations = iteration + 1

        if iteration == 0:
            prompt = goal
        else:
            # Keep context compact for Ollama: only last 3 results, truncated
            recent = collected_results[-3:]
            trimmed = [r[:800] + '...' if len(r) > 800 else r for r in recent]
            results_text = "\n".join(trimmed)
            prompt = (
                f"Your goal: {goal}\n\n"
                f"Tools executed so far (latest {len(recent)}):\n{results_text}\n\n"
                f"Continue: if you need more actions, use tool_call. "
                f"If you have enough information, write a brief summary of what you did and learned (no tool_call)."
            )

        try:
            result = await router.generate(
                task_description="autonomous goal pursuit",
                prompt=prompt,
                system_prompt=system_prompt,
                context={'activity_type': 'autonomous'},
                preferred_model=preferred_model,
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=timeout,
            )
            response = result.get("result", "").strip()
        except Exception as e:
            logger.warning(f"Autonomous loop LLM error: {e}")
            break

        if not response:
            break

        # Check for tool calls
        if '```tool_call' not in response or not tm:
            collected_narrative.append(response)
            break

        # Extract and execute tools
        narrative, tool_results = await extract_and_execute_tools(response, tm)
        if narrative:
            collected_narrative.append(narrative)
        collected_results.extend(tool_results)

        if not tool_results:
            break

        # --- Smart early stopping ---

        # 1. Check if narrative contains completion signals
        if narrative:
            narrative_lower = narrative.lower()
            if any(signal in narrative_lower for signal in DONE_SIGNALS):
                logger.info(f"🏁 Goal complete signal detected at iteration {iterations}")
                break

        # 2. Stop after write_file — the deliverable is done
        wrote_file = any('write_file' in r for r in tool_results)
        if wrote_file and iteration >= 1:
            logger.info(f"🏁 File written, goal likely complete at iteration {iterations}")
            break

        # 3. Stop if only errors in this iteration (no progress)
        all_failed = all(r.startswith('❌') or r.startswith('⚠️') for r in tool_results)
        if all_failed and iteration >= 2:
            logger.info(f"🏁 No progress (all tools failed), stopping at iteration {iterations}")
            break

    return {
        "narrative": "\n\n".join(collected_narrative),
        "tool_results": collected_results,
        "iterations": iterations,
    }
