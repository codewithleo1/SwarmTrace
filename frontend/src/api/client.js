/**
 * api/client.js — All calls to the FastAPI backend.
 * B1: Added auth headers, login, register, API key endpoints.
 */

import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || '/api'

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

// Auth
export const register  = (body) => http.post('/auth/register', body)
export const login     = (body) => http.post('/auth/login', body)
export const getMe     = ()     => http.get('/auth/me')

// Traces
export const getTraces  = (params) => http.get('/traces', { params })
export const getTrace   = (id)     => http.get(`/trace/${id}`)
export const postReplay = (body)   => http.post('/replay', body)

// API Keys
export const getApiKeys    = ()       => http.get('/api-keys')
export const createApiKey  = (body)   => http.post('/api-keys', body)
export const revokeApiKey  = (id)     => http.delete(`/api-keys/${id}`)