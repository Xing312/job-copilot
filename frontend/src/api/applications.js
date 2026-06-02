import { getToken, clearToken } from '../auth'
import {
  isDemoMode,
  getDemoApps, addDemoApp, updateDemoApp, updateDemoStatus, deleteDemoApp,
  toggleDemoPin, calcDemoStats,
} from '../demo'

const BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000') + '/api'

function authHeaders() {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function request(url, options = {}) {
  const res = await fetch(url, { ...options, headers: authHeaders() })
  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Session expired')
  }
  return res
}

export async function login(password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!res.ok) throw new Error('Invalid password')
  return res.json()
}

export async function getApplications() {
  if (isDemoMode()) return getDemoApps()
  const res = await request(`${BASE}/applications`)
  if (!res.ok) throw new Error('Failed to fetch applications')
  return res.json()
}

export async function createApplication(data) {
  if (isDemoMode()) return addDemoApp(data)
  const res = await request(`${BASE}/applications`, { method: 'POST', body: JSON.stringify(data) })
  if (!res.ok) throw new Error('Failed to create application')
  return res.json()
}

export async function getApplication(id) {
  if (isDemoMode()) return getDemoApps().find((a) => a.id === Number(id)) ?? null
  const res = await request(`${BASE}/applications/${id}`)
  if (!res.ok) throw new Error('Application not found')
  return res.json()
}

export async function updateStatus(id, status) {
  if (isDemoMode()) return updateDemoStatus(id, status)
  const res = await request(`${BASE}/applications/${id}/status`, {
    method: 'PATCH', body: JSON.stringify({ status }),
  })
  if (!res.ok) throw new Error('Failed to update status')
  return res.json()
}

export async function updateApplication(id, data) {
  if (isDemoMode()) return updateDemoApp(id, data)
  const res = await request(`${BASE}/applications/${id}`, {
    method: 'PUT', body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update application')
  return res.json()
}

export async function togglePin(id) {
  if (isDemoMode()) return toggleDemoPin(id)
  const res = await request(`${BASE}/applications/${id}/pin`, { method: 'PATCH' })
  if (!res.ok) throw new Error('Failed to toggle pin')
  return res.json()
}

export async function deleteApplication(id) {
  if (isDemoMode()) { deleteDemoApp(id); return }
  const res = await request(`${BASE}/applications/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete application')
}

export async function extractFromUrl(url) {
  const res = await request(`${BASE}/extract`, {
    method: 'POST', body: JSON.stringify({ url }),
  })
  if (!res.ok) throw new Error('Failed to extract from URL')
  return res.json()
}

export async function extractFromText(text) {
  const res = await request(`${BASE}/extract`, {
    method: 'POST', body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error('Failed to extract from text')
  return res.json()
}

export async function getStats(period = 'day') {
  if (isDemoMode()) return calcDemoStats(period)
  const res = await request(`${BASE}/stats?period=${period}`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}
