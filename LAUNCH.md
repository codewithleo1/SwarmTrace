# SwarmTrace — Launch Copy

> Ready-to-post copy for HackerNews and ProductHunt.
> Post whenever you feel ready — ideally Tuesday–Thursday 9am ET for best visibility.

---

## HackerNews — Show HN

**Title:**
Show HN: SwarmTrace – Open-source observability + time-travel debugger for AI agents

**Body:**
I built SwarmTrace to solve a problem I kept hitting: when a multi-agent AI pipeline fails,
you have no idea which agent caused it, and you have to re-run the entire thing from scratch to test a fix.

SwarmTrace records every agent action as a hierarchical OpenTelemetry span tree, then lets you
"fork" execution from any past step — edit a prompt or tool output, and replay only the downstream
agents. No re-running the full pipeline.

Features:
- Interactive span tree visualization (React Flow)
- Time-travel replay — fork from any step, compare original vs forked runs side by side
- LLM-as-a-judge — automatic quality scoring (relevance, reasoning, quality) per agent span
- Cost tracking per span using Groq token pricing
- Webhook alerts on FAILED or LOOP_DETECTED traces
- Multi-tenancy — projects, scoped API keys
- Dashboard metrics — success rate, avg latency, cost, daily chart
- Self-hostable via Docker Compose

Stack: FastAPI + asyncpg + Neon Postgres + LangGraph + React + @xyflow/react

Live demo: https://swarm-trace.vercel.app
GitHub: https://github.com/codewithleo1/SwarmTrace

Would love feedback on the time-travel replay UX — is this useful for how you debug agents?

---

## ProductHunt

**Tagline:**
Time-travel debugging for AI agent pipelines

**Description:**
SwarmTrace is an open-source observability platform for multi-agent AI systems.

When your AI pipeline fails, SwarmTrace shows you exactly which agent caused it —
then lets you fork execution from that exact step, edit the prompt or output,
and replay only the downstream agents. No re-running the full pipeline.

Key features:
→ Interactive span tree — visualize every agent action as a hierarchical graph
→ Time-travel replay — fork from any past step and compare runs side by side
→ LLM-as-a-judge — automatic quality scoring per agent span
→ Cost tracking — exact USD cost per span and per trace
→ Webhook alerts — get notified on failures instantly
→ Self-hostable — one command with Docker Compose

Built with FastAPI, React, LangGraph, and OpenTelemetry.
Free and open source.

**First comment (post this yourself on launch day):**
Hey PH! Builder here.

The core insight behind SwarmTrace: debugging multi-agent systems is fundamentally
different from debugging regular code. The failure isn't a line number — it's an
agent that made a bad decision 3 steps ago, and everything downstream compounded it.

Time-travel replay lets you isolate exactly that step, change one thing, and see
what would have happened — without re-running expensive LLM calls for the steps
that already worked correctly.

Happy to answer any questions about the architecture or the time-travel replay
engine specifically.

---

## Launch Checklist

Before posting:
- [ ] Make sure swarm-trace.vercel.app is live and loads fast
- [ ] Make sure the backend on Render is awake (visit /health first)
- [ ] Run the swarm once to generate fresh traces for the demo
- [ ] Have the GitHub README open — people will click straight to it
- [ ] Post Tuesday–Thursday between 9am–12pm ET for best HN visibility
- [ ] For ProductHunt — schedule the launch at 12:01am PT so you have a full day

After posting:
- [ ] Reply to every comment within the first 2 hours
- [ ] Share on LinkedIn and Twitter/X
- [ ] Ask friends to upvote (ProductHunt allows this)