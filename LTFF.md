# Long-Term Future Fund (LTFF) Application

**Deadline: February 15, 2026**
**Apply at:** https://av20jp3z.paperform.co/?fund=Long-Term%20Future%20Fund

---

## Fund Selection

Long-Term Future Fund

## Transfer to EAIF if better fit?

Yes

## OP Funding Status

Individual

## Organization

*(leave blank)*

---

## Short Description (max 120 chars)

```
Empirical AI safety research: measuring alignment drift in a running self-modifying AI system with 7-layer safety constraints
```

---

## Summary (max 1,000 chars)

```
Darwin is a running, open-source autonomous AI system that modifies its own code, evolves its own prompts through tournament selection, and pursues self-directed goals — constrained by a 7-layer safety architecture designed to study how self-modification can be made safe.

Unlike theoretical alignment work, Darwin produces empirical data: 6,809 autonomous actions logged (81.9% success rate), prompt evolution tournaments across 6 evolvable slots with auto-rollback when variants score below 90% of baseline, code validation with correction loops, and 420 wake/sleep consciousness cycles.

Safety mechanisms include: protected files whitelist (16 critical files immune to self-modification), tiered model routing (less capable local models for routine tasks), tool execution whitelist (10 allowed tools), and forced rest cycles with memory cleanup.

This grant funds 6 months publishing this data as the first empirical study of alignment properties in a continuously-operating self-modifying AI, plus instrumentation for longitudinal safety-event tracking.

Solo developer in Portugal. All code will be published open-source.
```

---

## Project Goals

```
GOAL 1: Publish empirical safety data from Darwin (months 1-3)

Write a detailed technical post on LessWrong/Alignment Forum documenting:
- Darwin's 7-layer safety architecture as a reusable pattern
- 6+ months of operational data: prompt evolution rollback rates, code validation pass rates, autonomous goal-pursuit patterns
- Honest failure analysis: hallucination incidents, goal repetition bugs, timeout failures
- Raw datasets published on GitHub

Success metrics:
- Published post with 5+ data visualizations from existing logs
- Raw datasets (13,000+ data points) published publicly
- Architecture documented well enough for others to implement similar safety constraints

Data sources already exist:
- consciousness_state.json: 218 wake cycles, 202 sleep cycles, 5,848 activities
- activity_monitor_state.json: 6,809 activities with success/failure by category
- prompt_evolution/prompt_registry.json: tournament scores across 6 prompt slots
- darwin.db: 69 code executions with fitness scores, 35 tracked intentions, safety_events table (newly instrumented)
- 167 exploration expeditions, 1,756 dream records, 98 learning sessions

GOAL 2: Add safety instrumentation and run extended study (months 2-6)

Per-event logging for every safety mechanism activation has already been deployed:
- Prompt rollback events (variant ID, score delta, slot)
- Protected file redirect attempts (which file, what modification was attempted)
- Tool whitelist rejections (what tool was requested)
- Model routing decisions (task complexity, model chosen, why)
- Early stop triggers (done_signal, write_file, all_failed)
- Model fallbacks and truncation retries

Run Darwin continuously for 6 months with this instrumentation. Produce a longitudinal dataset of safety events for the alignment research community.

Success metrics:
- Safety event logger already deployed and capturing data
- 10,000+ safety events logged over 6 months
- Follow-up post with longitudinal analysis published by month 6

RISKS:
- Compute costs could exceed budget if autonomous loops consume more API tokens than projected. Mitigated: already switched to free local Ollama for ~90% of operations, cloud API only for complex decisions.
- Solo capacity bottleneck for writing + engineering simultaneously. Mitigated: Darwin runs autonomously, research is primarily analysis of existing behavior data.
- Safety events may be too rare to produce statistically significant findings. Mitigated: will also publish negative result ("safety mechanisms rarely fire because constraints are well-calibrated") which is itself valuable.
```

---

## Track Record

