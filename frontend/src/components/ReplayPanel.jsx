/**
 * components/ReplayPanel.jsx — Time-travel replay UI.
 *
 * When a user clicks a span node, this panel slides in showing:
 *   - The span's input and output payloads
 *   - An editable textarea to override the output
 *   - A "Fork & Replay" button that calls POST /replay
 *
 * After replay, shows the forked trace_id with a link to view it.
 */

import { useState } from 'react'
import { postReplay } from '../api/client'

export default function ReplayPanel({ span, traceId, onReplayDone }) {
  const [overrideText, setOverrideText] = useState(
    JSON.stringify(span?.output_payload || {}, null, 2)
  )
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState(null)

  if (!span) return null

  const stepMap = { researcher: 1, writer: 2, critic: 3 }
  const stepNumber = stepMap[span.agent_name] ?? 1

  async function handleReplay() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      let overrides = {}
      try { overrides = JSON.parse(overrideText) } catch { overrides = { raw: overrideText } }

      const res = await postReplay({
        trace_id: traceId,
        step_number: stepNumber,
        overrides,
      })
      setResult(res.data)
      onReplayDone?.(res.data.forked_trace_id)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          ⏱ Time-Travel Replay
        </h3>
        <span className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-400 font-mono">
          {span.agent_name} · step {stepNumber}
        </span>
      </div>

      {/* Input payload (read-only) */}
      <div>
        <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Input (read-only)</p>
        <pre className="text-xs bg-[#0a0e1a] rounded-lg p-3 text-white/60 overflow-auto max-h-32 border border-[#2a3a55]">
          {JSON.stringify(span.input_payload, null, 2)}
        </pre>
      </div>

      {/* Output override (editable) */}
      <div>
        <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">
          Override Output — edit this, then fork
        </p>
        <textarea
          value={overrideText}
          onChange={(e) => setOverrideText(e.target.value)}
          rows={6}
          className="w-full text-xs font-mono bg-[#0a0e1a] rounded-lg p-3 text-green-400 border border-[#2a3a55] focus:border-blue-500 focus:outline-none resize-none"
        />
      </div>

      {/* Fork button */}
      <button
        onClick={handleReplay}
        disabled={loading}
        className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
      >
        {loading ? '⏳ Replaying...' : '🔀 Fork & Replay from this step'}
      </button>

      {/* Result */}
      {result && (
        <div className="rounded-lg bg-green-500/10 border border-green-500/30 p-3 space-y-1">
          <p className="text-xs text-green-400 font-semibold">✅ Fork created successfully</p>
          <p className="text-xs text-white/60 font-mono">
            New trace: <span className="text-green-400">{result.forked_trace_id}</span>
          </p>
          <p className="text-xs text-white/40">
            Forked from step {result.forked_from_step} of original trace.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3">
          <p className="text-xs text-red-400 font-semibold">❌ Replay failed</p>
          <p className="text-xs text-white/60 mt-1">{error}</p>
        </div>
      )}
    </div>
  )
}
