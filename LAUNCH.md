# SwarmTrace — Launch Copy

---

## ProductHunt

### Name
SwarmTrace

### Tagline (60 chars max)
Time-travel debugger for multi-agent AI pipelines

### Description
Debugging multi-agent LLM systems is painful. When a 4-agent pipeline fails, you don't know which agent caused it, logs are flat, and you have to re-run the entire workflow from scratch to test a fix.

SwarmTrace solves this with three things:

**1. Span Tree Visualisation**
Every agent action is recorded as an OpenTelemetry span and rendered as an interactive graph. You can see exactly which agent ran, in what order, with what input and output — and how long each step took.

**2. Time-Travel Replay**
Click any past step, edit the prompt or tool output, and replay only the downstream agents. No re-running from scratch. The forked run is saved as a new trace so you can compare both runs side by side.

**3. LLM-as-Judge Evaluation**
Each agent's output is automatically scored by a judge LLM. Scores surface which agents are failing and why — so you know where to focus.

**Also includes:**
- WebSocket live streaming — watch the span tree update in real time as agents run
- OTLP export — compatible with Jaeger, Grafana Tempo, Datadog
- PyPI SDK — `pip install swarmtrace` and instrument your agents in minutes
- Full RBAC (admin/developer/viewer) and audit logs
- Stripe-ready billing infrastructure

**Try it now — no sign-up needed.**
Click "Try Demo →" on the login page for instant access to a live trace.

### First Comment (post this yourself immediately after launch)
Hey PH! 👋 I'm Leo, I built SwarmTrace after spending way too many hours re-running entire agent pipelines just to debug one bad prompt.

The core insight was: multi-agent debugging needs the same primitives as distributed systems tracing — parent-child span relationships, state snapshots at every step, and checkpoint-based replay. OpenTelemetry already solves this for microservices. SwarmTrace brings it to LLM agents.

A few things I'd love feedback on:
- Is time-travel replay the right mental model, or is there a better framing?
- What's your biggest pain point when debugging multi-agent systems today?
- Would you self-host this or prefer a managed cloud version?

Live demo (no sign-up): https://swarm-trace.vercel.app
GitHub: https://github.com/codewithleo1/SwarmTrace

### Topics
- Artificial Intelligence
- Developer Tools
- Open Source
- LLM
- Debugging

### Links
- Website: https://swarmtrace-landing.vercel.app
- Demo: https://swarm-trace.vercel.app
- GitHub: https://github.com/codewithleo1/SwarmTrace

---

## Show HN (post when account karma > 10)

**Title:**
Show HN: SwarmTrace – Debug multi-agent AI with time-travel replay

**Body:**
I built SwarmTrace because debugging multi-agent LLM pipelines is painful.
When a 4-agent system fails, you don't know which agent caused it, logs
are flat, and you have to re-run everything from scratch to test a fix.

SwarmTrace records every agent action as an OpenTelemetry span tree,
visualises it as an interactive graph, and lets you fork execution from
any past step — edit a prompt or tool output and replay only the
downstream agents.

Live demo (no sign-up): https://swarm-trace.vercel.app
GitHub: https://github.com/codewithleo1/SwarmTrace

Stack: FastAPI + LangGraph + Neon Postgres + React Flow + Groq

---

## Reddit — r/LangChain (POSTED ✅)

8 upvotes, 928 views, 3 comments as of Aug 12 2026.

## Reddit — r/LocalLLaMA (REMOVED by mods)

New account restriction. Retry after karma builds.

## Reddit — r/MachineLearning (PENDING)

Post after karma builds on r/LangChain.

---

## Key Messages (use across all channels)

**One-liner:**
SwarmTrace lets you fork a failing agent pipeline from any past step and replay only the downstream agents.

**Problem:**
When a 4-agent LLM pipeline fails, you don't know which agent caused it and have to re-run everything from scratch.

**Solution:**
OpenTelemetry span trees + time-travel state replay + LLM-as-judge evaluation.

**Differentiator vs LangSmith/Langfuse:**
They show you traces. SwarmTrace lets you replay and fix them — without re-running the whole pipeline.

---

## Demo Credentials (for sharing)
URL: https://swarm-trace.vercel.app
Click "Try Demo →" — no sign-up needed.