```
I've built Darwin independently over several months, progressing from a basic multi-model router to a fully autonomous self-evolving AI system:

Technical achievements:
- Multi-model routing system across 4 providers (Claude, Gemini, OpenAI, Ollama) with automatic complexity-based task assignment and fallback chains
- Self-evolving prompt system with tournament selection: 6 evolvable prompt slots, max 8 variants each, auto-rollback at <90% baseline performance, permanent retirement after 3 rollbacks
- Autonomous consciousness cycles: Darwin decides its own goals via LLM, executes multi-step tool chains (up to 20 iterations), writes analysis documents, creates backups — without human intervention
- 7-layer safety architecture: protected files, code validation loops, prompt evolution constraints, capability tiering, tool whitelisting, forced rest cycles, memory cleanup
- Solved real engineering challenges: code truncation detection across 4 model clients, dynamic token scaling, Ollama timeout handling with cloud fallback, anti-hallucination grounding

Current system metrics:
- 6,809 autonomous activities logged, 81.9% success rate
- 420 wake/sleep cycles completed
- 26 self-written analysis documents
- 21 self-implemented code improvements
- Running 24/7 for months on Docker with Ollama (local) + cloud APIs

I'm a software engineer based in Portugal. No academic affiliation. All work is self-funded.
```

---

## Public Portfolio

```
Darwin source code: hosted on private Gitea instance, will be published on GitHub as part of this grant (open-source commitment is a core deliverable)

Darwin's self-written outputs (samples available on request):
- "Integrated Self-Understanding Framework" — 4.2KB structured analysis Darwin wrote about its own memory architecture
- "Memory Identity Analysis" — 7.3KB self-examination of identity formation
- 26 total analysis documents written autonomously

I have not previously published on LessWrong or the Alignment Forum. This grant's primary deliverable is my first publication there.
```

---

## Requested Amount (USD)

```
8000
```

---

## Funding Amount & Breakdown

```
$8,000 USD over 6 months (February-August 2026)

Breakdown:
- Cloud API compute (Claude Haiku for goal decisions + chat): $3,600 (45%)
  ~$600/month, covering Darwin's autonomous loop API calls.
  90% of operations already run on free local Ollama.
- GPU upgrade for local inference: $2,000 (25%)
  Currently running Ollama on CPU (~7 tok/s). A GPU would increase
  throughput 10-20x, enabling richer autonomous behavior and faster
  iteration on safety experiments.
- Publication and data hosting: $500 (6%)
  Domain hosting for public datasets, chart generation tools,
  potential arXiv formatting.
- Buffer for unexpected compute spikes: $1,900 (24%)
  Safety margin for periods of intensive autonomous operation
  or additional cloud API usage during instrumentation testing.

Note: This is a side project alongside my regular employment.
All work is self-funded so far. I am also applying to NGI Zero
Commons Fund (EU) and Manifund for complementary funding — there
is no overlap in budget items between applications.
```

---

## Alternatives to Funding

```
Currently self-funding all compute costs (~$3-5/day for cloud API).

Other funding applications planned or in progress:
- NGI Zero Commons Fund (NLnet, EU): applying March 2026, EUR 5,000-50,000, status: preparing application
- Manifund AI Safety Regranting: applying February 2026, $5,000-$50,000, status: not yet submitted
- Anthropic Startup Program: planned, API credits (not cash), status: not yet submitted

No other active funding. No institutional backing. No Open Philanthropy funding.

If this grant is not funded, I will continue the project self-funded but at a slower pace, with publication likely delayed 3-6 months.
```

---

## Checklist

- [ ] Go to https://av20jp3z.paperform.co/?fund=Long-Term%20Future%20Fund
- [ ] Select "Long-Term Future Fund"
- [ ] Select "Yes" for transfer to EAIF
- [ ] Check scope confirmation box
- [ ] Select "Individual" for OP Funding Status
- [ ] Fill in your name
- [ ] Fill in your email
- [ ] Leave Organization blank
- [ ] Paste Short Description
- [ ] Paste Summary
- [ ] Paste Project Goals
- [ ] Paste Track Record
- [ ] Paste Public Portfolio
- [ ] Enter 8000 as Requested Amount
- [ ] Paste Funding Breakdown
- [ ] Paste Alternatives to Funding
- [ ] Submit before February 15, 2026
