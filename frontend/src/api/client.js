/**
 * api/client.js — All calls to the FastAPI backend go through here.
 *
 * Why proxy via /api?
 *   The Vite dev server proxies /api/* to http://127.0.0.1:8000/*
 *   so we never hit CORS issues during development.
 *   On Vercel, we set VITE_API_URL to the Render backend URL.
 */

import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || '/api'

const http = axios.create({ baseURL: BASE })

export const getTraces = () => http.get('/traces')
export const getTrace  = (id) => http.get(`/trace/${id}`)
export const postReplay = (body) => http.post('/replay', body)
