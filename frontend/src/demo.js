export const DEMO_KEY = 'jc_demo'
export const DEMO_STORE_KEY = 'jc_demo_apps'

export const isDemoMode = () => localStorage.getItem(DEMO_KEY) === 'true'
export const enterDemo = () => localStorage.setItem(DEMO_KEY, 'true')
export const exitDemo = () => {
  localStorage.removeItem(DEMO_KEY)
  sessionStorage.removeItem(DEMO_STORE_KEY)
}

const DEMO_APPS_SEED = [
  {
    id: 1, company: 'Anthropic', title: 'Research Engineer, Interpretability',
    location: 'San Francisco, CA', salary_min: 180000, salary_max: 250000,
    work_type: 'Hybrid', platform: 'Greenhouse', status: 'Interview', pinned: false,
    applied_date: '2026-05-10', source_url: null, created_at: '2026-05-10T10:00:00',
  },
  {
    id: 2, company: 'Waymo', title: 'Data Scientist, Perception',
    location: 'Mountain View, CA', salary_min: 160000, salary_max: 220000,
    work_type: 'Onsite', platform: 'LinkedIn', status: 'Phone Screen', pinned: false,
    applied_date: '2026-05-08', source_url: null, created_at: '2026-05-08T10:00:00',
  },
  {
    id: 3, company: 'Stripe', title: 'Machine Learning Engineer',
    location: 'Remote', salary_min: 170000, salary_max: 230000,
    work_type: 'Remote', platform: 'Company Site', status: 'OA', pinned: false,
    applied_date: '2026-05-05', source_url: null, created_at: '2026-05-05T10:00:00',
  },
  {
    id: 4, company: 'Duolingo', title: 'Senior Data Scientist',
    location: 'Pittsburgh, PA', salary_min: 150000, salary_max: 200000,
    work_type: 'Hybrid', platform: 'Greenhouse', status: 'Applied', pinned: false,
    applied_date: '2026-05-14', source_url: null, created_at: '2026-05-14T10:00:00',
  },
  {
    id: 5, company: 'Netflix', title: 'Data Scientist, Recommendations',
    location: 'Los Gatos, CA', salary_min: 200000, salary_max: 300000,
    work_type: 'Onsite', platform: 'Lever', status: 'Rejected', pinned: false,
    applied_date: '2026-04-28', source_url: null, created_at: '2026-04-28T10:00:00',
  },
  {
    id: 6, company: 'Notion', title: 'ML Engineer, Search',
    location: 'San Francisco, CA', salary_min: 160000, salary_max: 210000,
    work_type: 'Hybrid', platform: 'Ashby', status: 'Ghosted', pinned: false,
    applied_date: '2026-04-20', source_url: null, created_at: '2026-04-20T10:00:00',
  },
]

// ── Session store ──────────────────────────────────────────────────────────

export function getDemoApps() {
  const raw = sessionStorage.getItem(DEMO_STORE_KEY)
  return raw ? JSON.parse(raw) : [...DEMO_APPS_SEED]
}

function saveDemoApps(apps) {
  sessionStorage.setItem(DEMO_STORE_KEY, JSON.stringify(apps))
}

function nextId() {
  const apps = getDemoApps()
  return apps.length ? Math.max(...apps.map((a) => a.id)) + 1 : 1
}

export function addDemoApp(data) {
  const apps = getDemoApps()
  const app = {
    ...data,
    id: nextId(),
    status: data.status || 'Applied',
    created_at: new Date().toISOString(),
    updated_at: null,
  }
  saveDemoApps([app, ...apps])
  return app
}

export function updateDemoApp(id, data) {
  const apps = getDemoApps()
  const app = { ...apps.find((a) => a.id === id), ...data, updated_at: new Date().toISOString() }
  saveDemoApps(apps.map((a) => (a.id === id ? app : a)))
  return app
}

export function updateDemoStatus(id, status) {
  return updateDemoApp(id, { status })
}

export function deleteDemoApp(id) {
  saveDemoApps(getDemoApps().filter((a) => a.id !== id))
}

export function toggleDemoPin(id) {
  const apps = getDemoApps()
  const app = apps.find((a) => a.id === id)
  if (!app) return null
  const updated = { ...app, pinned: !app.pinned, updated_at: new Date().toISOString() }
  saveDemoApps(apps.map((a) => (a.id === id ? updated : a)))
  return updated
}

// ── Stats calculation ──────────────────────────────────────────────────────

const STATUS_ORDER = ['Applied', 'OA', 'Phone Screen', 'Interview', 'Offer', 'Rejected', 'Ghosted']

function weekMonday(date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return d
}

function fmtWeek(date) {
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${m}/${d}`
}

export function calcDemoStats() {
  const apps = getDemoApps()
  const total = apps.length

  const statusCount = {}
  const platformCount = {}
  const workCount = {}
  const weekCount = {}

  for (const a of apps) {
    statusCount[a.status] = (statusCount[a.status] || 0) + 1
    if (a.platform) platformCount[a.platform] = (platformCount[a.platform] || 0) + 1
    if (a.work_type) workCount[a.work_type] = (workCount[a.work_type] || 0) + 1
    const d = a.applied_date ? new Date(a.applied_date) : a.created_at ? new Date(a.created_at) : null
    if (d) {
      const key = fmtWeek(weekMonday(d))
      weekCount[key] = (weekCount[key] || 0) + 1
    }
  }

  const today = new Date()
  const by_week = Array.from({ length: 12 }, (_, i) => {
    const d = new Date(today)
    d.setDate(d.getDate() - (11 - i) * 7)
    const key = fmtWeek(weekMonday(d))
    return { week: key, count: weekCount[key] || 0 }
  })

  const responded = apps.filter((a) => !['Applied', 'Ghosted'].includes(a.status)).length

  return {
    total,
    offers: statusCount['Offer'] || 0,
    interviews: statusCount['Interview'] || 0,
    response_rate: total ? Math.round((responded / total) * 1000) / 10 : 0,
    by_status: STATUS_ORDER.filter((s) => statusCount[s]).map((s) => ({ name: s, value: statusCount[s] })),
    by_week,
    by_platform: Object.entries(platformCount).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([name, value]) => ({ name, value })),
    by_work_type: Object.entries(workCount).map(([name, value]) => ({ name, value })),
  }
}
