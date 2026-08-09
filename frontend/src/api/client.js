/**
 * api/client.js — All calls to the FastAPI backend.
 * B1: Added auth headers, login, register, API key endpoints.
 * B2: Added project endpoints. getTraces now accepts project_id param.
 * C4: Added WebSocket factory functions for live streaming.
 */

import axios from 'axios'

const BASE    = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_BASE = BASE.replace(/^http/, 'ws')   // http→ws, https→wss automatically

const http = axios.create({ baseURL: BASE })

// Attach JWT to every request if available
http.interceptors.request.use(config => {
  const token = localStorage.getItem('swt_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401
http.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('swt_token')
      localStorage.removeItem('swt_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const register = (body) => http.post('/auth/register', body)
export const login    = (body) => http.post('/auth/login', body)
export const getMe    = ()     => http.get('/auth/me')

// ── Projects ──────────────────────────────────────────────────────────────────
export const getProjects   = ()     => http.get('/projects')
export const createProject = (body) => http.post('/projects', body)
export const deleteProject = (id)   => http.delete(`/projects/${id}`)

// ── Traces ────────────────────────────────────────────────────────────────────
export const getTraces  = (params) => http.get('/traces', { params })
export const getTrace   = (id)     => http.get(`/trace/${id}`)
export const postReplay = (body)   => http.post('/replay', body)

// ── API Keys ──────────────────────────────────────────────────────────────────
export const getApiKeys   = ()     => http.get('/api-keys')
export const createApiKey = (body) => http.post('/api-keys', body)
export const revokeApiKey = (id)   => http.delete(`/api-keys/${id}`)

// ── Evaluations ───────────────────────────────────────────────────────────────
export const evaluateTrace  = (traceId) => http.post(`/evaluate/${traceId}`)
export const getEvaluations = (traceId) => http.get(`/evaluations/${traceId}`)

// ── Alerts ────────────────────────────────────────────────────────────────────
export const getAlertConfig    = (projectId) => http.get(`/alerts/${projectId}`)
export const upsertAlertConfig = (body)      => http.post('/alerts', body)
export const deleteAlertConfig = (projectId) => http.delete(`/alerts/${projectId}`)

// ── Metrics ───────────────────────────────────────────────────────────────────
export const getMetrics = (projectId) =>
  http.get('/metrics', { params: projectId ? { project_id: projectId } : {} })

// ── WebSockets (C4) ───────────────────────────────────────────────────────────

/**
 * createTraceSocket — connects to /ws/traces
 * Called by TraceList to get live "a trace was created/updated" notifications.
 *
 * Usage:
 *   const ws = createTraceSocket(({ trace_id, status }) => refetch())
 *   // later:
 *   ws.close()
 *
 * @param {function} onMessage  — called with parsed JSON payload on each message
 * @returns {WebSocket}
 */
export function createTraceSocket(onMessage) {
  const ws = new WebSocket(`${WS_BASE}/ws/traces`)

  ws.onopen    = () => console.log('[WS] trace list connected')
  ws.onclose   = () => console.log('[WS] trace list disconnected')
  ws.onerror   = (e) => console.warn('[WS] trace list error', e)
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data))
    } catch {
      // ignore malformed frames
    }
  }

  return ws
}

/**
 * createSpanSocket — connects to /ws/trace/{traceId}
 * Called by TraceDetail to receive new spans live as the swarm runs.
 *
 * Usage:
 *   const ws = createSpanSocket(traceId, (span) => addSpanToTree(span))
 *   // later:
 *   ws.close()
 *
 * @param {string}   traceId    — the trace being watched
 * @param {function} onSpan     — called with the span object on each message
 * @returns {WebSocket}
 */
export function createSpanSocket(traceId, onSpan) {
  const ws = new WebSocket(`${WS_BASE}/ws/trace/${traceId}`)

  ws.onopen    = () => console.log(`[WS] span stream connected for ${traceId}`)
  ws.onclose   = () => console.log(`[WS] span stream disconnected for ${traceId}`)
  ws.onerror   = (e) => console.warn('[WS] span stream error', e)
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'NEW_SPAN') onSpan(msg.span)
    } catch {
      // ignore malformed frames
    }
  }

  return ws
}