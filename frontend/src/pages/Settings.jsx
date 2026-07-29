/**
 * pages/Settings.jsx — User profile + API key management.
 *
 * Shows:
 *   - Current user info
 *   - List of API keys with preview + last used date
 *   - Generate new key button
 *   - Revoke key button
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMe, getApiKeys, createApiKey, revokeApiKey } from '../api/client'

export default function Settings() {
  const [user, setUser]         = useState(null)
  const [keys, setKeys]         = useState([])
  const [newKeyName, setName]   = useState('')
  const [newKey, setNewKey]     = useState(null)   // shown once after creation
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    getMe().then(r => setUser(r.data))
    getApiKeys().then(r => setKeys(r.data))
  }, [])

  async function handleCreate() {
    if (!newKeyName.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await createApiKey({ name: newKeyName.trim() })
      setNewKey(res.data)
      setName('')
      const updated = await getApiKeys()
      setKeys(updated.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRevoke(keyId) {
    await revokeApiKey(keyId)
    const updated = await getApiKeys()
    setKeys(updated.data)
  }

  function handleLogout() {
    localStorage.removeItem('swt_token')
    localStorage.removeItem('swt_user')
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white">
      {/* Header */}
      <div className="border-b border-[#2a3a55] px-8 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-white/40 hover:text-white text-sm transition-colors">
          ← Back
        </button>
        <div className="h-4 w-px bg-[#2a3a55]" />
        <h1 className="text-sm font-bold">⚙️ Settings</h1>
        <button
          onClick={handleLogout}
          className="ml-auto text-xs text-red-400 hover:text-red-300 transition-colors"
        >
          Sign Out
        </button>
      </div>

      <div className="px-8 py-6 max-w-2xl space-y-8">

        {/* Profile */}
        {user && (
          <div className="rounded-xl border border-[#2a3a55] bg-[#1a2235] p-5 space-y-3">
            <h2 className="text-xs font-semibold text-white/40 uppercase tracking-wider">Profile</h2>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-blue-600/30 flex items-center justify-center text-blue-400 font-bold text-lg">
                {user.name?.[0]?.toUpperCase()}
              </div>
              <div>
                <p className="font-semibold text-white">{user.name}</p>
                <p className="text-sm text-white/40">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        {/* API Keys */}
        <div className="space-y-4">
          <h2 className="text-xs font-semibold text-white/40 uppercase tracking-wider">API Keys</h2>
          <p className="text-xs text-white/40">
            Use API keys to authenticate agent systems (AEGIS, ACSA, etc.) without a login flow.
            Add <code className="bg-white/10 px-1 rounded">X-API-Key: swt_...</code> to your agent's headers.
          </p>

          {/* New key shown once */}
          {newKey && (
            <div className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 space-y-2">
              <p className="text-xs text-green-400 font-semibold">✅ API Key created — copy it now, it won't be shown again</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs font-mono bg-[#0a0e1a] rounded px-3 py-2 text-green-400 border border-green-500/20 break-all">
                  {newKey.key_value}
                </code>
                <button
                  onClick={() => navigator.clipboard.writeText(newKey.key_value)}
                  className="text-xs px-3 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white transition-colors whitespace-nowrap"
                >
                  Copy
                </button>
              </div>
              <button onClick={() => setNewKey(null)} className="text-xs text-white/30 hover:text-white/60">
                Dismiss
              </button>
            </div>
          )}

          {/* Generate new key */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Key name (e.g. AEGIS production)"
              value={newKeyName}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
              className="flex-1 bg-[#1a2235] border border-[#2a3a55] rounded-lg px-4 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleCreate}
              disabled={loading || !newKeyName.trim()}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors whitespace-nowrap"
            >
              {loading ? '...' : '+ Generate Key'}
            </button>
          </div>

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          {/* Keys list */}
          {keys.length === 0 ? (
            <div className="text-center py-8 text-white/30 text-sm">
              No API keys yet. Generate one above.
            </div>
          ) : (
            <div className="rounded-xl border border-[#2a3a55] overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#2a3a55] bg-[#111827]">
                    <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider">Name</th>
                    <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider">Key</th>
                    <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider">Last Used</th>
                    <th className="text-left px-4 py-3 text-xs text-white/40 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((k, i) => (
                    <tr key={k.key_id} className={`border-b border-[#2a3a55] ${i % 2 === 0 ? 'bg-[#0a0e1a]' : 'bg-[#0d1220]'}`}>
                      <td className="px-4 py-3 text-white/80">{k.name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-white/40">{k.key_preview}</td>
                      <td className="px-4 py-3 text-xs text-white/40">
                        {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${
                          k.is_active
                            ? 'bg-green-500/20 text-green-400 border-green-500/30'
                            : 'bg-white/5 text-white/30 border-white/10'
                        }`}>
                          {k.is_active ? 'Active' : 'Revoked'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {k.is_active && (
                          <button
                            onClick={() => handleRevoke(k.key_id)}
                            className="text-xs text-red-400 hover:text-red-300 transition-colors"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}