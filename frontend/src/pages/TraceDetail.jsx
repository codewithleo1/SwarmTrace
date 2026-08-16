/**
 * pages/TraceDetail.jsx — Interactive span tree + replay panel.
 * B3: Added "Evaluate Trace" button + evaluation score badges per span.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTrace, evaluateTrace, getEvaluations } from '../api/client'
import SpanTree from '../components/SpanTree'
import ReplayPanel from '../components/ReplayPanel'

const STATUS_STYLES = {
  SUCCESS:        'bg-green-500/20 text-green-400 border-green-500/30',
  RUNNING:        'bg-blue-500/20 text-blue-400 border-blue-500/30',
  FAILED:         'bg-red-500/20 text-red-400 border-red-500/30',
  LOOP_DETECTED:  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
}

function ScoreBadge({ label, score }) {
  const color = score >= 8 ? 'text-green-400' : score >= 6 ? 'text-yellow-400' : 'text-red-400'
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-white/40 capitalize">{label}</span>
      <span className={`text-xs font-mono font-bold ${color}`}>{score?.toFixed(1)}/10</span>
    </div>
  )
}

function EvalPanel({ eval: e }) {
  if (!e) return null
  const verdictStyle = e.verdict === 'PASS'
    ? 'bg-green-500/20 text-green-400 border-green-500/30'
    : 'bg-red-500/20 text-red-400 border-red-500/30'

  return (
    <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Judge Scores</h3>
        <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${verdictStyle}`}>
          {e.verdict}
        </span>
      </div>
      <ScoreBadge label="Relevance" score={e.relevance} />
      <ScoreBadge label="Reasoning" score={e.reasoning} />
      <ScoreBadge label="Quality"   score={e.quality} />
      <div className="border-t border-[#2a3a55] pt-2">
        <ScoreBadge label="Overall" score={e.overall} />
      </div>
      <p className="text-xs text-white/50 italic leading-relaxed">{e.feedback}</p>
      <p className="text-[10px] text-white/20">Judge: {e.judge_model}</p>
    </div>
  )
}

export default function TraceDetail() {
  const { traceId } = useParams()
  const navigate = useNavigate()
  const [data, setData]               = useState(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [selectedSpan, setSelectedSpan] = useState(null)
  const [evaluations, setEvaluations] = useState({})   // span_id → eval object
  const [evalLoading, setEvalLoading] = useState(false)
  const [evalDone, setEvalDone]       = useState(false)

  useEffect(() => {
    getTrace(traceId)
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))

    // Load any existing evaluations for this trace
    getEvaluations(traceId).then(r => {
      const map = {}
      r.data.forEach(e => { map[e.span_id] = e })
      setEvaluations(map)
      if (r.data.length > 0) setEvalDone(true)
    }).catch(() => {})
  }, [traceId])

  async function handleEvaluate() {
    setEvalLoading(true)
    try {
      await evaluateTrace(traceId)
      const r = await getEvaluations(traceId)
      const map = {}
      r.data.forEach(e => { map[e.span_id] = e })
      setEvaluations(map)
      setEvalDone(true)
    } catch (e) {
      console.error('Evaluation failed:', e)
    } finally {
      setEvalLoading(false)
    }
  }

  function handleReplayDone(forkedTraceId) {
    setTimeout(() => navigate(`/trace/${forkedTraceId}`), 1500)
  }

  if (loading) return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center text-white/30">
      Loading trace...
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center">
      <div className="text-red-400 text-sm">{error}</div>
    </div>
  )

  const { trace, span_tree } = data
  const selectedEval = selectedSpan ? evaluations[selectedSpan.span_id] : null

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white">
      {/* Header */}
      <div className="border-b border-[#2a3a55] px-8 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="text-white/40 hover:text-white text-sm transition-colors"
        >
          ← Back
        </button>
        <div className="h-4 w-px bg-[#2a3a55]" />
        <h1 className="text-sm font-bold tracking-tight">🔭 SwarmTrace</h1>
        <div className="h-4 w-px bg-[#2a3a55]" />
        <span className="font-mono text-xs text-blue-400">{traceId.slice(0, 16)}...</span>
        <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${STATUS_STYLES[trace.status] || ''}`}>
          {trace.status}
        </span>
        <div className="ml-auto flex items-center gap-3">
          {trace.total_latency_ms && (
            <span className="text-xs text-white/40 font-mono">{trace.total_latency_ms}ms</span>
          )}
          {trace.total_cost_usd && (
            <span className="text-xs text-green-400 font-mono">${Number(trace.total_cost_usd).toFixed(6)}</span>
          )}
          {/* Evaluate button */}
          <button
            onClick={handleEvaluate}
            disabled={evalLoading}
            className="text-xs px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold transition-colors"
          >
            {evalLoading ? '⏳ Evaluating...' : evalDone ? '✅ Re-evaluate' : '🧑‍⚖️ Evaluate Trace'}
          </button>
        </div>
      </div>

      {/* Parent trace banner */}
      {trace.parent_trace_id && (
        <div className="px-8 py-2 bg-purple-500/10 border-b border-purple-500/20 text-xs text-purple-400">
          🔀 Forked from trace{' '}
          <button
            onClick={() => navigate(`/trace/${trace.parent_trace_id}`)}
            className="underline hover:text-purple-300"
          >
            {trace.parent_trace_id.slice(0, 16)}...
          </button>
        </div>
      )}

      {/* Eval summary bar — shown after evaluation */}
      {evalDone && Object.keys(evaluations).length > 0 && (
        <div className="px-8 py-3 border-b border-[#2a3a55] flex items-center gap-6 bg-[#0d1220]">
          <span className="text-xs text-white/40 uppercase tracking-wider">Judge Summary</span>
          {Object.values(evaluations).map(e => (
            <div key={e.span_id} className="flex items-center gap-2">
              <span className="text-xs text-white/60 capitalize">{e.agent_name}</span>
              <span className={`text-xs font-mono font-bold ${
                e.overall >= 8 ? 'text-green-400' : e.overall >= 6 ? 'text-yellow-400' : 'text-red-400'
              }`}>{e.overall?.toFixed(1)}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${
                e.verdict === 'PASS'
                  ? 'bg-green-500/20 text-green-400 border-green-500/30'
                  : 'bg-red-500/20 text-red-400 border-red-500/30'
              }`}>{e.verdict}</span>
            </div>
          ))}
        </div>
      )}

      <div className="px-8 py-6 grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Span Tree */}
        <div className="xl:col-span-2 space-y-3">
          <h2 className="text-xs font-semibold text-white/40 uppercase tracking-wider">
            Execution Tree — click any node to inspect or replay
          </h2>
          {span_tree.length === 0 ? (
            <div className="text-white/30 text-sm py-10 text-center">No spans recorded.</div>
          ) : (
            <SpanTree spans={span_tree} onNodeClick={setSelectedSpan} />
          )}
          <div className="flex gap-4 flex-wrap">
            {[
              { name: 'orchestrator', color: '#3b82f6' },
              { name: 'researcher',   color: '#8b5cf6' },
              { name: 'writer',       color: '#10b981' },
              { name: 'critic',       color: '#f59e0b' },
            ].map(({ name, color }) => (
              <div key={name} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-xs text-white/40 capitalize">{name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel — ReplayPanel + EvalPanel */}
        <div className="space-y-4">
          {selectedSpan ? (
            <>
              <ReplayPanel
                span={selectedSpan}
                traceId={traceId}
                parentTraceId={trace.parent_trace_id}
                onReplayDone={handleReplayDone}
              />
              {selectedEval && <EvalPanel eval={selectedEval} />}
              {evalDone && !selectedEval && (
                <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-4 text-center">
                  <p className="text-xs text-white/30">No evaluation for this span type</p>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-6 text-center">
              <p className="text-2xl mb-2">👆</p>
              <p className="text-sm text-white/40">Click any node to inspect it and fork execution from that step</p>
              {!evalDone && (
                <button
                  onClick={handleEvaluate}
                  disabled={evalLoading}
                  className="mt-4 text-xs px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold transition-colors"
                >
                  {evalLoading ? '⏳ Evaluating...' : '🧑‍⚖️ Evaluate Trace'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}