/**
 * components/SpanNode.jsx — Custom React Flow node for a single span.
 *
 * Each node shows:
 *   - Agent name + span type badge
 *   - Latency in ms
 *   - Token usage (prompt + completion)
 *   - Status colour (green = success, red = loop detected, yellow = running)
 *
 * Why custom nodes?
 *   React Flow's default nodes are plain boxes. Custom nodes let us show
 *   agent-specific data (tokens, latency) directly on the graph — which
 *   is exactly what an observability tool needs.
 */

import { Handle, Position } from '@xyflow/react'

const AGENT_COLORS = {
  orchestrator: '#3b82f6',  // blue
  researcher:   '#8b5cf6',  // purple
  writer:       '#10b981',  // green
  critic:       '#f59e0b',  // yellow
}

const TYPE_LABELS = {
  AGENT_REASONING: 'reasoning',
  TOOL_EXECUTION:  'tool',
  HANDOFF:         'handoff',
}

export default function SpanNode({ data }) {
  const color = AGENT_COLORS[data.agent_name] || '#6b7280'
  const typeLabel = TYPE_LABELS[data.span_type] || data.span_type?.toLowerCase()
  const tokens = data.token_usage
    ? (data.token_usage.prompt_tokens || 0) + (data.token_usage.completion_tokens || 0)
    : null

  return (
    <div
      style={{ borderColor: color }}
      className="rounded-xl border-2 bg-[#1a2235] min-w-[180px] max-w-[220px] shadow-xl"
    >
      <Handle type="target" position={Position.Top} style={{ background: color, border: 'none' }} />

      {/* Header */}
      <div
        style={{ backgroundColor: color + '22', borderBottomColor: color + '44' }}
        className="px-3 py-2 border-b rounded-t-xl flex items-center justify-between"
      >
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color }}>
          {data.agent_name}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-white/60">
          {typeLabel}
        </span>
      </div>

      {/* Body */}
      <div className="px-3 py-2 space-y-1">
        {data.latency_ms != null && (
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-white/40">latency</span>
            <span className="text-[11px] font-mono text-white/80">{data.latency_ms}ms</span>
          </div>
        )}
        {data.estimated_cost_usd != null && (
          <div className="flex justify-between items-center">
            <span className="text-[11px] text-white/40">cost</span>
            <span className="text-[11px] font-mono text-green-400">
              ${Number(data.estimated_cost_usd).toFixed(6)}
            </span>
          </div>
        )}
        {data.span_type === 'HANDOFF' && (
          <div className="text-[11px] text-white/40 text-center pt-1">
            {data.input_payload?.sender} → {data.input_payload?.receiver}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: color, border: 'none' }} />
    </div>
  )
}
