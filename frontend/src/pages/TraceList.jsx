/**
 * pages/TraceList.jsx — Home page showing all swarm runs.
 * A3: Added search by trace ID + filter by status and agent.
 */

import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTraces } from '../api/client'

const STATUS_STYLES = {
  SUCCESS:        'bg-green-500/20 text-green-400 border-green-500/30',
  RUNNING:        'bg-blue-500/20 text-blue-400 border-blue-500/30',
  FAILED:         'bg-red-500/20 text-red-400 border-red-500/30',
  LOOP_DETECTED:  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
}

function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${STATUS_STYLES[status] || 'bg-white/10 text-white/40'}`}>
      {status}
    </span>
  )
}

export default function TraceList() {
  const [traces, setTraces]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  const [search, setSearch]         = useState('')
  const [statusFilter, setStatus]   = useState('')
  const [agentFilter, setAgent]     = useState('')

  const navigate = useNavigate()

  const fetchTraces = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams()
    if (search)       params.append('search', search)
    if (statusFilter) params.append('status', statusFilter)
    if (agentFilter)  params.append('root_agent', agentFilter)

    getTraces(params)
      .then(r => setTraces(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [search, statusFilter, agentFilter])

  useEffect(() => { fetchTraces() }, [fetchTraces])

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white">
      <div className="border-b border-[#2a3a55] px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">🔭 SwarmTrace</h1>
          <p className="text-xs text-white/40 mt-0.5">Multi-agent observability platform</p>
        </div>
        <span className="text-xs text-white/30 font-mono">
          {traces.length} trace{traces.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="px-8 py-6">

        <div className="flex flex-wrap gap-3 mb-5">
          <input
            type="text"
            placeholder="Search trace ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-[#1a2235] border border-[#2a3a55] rounded-lg px-4 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-blue-500 w-64"
          />

          <select
            value={statusFilter}
            onChange={e => setStatus(e.target.value)}
            className="bg-[#1a2235] border border-[#2a3a55] rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">SUCCESS</option>
            <option value="RUNNING">RUNNING</option>
            <option value="FAILED">FAILED</option>
            <option value="LOOP_DETECTED">LOOP_DETECTED</option>
          </select>

          <select
            value={agentFilter}
            onChange={e => setAgent(e.target.value)}
            className="bg-[#1a2235] border border-[#2a3a55] rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">All Agents</option>
            <option value="orchestrator">Orchestrator</option>
            <option value="researcher">Researcher</option>
            <option value="writer">Writer</option>
            <option value="critic">Critic</option>
          </select>

          {(search || statusFilter || agentFilter) && (
            <button
              onClick={() => { setSearch(''); setStatus(''); setAgent('') }}
              className="px-4 py-2 text-sm text-white/40 hover:text-white border border-[#2a3a55] rounded-lg transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Agent Runs</h2>

        {loading && <div className="text-center py-20 text-white/30">Loading traces...</div>}

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-400 text-sm">
            Failed to load traces: {error}. Is the backend running?
          </div>
        )}

        {!loading && !error && traces.length === 0 && (
          <div className="text-center py-20 text-white/30">No traces found. Try clearing filters or run the swarm.</div>
        )}

        {!loading && traces.length > 0 && (
          <div className="rounded-xl border border-[#2a3a55] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#2a3a55] bg-[#111827]">
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Trace ID</th>
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Root Agent</th>
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Status</th>
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Latency</th>
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Cost</th>
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Parent</th>
                  <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider font-semibold">Created</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((t, i) => (
                  <tr
                    key={t.trace_id}
                    onClick={() => navigate(`/trace/${t.trace_id}`)}
                    className={`border-b border-[#2a3a55] hover:bg-[#1a2235] cursor-pointer transition-colors ${i % 2 === 0 ? 'bg-[#0a0e1a]' : 'bg-[#0d1220]'}`}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-blue-400">{t.trace_id.slice(0, 12)}...</td>
                    <td className="px-4 py-3 text-white/70 capitalize">{t.root_agent}</td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-white/60">{t.total_latency_ms ? `${t.total_latency_ms}ms` : '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-green-400">{t.total_cost_usd ? `$${Number(t.total_cost_usd).toFixed(6)}` : '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-purple-400">{t.parent_trace_id ? `${t.parent_trace_id.slice(0, 8)}...` : '—'}</td>
                    <td className="px-4 py-3 text-xs text-white/40">{new Date(t.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}