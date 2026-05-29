import { getToken, clearToken } from '../auth'

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
  const res = await request(`${BASE}/applications`)
  if (!res.ok) throw new Error('Failed to fetch applications')
  return res.json()
}

export async function createApplication(data) {
  const res = await request(`${BASE}/applications`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create application')
  return res.json()
}

export async function getApplication(id) {
  const res = await request(`${BASE}/applications/${id}`)
  if (!res.ok) throw new Error('Application not found')
  return res.json()
}

export async function updateStatus(id, status) {
  const res = await request(`${BASE}/applications/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
  if (!res.ok) throw new Error('Failed to update status')
  return res.json()
}

export async function updateApplication(id, data) {
  const res = await request(`${BASE}/applications/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update application')
  return res.json()
}

export async function deleteApplication(id) {
  const res = await request(`${BASE}/applications/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete application')
}

export async function extractFromUrl(url) {
  const res = await request(`${BASE}/extract`, {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
  if (!res.ok) throw new Error('Failed to extract from URL')
  return res.json()
}

export async function extractFromText(text) {
  const res = await request(`${BASE}/extract`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error('Failed to extract from text')
  return res.json()
}

export async function getStats() {
  const res = await request(`${BASE}/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}
