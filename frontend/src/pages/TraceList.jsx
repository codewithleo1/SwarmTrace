/**
 * pages/TraceList.jsx — Home page showing all swarm runs.
 * A3: Added search by trace ID + filter by status and agent.
 * B2: Added project selector — traces are scoped to active project.
 * B5: Added dashboard metrics cards + daily trace chart.
 */

import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTraces, getProjects, getMetrics } from '../api/client'

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

function MetricCard({ label, value, sub, color = 'text-white' }) {
  return (
    <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-4 space-y-1">
      <p className="text-xs text-white/40 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-bold font-mono ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-white/30">{sub}</p>}
    </div>
  )
}

function MiniBarChart({ daily }) {
  if (!daily || daily.length === 0) return (
    <div className="flex items-center justify-center h-full text-white/20 text-xs">No data</div>
  )
  const max = Math.max(...daily.map(d => d.count), 1)

  return (
    <div className="flex items-end gap-1.5 h-16 w-full">
      {daily.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div
            className="w-full rounded-sm bg-blue-500/60 hover:bg-blue-400/80 transition-colors"
            style={{ height: `${Math.max((d.count / max) * 100, 8)}%` }}
            title={`${d.day}: ${d.count} traces`}
          />
          <span className="text-[9px] text-white/20 rotate-45 origin-left">
            {new Date(d.day).toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' })}
          </span>
        </div>
      ))}
    </div>
  )
}

function Dashboard({ metrics }) {
  if (!metrics) return null
  const { summary, daily } = metrics

  return (
    <div className="mb-6 space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Total Traces"
          value={summary.total_traces}
          sub={`${summary.running ?? 0} running`}
        />
        <MetricCard
          label="Success Rate"
          value={summary.success_rate != null ? `${summary.success_rate}%` : '—'}
          sub={`${summary.failed ?? 0} failed · ${summary.loops ?? 0} loops`}
          color={
            summary.success_rate >= 90 ? 'text-green-400' :
            summary.success_rate >= 70 ? 'text-yellow-400' :
            'text-red-400'
          }
        />
        <MetricCard
          label="Avg Latency"
          value={summary.avg_latency_ms ? `${Number(summary.avg_latency_ms).toLocaleString()}ms` : '—'}
          sub="across all traces"
        />
        <MetricCard
          label="Total Cost"
          value={summary.total_cost_usd ? `$${Number(summary.total_cost_usd).toFixed(4)}` : '$0'}
          sub="estimated spend"
          color="text-green-400"
        />
      </div>

      {/* Daily chart */}
      <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-4">
        <p className="text-xs text-white/40 uppercase tracking-wider mb-3">Traces — Last 7 Days</p>
        <MiniBarChart daily={daily} />
      </div>
    </div>
  )
}

export default function TraceList() {
  const [traces, setTraces]         = useState([])
  const [projects, setProjects]     = useState([])
  const [metrics, setMetrics]       = useState(null)
  const [activeProject, setActive]  = useState(() => localStorage.getItem('swt_project') || '')
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)

  const [search, setSearch]         = useState('')
  const [statusFilter, setStatus]   = useState('')
  const [agentFilter, setAgent]     = useState('')

  const navigate = useNavigate()

  useEffect(() => {
    getProjects().then(r => {
      setProjects(r.data)
      if (!activeProject && r.data.length > 0) {
        setActive(r.data[0].project_id)
        localStorage.setItem('swt_project', r.data[0].project_id)
      }
    })
  }, [])

  const fetchTraces = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = {}
    if (activeProject) params.project_id = activeProject
    if (search)        params.search     = search
    if (statusFilter)  params.status     = statusFilter
    if (agentFilter)   params.root_agent = agentFilter

    getTraces(params)
      .then(r => setTraces(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [activeProject, search, statusFilter, agentFilter])

  const fetchMetrics = useCallback(() => {
    getMetrics(activeProject || null)
      .then(r => setMetrics(r.data))
      .catch(() => {})
  }, [activeProject])

  useEffect(() => { fetchTraces() }, [fetchTraces])
  useEffect(() => { fetchMetrics() }, [fetchMetrics])

  function handleProjectChange(projectId) {
    setActive(projectId)
    localStorage.setItem('swt_project', projectId)
  }

  const activeProjectName = projects.find(p => p.project_id === activeProject)?.name || 'All Projects'

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white">
      <div className="border-b border-[#2a3a55] px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">🔭 SwarmTrace</h1>
          <p className="text-xs text-white/40 mt-0.5">Multi-agent observability platform</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={activeProject}
            onChange={e => handleProjectChange(e.target.value)}
            className="bg-[#1a2235] border border-[#2a3a55] rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">All Projects</option>
            {projects.map(p => (
              <option key={p.project_id} value={p.project_id}>
                {p.name} ({p.trace_count})
              </option>
            ))}
          </select>
          <span className="text-xs text-white/30 font-mono">
            {traces.length} trace{traces.length !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => navigate('/settings')}
            className="text-xs text-white/40 hover:text-white transition-colors"
          >
            ⚙️ Settings
          </button>
        </div>
      </div>

      <div className="px-8 py-6">

        {/* Dashboard */}
        <Dashboard metrics={metrics} />

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

        <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">
          {activeProject ? `${activeProjectName} — Agent Runs` : 'All Agent Runs'}
        </h2>

        {loading && <div className="text-center py-20 text-white/30">Loading traces...</div>}

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-400 text-sm">
            Failed to load traces: {error}. Is the backend running?
          </div>
        )}

        {!loading && !error && traces.length === 0 && (
          <div className="text-center py-20 text-white/30">
            No traces found.
            {activeProject ? ' Run your agent with this project\'s API key.' : ' Try clearing filters or run the swarm.'}
          </div>
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