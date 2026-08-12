/**
 * pages/Login.jsx — Login + Register page.
 * Single page with tab switcher between login and register forms.
 * Added: "Try Demo" button for instant access without registration.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../api/client'

export default function Login() {
  const [tab, setTab]         = useState('login')
  const [email, setEmail]     = useState('')
  const [password, setPass]   = useState('')
  const [name, setName]       = useState('')
  const [error, setError]     = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      const res = tab === 'login'
        ? await login({ email, password })
        : await register({ email, password, name })

      localStorage.setItem('swt_token', res.data.access_token)
      localStorage.setItem('swt_user', JSON.stringify({
        user_id: res.data.user_id,
        email: res.data.email,
        name: res.data.name,
      }))
      navigate('/')
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDemo() {
    setLoading(true)
    setError(null)
    try {
      const res = await login({ email: 'demo@swarmtrace.dev', password: 'demo1234' })
      localStorage.setItem('swt_token', res.data.access_token)
      localStorage.setItem('swt_user', JSON.stringify({
        user_id: res.data.user_id,
        email: res.data.email,
        name: res.data.name,
      }))
      navigate('/')
    } catch (e) {
      setError('Demo login failed — please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">🔭 SwarmTrace</h1>
          <p className="text-sm text-white/40 mt-1">Multi-agent observability platform</p>
        </div>

        {/* Try Demo Banner */}
        <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-4 mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-blue-400">Try the live demo</p>
            <p className="text-xs text-white/40 mt-0.5">No sign-up needed — instant access</p>
          </div>
          <button
            onClick={handleDemo}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors whitespace-nowrap"
          >
            {loading ? '...' : 'Try Demo →'}
          </button>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-[#2a3a55] bg-[#1a2235] p-8 space-y-6">
          {/* Tab switcher */}
          <div className="flex rounded-lg bg-[#0a0e1a] p-1 gap-1">
            {['login', 'register'].map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(null) }}
                className={`flex-1 py-2 rounded-md text-sm font-semibold transition-colors capitalize ${
                  tab === t
                    ? 'bg-blue-600 text-white'
                    : 'text-white/40 hover:text-white'
                }`}
              >
                {t === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* Form */}
          <div className="space-y-4">
            {tab === 'register' && (
              <div>
                <label className="text-xs text-white/40 uppercase tracking-wider mb-1 block">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Your name"
                  className="w-full bg-[#0a0e1a] border border-[#2a3a55] rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-blue-500"
                />
              </div>
            )}

            <div>
              <label className="text-xs text-white/40 uppercase tracking-wider mb-1 block">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-[#0a0e1a] border border-[#2a3a55] rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-xs text-white/40 uppercase tracking-wider mb-1 block">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPass(e.target.value)}
                placeholder="••••••••"
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                className="w-full bg-[#0a0e1a] border border-[#2a3a55] rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-xs text-red-400">
              {error}
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold text-sm transition-colors"
          >
            {loading ? '...' : tab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </div>
      </div>
    </div>
  )
}