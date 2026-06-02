import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApplications, updateStatus, togglePin } from '../api/applications'

const STATUS_COLORS = {
  Applied:       'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  OA:            'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  'Phone Screen':'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
  Interview:     'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  Offer:         'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  Rejected:      'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  Ghosted:       'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
}

const STATUSES = ['Applied', 'OA', 'Phone Screen', 'Interview', 'Offer', 'Rejected', 'Ghosted']
const WORK_TYPES = ['Remote', 'Hybrid', 'Onsite']

export default function Applications() {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updating, setUpdating] = useState(null)
  const [pinning, setPinning] = useState(null)

  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterWorkType, setFilterWorkType] = useState('')
  const [sortKey, setSortKey] = useState('applied_date')
  const [sortDir, setSortDir] = useState('desc')

  const navigate = useNavigate()

  useEffect(() => {
    getApplications()
      .then(setApps)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleTogglePin(id) {
    setPinning(id)
    try {
      const updated = await togglePin(id)
      setApps((prev) => prev.map((a) => (a.id === id ? updated : a)))
    } catch {
      // ignore
    } finally {
      setPinning(null)
    }
  }

  async function handleStatusChange(id, newStatus) {
    setUpdating(id)
    try {
      const updated = await updateStatus(id, newStatus)
      setApps((prev) => prev.map((a) => (a.id === id ? updated : a)))
    } catch {
      const fresh = await getApplications()
      setApps(fresh)
    } finally {
      setUpdating(null)
    }
  }

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const filtered = useMemo(() => {
    let result = apps

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (a) =>
          a.company.toLowerCase().includes(q) ||
          a.title.toLowerCase().includes(q),
      )
    }

    if (filterStatus) result = result.filter((a) => a.status === filterStatus)
    if (filterWorkType) result = result.filter((a) => a.work_type === filterWorkType)

    return [...result].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1
      if (!a.pinned && b.pinned) return 1
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      if (!av && bv) return 1
      if (av && !bv) return -1
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [apps, search, filterStatus, filterWorkType, sortKey, sortDir])

  function SortBtn({ col, children }) {
    const active = sortKey === col
    return (
      <button
        onClick={() => toggleSort(col)}
        className="flex items-center gap-1 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
      >
        {children}
        <span className={`text-xs ${active ? 'opacity-100' : 'opacity-25'}`}>
          {active ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
        </span>
      </button>
    )
  }

  if (loading) return <p className="p-8 text-gray-500 dark:text-gray-400">Loading…</p>
  if (error) return <p className="p-8 text-red-500">{error}</p>

  if (apps.length === 0) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <p className="text-gray-400 dark:text-gray-500 text-lg mb-4">No applications yet.</p>
        <Link to="/applications/new" className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700">
          Add your first one
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Applications{' '}
          <span className="text-gray-400 dark:text-gray-500 font-normal text-lg ml-1">
            {filtered.length !== apps.length ? `${filtered.length} / ${apps.length}` : apps.length}
          </span>
        </h1>
        <Link to="/applications/new" className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700">
          + Add New
        </Link>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Search company or title…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 text-sm rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={filterWorkType}
          onChange={(e) => setFilterWorkType(e.target.value)}
          className="px-3 py-2 text-sm rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">All work types</option>
          {WORK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
            <tr>
              <th className="px-3 py-3 w-8"></th>
              <th className="text-left px-4 py-3 font-medium"><SortBtn col="company">Company</SortBtn></th>
              <th className="text-left px-4 py-3 font-medium"><SortBtn col="title">Title</SortBtn></th>
              <th className="text-left px-4 py-3 font-medium"><SortBtn col="work_type">Work Type</SortBtn></th>
              <th className="text-left px-4 py-3 font-medium"><SortBtn col="platform">Platform</SortBtn></th>
              <th className="text-left px-4 py-3 font-medium"><SortBtn col="applied_date">Applied</SortBtn></th>
              <th className="text-left px-4 py-3 font-medium"><SortBtn col="status">Status</SortBtn></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-400 dark:text-gray-500">
                  No results match your search or filters.
                </td>
              </tr>
            ) : (
              filtered.map((app) => (
                <tr key={app.id} className={`hover:bg-gray-50 dark:hover:bg-gray-800/60 cursor-pointer${app.pinned ? ' border-l-2 border-indigo-400' : ''}`}>
                  <td className="px-3 py-3 text-center">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleTogglePin(app.id) }}
                      disabled={pinning === app.id}
                      title={app.pinned ? 'Unpin' : 'Pin to top'}
                      className={`text-base leading-none transition-opacity disabled:opacity-30 ${app.pinned ? 'opacity-100' : 'opacity-20 hover:opacity-60'}`}
                    >
                      📌
                    </button>
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100" onClick={() => navigate(`/applications/${app.id}`)}>{app.company}</td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300" onClick={() => navigate(`/applications/${app.id}`)}>{app.title}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400" onClick={() => navigate(`/applications/${app.id}`)}>{app.work_type || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400" onClick={() => navigate(`/applications/${app.id}`)}>{app.platform || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400" onClick={() => navigate(`/applications/${app.id}`)}>{app.applied_date || '—'}</td>
                  <td className="px-4 py-3">
                    <select
                      value={app.status}
                      disabled={updating === app.id}
                      onChange={(e) => handleStatusChange(app.id, e.target.value)}
                      className={`px-2 py-0.5 rounded-full text-xs font-medium border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50 ${STATUS_COLORS[app.status] ?? 'bg-gray-100 text-gray-600'}`}
                    >
                      {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
