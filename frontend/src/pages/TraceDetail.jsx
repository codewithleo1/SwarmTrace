/**
 * pages/TraceDetail.jsx — Interactive span tree + replay panel.
 *
 * Fetches GET /trace/{id} and shows:
 *   - Trace metadata (status, latency, parent trace)
 *   - Interactive span tree graph (SpanTree)
 *   - Clicking a span opens the ReplayPanel on the right
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTrace } from '../api/client'
import SpanTree from '../components/SpanTree'
import ReplayPanel from '../components/ReplayPanel'

const STATUS_STYLES = {
  SUCCESS:        'bg-green-500/20 text-green-400 border-green-500/30',
  RUNNING:        'bg-blue-500/20 text-blue-400 border-blue-500/30',
  FAILED:         'bg-red-500/20 text-red-400 border-red-500/30',
  LOOP_DETECTED:  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
}

export default function TraceDetail() {
  const { traceId } = useParams()
  const navigate = useNavigate()
  const [data, setData]           = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [selectedSpan, setSelectedSpan] = useState(null)

  useEffect(() => {
    getTrace(traceId)
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [traceId])

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
        {trace.total_latency_ms && (
          <span className="text-xs text-white/40 font-mono ml-auto">
            {trace.total_latency_ms}ms total
          </span>
        )}
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

      <div className="px-8 py-6 grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Span Tree — takes 2/3 width on large screens */}
        <div className="xl:col-span-2 space-y-3">
          <h2 className="text-xs font-semibold text-white/40 uppercase tracking-wider">
            Execution Tree — click any node to replay from that step
          </h2>
          {span_tree.length === 0 ? (
            <div className="text-white/30 text-sm py-10 text-center">No spans recorded.</div>
          ) : (
            <SpanTree spans={span_tree} onNodeClick={setSelectedSpan} />
          )}

          {/* Legend */}
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

        {/* Replay Panel — takes 1/3 width */}
        <div>
          {selectedSpan ? (
            <ReplayPanel
              span={selectedSpan}
              traceId={traceId}
              onReplayDone={handleReplayDone}
            />
          ) : (
            <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-6 text-center">
              <p className="text-2xl mb-2">👆</p>
              <p className="text-sm text-white/40">Click any node in the graph to inspect it and fork execution from that step</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
