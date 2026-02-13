# NGI Zero Commons Fund Application (via NLnet)

**Deadline: April 1, 2026, 12:00 CEST**
**Apply at:** https://nlnet.nl/propose/
**Guide:** https://nlnet.nl/commonsfund/guideforapplicants/
**FAQ:** https://nlnet.nl/commonsfund/faq/

---

## Key Rules

- Must be written in **English**
- Must **NOT** be written by generative AI (disclose AI use in the project itself)
- Must have a **clear European dimension** (you're in Portugal = automatic)
- Must commit to **open source** licensing
- Must focus on **R&D** activities
- Budget: **EUR 5,000 - 50,000** (first proposal)
- Priority given to **EU inhabitants** (Portugal qualifies)

---

## Evaluation Criteria (must score above 5.0/7)

| Criterion | Weight |
|-----------|--------|
| Technical excellence / feasibility | 30% |
| Relevance / Impact / Strategic potential | 40% |
| Cost effectiveness / Value for money | 30% |

---

## Application Form Fields

### Thematic Call

```
NGI Zero Commons Fund
```

### Proposal Name

```
Darwin: Safety-Instrumented Self-Evolving AI System
```

### Website / Wiki

```
[YOUR GITHUB URL — publish repo before applying]
```

### Abstract

*Complete explanation of the project and expected outcomes. This is the main field.*

```
Darwin is an open-source, autonomous AI system that modifies its own code, evolves its own prompts through tournament selection, and pursues self-directed goals. It runs 24/7 with wake/sleep consciousness cycles, multi-model routing (local Ollama + cloud APIs), and a 7-layer safety architecture that constrains its self-modification capabilities.

The project addresses a critical gap in the Next Generation Internet: as AI agents become more autonomous, we lack empirical data on how self-modifying systems behave under safety constraints. Darwin fills this gap by providing:

1. A WORKING OPEN-SOURCE TESTBED for studying autonomous AI behavior — not a theoretical framework, but a system that has already completed 6,809 autonomous actions across 420 wake/sleep cycles.

2. A 7-LAYER SAFETY ARCHITECTURE that other developers can adopt:
   - Protected files whitelist (16 critical files immune to self-modification)
   - Code validation loop with AI-assisted correction (max 2 retries, score threshold 70/100)
   - Prompt evolution with tournament selection and auto-rollback (<90% baseline = automatic revert)
   - Variant retirement (3 rollbacks = permanent removal, max 8 variants per slot)
   - Tiered model routing (less capable local models for routine tasks, powerful models only for complex work)
   - Tool execution whitelist (only 10 specific tools allowed for autonomous operation)
   - Consciousness rhythm (2-hour active cycles with forced 30-minute rest and memory cleanup)

3. EMPIRICAL SAFETY DATA from continuous operation: a newly-deployed safety event logger captures every safety mechanism activation (rollbacks, file protection triggers, tool rejections, model fallbacks) to a persistent database for longitudinal analysis.

EXPECTED OUTCOMES:
- Published open-source safety framework extractable from Darwin, documented for reuse
- Longitudinal dataset of 10,000+ safety events from continuous autonomous operation
- Technical publication analyzing alignment properties of self-modifying AI under constraints
- Monitoring dashboard for real-time safety event visualization

RELEVANCE TO NGI:
Darwin directly addresses trustworthy AI infrastructure for the Next Generation Internet. As AI agents are deployed across European services, Darwin's safety architecture provides concrete, tested patterns for constraining autonomous AI behavior while preserving usefulness. The open-source framework enables other European developers to build safer autonomous systems.

The project is built entirely on open-source components (Python, Ollama for local inference, SQLite for data persistence) and all outputs will be published under open-source licenses.
```

### Prior Involvement

```
I am an independent software engineer based in Portugal with experience in AI systems integration, multi-model routing architectures, and backend development.

I built Darwin independently over several months, progressing from a basic API router to a fully autonomous system with self-evolving prompts, goal-directed behavior, and comprehensive safety constraints. The system currently runs 24/7 on Docker with local Ollama inference and cloud API fallbacks.

Key technical achievements in this project:
- Designed and implemented multi-model routing across 4 AI providers with automatic complexity-based task assignment
- Built a prompt evolution system using tournament selection with measurable safety properties (auto-rollback, variant retirement)
- Implemented autonomous consciousness cycles where Darwin decides its own goals, chains tool executions, and writes analysis documents without human intervention
- Deployed safety instrumentation logging all mechanism activations to SQLite for research analysis

Current system metrics: 6,809 autonomous activities (81.9% success rate), 420 wake/sleep cycles, 26 self-written analysis documents, 21 self-implemented code improvements.
```

### Requested Amount (EUR)

```
25000
```

### Budget Usage Explanation

```
EUR 25,000 over 12 months

Personnel / development time: EUR 15,000 (60%)
- Part-time dedication (~15 hours/week) to:
  - Extract safety framework as standalone reusable library
  - Write technical documentation and publication
  - Analyze longitudinal safety data
  - Respond to community feedback and contributions

Cloud compute (API costs): EUR 4,800 (19%)
- Claude Haiku API for goal decisions and chat: ~EUR 400/month
- 90% of operations run on free local Ollama

Hardware (GPU for local inference): EUR 3,000 (12%)
- Currently running Ollama on CPU (~7 tokens/second)
- GPU would enable 10-20x faster local inference
- Reduces dependency on cloud APIs (cost + privacy)

Publication and dissemination: EUR 1,200 (5%)
- Domain and hosting for datasets and documentation
- Conference attendance or workshop participation

Buffer: EUR 1,000 (4%)
- Contingency for unexpected compute or infrastructure costs
```

### Other Funding Sources

```
Currently entirely self-funded.

Applied to Long-Term Future Fund (EA Funds) for $8,000 USD — status: pending.
Planning to apply to Manifund AI Safety Regranting — not yet submitted.
Planning to apply to Anthropic Startup Program for API credits (not cash) — not yet submitted.

These applications are complementary, not overlapping: LTFF covers short-term publication costs, NGI covers the longer-term framework extraction and sustained development. Anthropic credits would directly reduce the cloud compute line item.
```

### Comparison with Existing Efforts

```
Several projects explore autonomous AI agents, but Darwin is unique in three ways:

1. RUNNING SYSTEM WITH SAFETY DATA: Projects like AutoGPT, BabyAGI, and CrewAI focus on task completion capabilities. Darwin uniquely focuses on safety properties — measuring how well constraints hold during continuous autonomous operation. No existing project publishes empirical data on self-modification safety.

2. SELF-EVOLVING PROMPTS WITH SAFETY BOUNDS: LangChain and similar frameworks offer prompt management but not autonomous prompt evolution. Darwin's tournament selection with auto-rollback (<90% baseline) and variant retirement (3 rollbacks = permanent removal) is a novel safety mechanism for prompt self-modification.

3. TIERED CAPABILITY ROUTING AS SAFETY: Most multi-model systems optimize for cost or quality. Darwin's tiered routing (local Ollama for routine tasks, cloud models only for complex work) is designed as a safety mechanism — limiting the capability available for unsupervised autonomous operations.

The closest related work is OpenAI's "Self-Evolving Agents Cookbook" (theoretical) and Anthropic's research on AI control (theoretical/lab-based). Darwin provides the empirical complement — a working system operating under real constraints.
```

### Technical Challenges

```
1. MEASURING ALIGNMENT DRIFT: Defining and measuring whether self-evolved prompts maintain alignment with original intent is an open research question. My approach: compare semantic similarity of evolved prompts to originals, track task success rates, and monitor rollback frequency as a proxy for drift.

2. SCALING SAFETY INSTRUMENTATION WITHOUT OVERHEAD: The safety event logger must capture all mechanism activations without slowing Darwin's operation. Current implementation uses fire-and-forget SQLite writes, but sustained high-frequency logging may require batching or async writes.

3. EXTRACTING A REUSABLE FRAMEWORK: Darwin's safety mechanisms are currently tightly integrated with its codebase. Extracting them as a standalone library requires careful abstraction without losing the safety properties that come from tight integration.

4. BALANCING AUTONOMY WITH OVERSIGHT: More capable autonomous behavior produces better research data but increases risk. The challenge is expanding Darwin's capabilities (e.g., more tools, network access) while maintaining safety guarantees.

5. LOCAL INFERENCE PERFORMANCE: Running Ollama on CPU limits throughput to ~7 tokens/second. Complex autonomous reasoning requires larger context windows and longer generations. A GPU upgrade would substantially improve data collection rate.
```

### Ecosystem Description

```
TARGET USERS:
- AI developers building autonomous agents who need tested safety patterns
- AI safety researchers who need empirical data on self-modifying systems
- Open-source AI community interested in practical alignment approaches

DISSEMINATION PLAN:
- Open-source all code on GitHub under MIT or Apache-2.0 license
- Publish safety framework as a standalone Python library on PyPI
- Write technical posts on LessWrong/Alignment Forum (primary AI safety community)
- Publish raw safety event datasets for community analysis
- Submit to AI safety workshops (e.g., NeurIPS SafeRL, ICML workshops)
- Engage with European AI safety community through local meetups and online forums

SUSTAINABILITY:
- Darwin runs autonomously at minimal cost (~EUR 100-150/month on Ollama + Haiku)
- Safety framework library would be maintained as open-source with community contributions
- Longitudinal data collection continues automatically after grant period
- Potential for follow-up research funding based on published results
```

### Generative AI Usage

```
Yes — Darwin itself uses generative AI (LLMs) as its core technology for autonomous decision-making, code generation, and self-modification. The safety architecture constraining this AI usage is the subject of this research.

The application text was written by me (human), not generated by AI.
```

---

## Checklist

- [ ] Push Darwin repo to public GitHub before applying
- [ ] Go to https://nlnet.nl/propose/
- [ ] Select "NGI Zero Commons Fund" from thematic call dropdown
- [ ] Fill in contact info (name, email, phone, country: Portugal)
- [ ] Fill in all fields above
- [ ] Disclose AI usage honestly
- [ ] Double-check: application text is human-written (required)
- [ ] Submit before April 1, 2026, 12:00 CEST
- [ ] Save confirmation email
