/**
 * pages/TraceDiff.jsx — Side-by-side diff of original vs forked trace.
 *
 * Fix: if the "original" trace has no spans (it's itself a fork),
 * walk up to its parent trace automatically so the diff is meaningful.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTrace } from '../api/client'

function flattenSpans(spans, result = []) {
  for (const span of spans) {
    result.push(span)
    if (span.children?.length) flattenSpans(span.children, result)
  }
  return result
}

function DeltaBadge({ original, forked, unit = 'ms' }) {
  if (original == null || forked == null) return <span className="text-white/30">—</span>
  const delta = forked - original
  const pct = original > 0 ? ((delta / original) * 100).toFixed(1) : 0
  const color = delta > 0 ? 'text-red-400' : delta < 0 ? 'text-green-400' : 'text-white/40'
  const sign = delta > 0 ? '+' : ''
  return (
    <span className={`font-mono text-xs ${color}`}>
      {sign}{delta}{unit} ({sign}{pct}%)
    </span>
  )
}

function SpanRow({ span, counterpart }) {
  const hasChange = counterpart &&
    JSON.stringify(span.output_payload) !== JSON.stringify(counterpart.output_payload)

  return (
    <div className={`rounded-lg border p-3 space-y-1.5 ${hasChange ? 'border-yellow-500/40 bg-yellow-500/5' : 'border-[#2a3a55] bg-[#1a2235]'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold uppercase tracking-wider ${
            { orchestrator: 'text-blue-400', researcher: 'text-purple-400',
              writer: 'text-green-400', critic: 'text-yellow-400' }[span.agent_name] || 'text-white/60'
          }`}>
            {span.agent_name}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-white/40">
            {span.span_type?.toLowerCase()}
          </span>
          {hasChange && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">
              changed
            </span>
          )}
        </div>
        <span className="font-mono text-xs text-white/40">{span.latency_ms}ms</span>
      </div>

      {span.estimated_cost_usd != null && (
        <div className="text-[11px] text-white/40 font-mono">
          cost: <span className="text-green-400">${Number(span.estimated_cost_usd).toFixed(6)}</span>
        </div>
      )}

      {hasChange && (
        <div className="mt-2 space-y-1">
          <p className="text-[10px] text-white/30 uppercase tracking-wider">Output</p>
          <pre className="text-[10px] bg-[#0a0e1a] rounded p-2 text-white/60 overflow-auto max-h-24 border border-[#2a3a55]">
            {JSON.stringify(span.output_payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function TraceDiff() {
  const { originalId, forkedId } = useParams()
  const navigate = useNavigate()

  const [original, setOriginal] = useState(null)
  const [forked, setForked]     = useState(null)
  const [resolvedOriginalId, setResolvedOriginalId] = useState(originalId)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const [origRes, forkRes] = await Promise.all([
          getTrace(originalId),
          getTrace(forkedId),
        ])

        let origData = origRes.data

        // If original has no spans but has a parent, walk up to parent
        if (
          origData.span_tree.length === 0 &&
          origData.trace.parent_trace_id
        ) {
          const parentRes = await getTrace(origData.trace.parent_trace_id)
          origData = parentRes.data
          setResolvedOriginalId(origData.trace.trace_id)
        }

        setOriginal(origData)
        setForked(forkRes.data)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [originalId, forkedId])

  if (loading) return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center text-white/30">
      Loading diff...
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center text-red-400 text-sm">
      {error}
    </div>
  )

  const origSpans = flattenSpans(original.span_tree)
  const forkSpans = flattenSpans(forked.span_tree)
  const matchSpan = (spans, agentName) => spans.find(s => s.agent_name === agentName)

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white">
      {/* Header */}
      <div className="border-b border-[#2a3a55] px-8 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-white/40 hover:text-white text-sm transition-colors">
          ← Back
        </button>
        <div className="h-4 w-px bg-[#2a3a55]" />
        <h1 className="text-sm font-bold">🔀 Trace Diff</h1>
        <div className="h-4 w-px bg-[#2a3a55]" />
        <span className="text-xs text-white/40">Original vs Forked</span>
      </div>

      {/* Summary bar */}
      <div className="px-8 py-4 border-b border-[#2a3a55] grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg bg-[#1a2235] border border-[#2a3a55] p-3">
          <p className="text-xs text-white/40 mb-1">Latency Delta</p>
          <DeltaBadge original={original.trace.total_latency_ms} forked={forked.trace.total_latency_ms} unit="ms" />
        </div>
        <div className="rounded-lg bg-[#1a2235] border border-[#2a3a55] p-3">
          <p className="text-xs text-white/40 mb-1">Cost Delta</p>
          <DeltaBadge
            original={Number(original.trace.total_cost_usd) * 1_000_000}
            forked={Number(forked.trace.total_cost_usd) * 1_000_000}
            unit="μ$"
          />
        </div>
        <div className="rounded-lg bg-[#1a2235] border border-[#2a3a55] p-3">
          <p className="text-xs text-white/40 mb-1">Original Spans</p>
          <span className="font-mono text-xs text-white/80">{origSpans.length}</span>
        </div>
        <div className="rounded-lg bg-[#1a2235] border border-[#2a3a55] p-3">
          <p className="text-xs text-white/40 mb-1">Forked Spans</p>
          <span className="font-mono text-xs text-white/80">{forkSpans.length}</span>
        </div>
      </div>

      {/* Side by side */}
      <div className="px-8 py-6 grid grid-cols-2 gap-6">
        {/* Original */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold text-white/60 uppercase tracking-wider">Original</h2>
            <span className="font-mono text-xs text-blue-400">{resolvedOriginalId.slice(0, 12)}...</span>
            <span className="text-xs text-white/40 font-mono">{original.trace.total_latency_ms}ms</span>
            {original.trace.total_cost_usd && (
              <span className="text-xs text-green-400 font-mono">${Number(original.trace.total_cost_usd).toFixed(6)}</span>
            )}
          </div>
          <div className="space-y-2">
            {origSpans.length === 0 ? (
              <div className="text-white/30 text-sm text-center py-10">
                No spans recorded for this trace.
              </div>
            ) : (
              origSpans.map(span => (
                <SpanRow
                  key={span.span_id}
                  span={span}
                  counterpart={matchSpan(forkSpans, span.agent_name)}
                />
              ))
            )}
          </div>
        </div>

        {/* Forked */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold text-white/60 uppercase tracking-wider">Forked</h2>
            <span className="font-mono text-xs text-purple-400">{forkedId.slice(0, 12)}...</span>
            <span className="text-xs text-white/40 font-mono">{forked.trace.total_latency_ms}ms</span>
            {forked.trace.total_cost_usd && (
              <span className="text-xs text-green-400 font-mono">${Number(forked.trace.total_cost_usd).toFixed(6)}</span>
            )}
          </div>
          <div className="space-y-2">
            {forkSpans.length === 0 ? (
              <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-6 text-center space-y-2">
                <p className="text-yellow-400 text-sm font-semibold">⏳ Replay in progress</p>
                <p className="text-white/40 text-xs">
                  The forked pipeline is re-running downstream agents. 
                  Refresh in a few seconds to see the results.
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="mt-2 px-4 py-1.5 rounded-lg bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 text-xs font-semibold transition-colors"
                >
                  Refresh
                </button>
              </div>
            ) : (
              forkSpans.map(span => (
                <SpanRow
                  key={span.span_id}
                  span={span}
                  counterpart={matchSpan(origSpans, span.agent_name)}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}