"""
swarmtrace — Instrumentation SDK for SwarmTrace.

Quickstart:
    pip install swarmtrace

    from swarmtrace import SwarmTracer

    tracer = SwarmTracer(
        api_key="swt_your_key_here",
        base_url="http://localhost:8000",  # or your Render URL
    )

    # Context manager (sync)
    with tracer.span("my_agent", input_payload={"query": "hello"}) as span:
        result = my_agent("hello")
        span.set_output({"result": result})
        span.set_token_usage(prompt_tokens=120, completion_tokens=45)

    # Context manager (async)
    async with tracer.async_span("my_agent") as span:
        result = await my_agent_async("hello")
        span.set_output({"result": result})

    # Decorator
    @tracer.trace("my_agent")
    def my_agent(query: str) -> str:
        return call_llm(query)
"""

from swarmtrace.tracer import Span, SwarmTracer

__all__ = ["Span", "SwarmTracer"]
__version__ = "0.1.0"