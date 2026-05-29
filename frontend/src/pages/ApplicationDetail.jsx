import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getApplication, updateApplication, deleteApplication } from '../api/applications'

const WORK_TYPES = ['Remote', 'Hybrid', 'Onsite']
const PLATFORMS = ['LinkedIn', 'Greenhouse', 'Lever', 'Workday', 'Company Site', 'Indeed', 'Other']
const STATUSES = ['Applied', 'OA', 'Phone Screen', 'Interview', 'Offer', 'Rejected', 'Ghosted']

const inputClass =
  'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent'

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
      {children}
    </div>
  )
}

function ReadValue({ value }) {
  return <p className="text-sm text-gray-900 dark:text-gray-100 py-2">{value || <span className="text-gray-400 dark:text-gray-500">—</span>}</p>
}

export default function ApplicationDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [app, setApp] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    getApplication(id)
      .then((data) => { setApp(data); setForm(toForm(data)) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  function toForm(data) {
    return {
      company: data.company ?? '',
      title: data.title ?? '',
      location: data.location ?? '',
      salary_min: data.salary_min ?? '',
      salary_max: data.salary_max ?? '',
      work_type: data.work_type ?? '',
      platform: data.platform ?? '',
      source_url: data.source_url ?? '',
      applied_date: data.applied_date ?? '',
      status: data.status ?? 'Applied',
    }
  }

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleSave() {
    setSaving(true)
    try {
      const payload = {
        ...form,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
        location: form.location || null,
        work_type: form.work_type || null,
        platform: form.platform || null,
        source_url: form.source_url || null,
        applied_date: form.applied_date || null,
      }
      const updated = await updateApplication(id, payload)
      setApp(updated)
      setForm(toForm(updated))
      setEditing(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete "${app.title} @ ${app.company}"?`)) return
    setDeleting(true)
    try {
      await deleteApplication(id)
      navigate('/applications')
    } catch (e) {
      setError(e.message)
      setDeleting(false)
    }
  }

  if (loading) return <p className="p-8 text-gray-500 dark:text-gray-400">Loading…</p>
  if (error) return <p className="p-8 text-red-500">{error}</p>

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => navigate('/applications')} className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-1">
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{app.title}</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm">{app.company}</p>
        </div>
        <div className="flex gap-2">
          {!editing && (
            <>
              <button
                onClick={() => setEditing(true)}
                className="px-4 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm rounded-md border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Company">
            {editing ? <input className={inputClass} value={form.company} onChange={set('company')} required /> : <ReadValue value={app.company} />}
          </Field>
          <Field label="Job Title">
            {editing ? <input className={inputClass} value={form.title} onChange={set('title')} required /> : <ReadValue value={app.title} />}
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Location">
            {editing ? <input className={inputClass} value={form.location} onChange={set('location')} /> : <ReadValue value={app.location} />}
          </Field>
          <Field label="Work Type">
            {editing
              ? <select className={inputClass} value={form.work_type} onChange={set('work_type')}>
                  <option value="">Select…</option>
                  {WORK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              : <ReadValue value={app.work_type} />}
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Salary Min ($)">
            {editing ? <input type="number" className={inputClass} value={form.salary_min} onChange={set('salary_min')} /> : <ReadValue value={app.salary_min} />}
          </Field>
          <Field label="Salary Max ($)">
            {editing ? <input type="number" className={inputClass} value={form.salary_max} onChange={set('salary_max')} /> : <ReadValue value={app.salary_max} />}
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Platform">
            {editing
              ? <select className={inputClass} value={form.platform} onChange={set('platform')}>
                  <option value="">Select…</option>
                  {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              : <ReadValue value={app.platform} />}
          </Field>
          <Field label="Applied Date">
            {editing ? <input type="date" className={inputClass} value={form.applied_date} onChange={set('applied_date')} /> : <ReadValue value={app.applied_date} />}
          </Field>
        </div>

        <Field label="Job Posting URL">
          {editing
            ? <input className={inputClass} value={form.source_url} onChange={set('source_url')} placeholder="https://…" />
            : app.source_url
              ? <a href={app.source_url} target="_blank" rel="noreferrer" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline py-2 block">{app.source_url}</a>
              : <ReadValue value={null} />}
        </Field>

        <Field label="Status">
          {editing
            ? <select className={inputClass} value={form.status} onChange={set('status')}>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            : <ReadValue value={app.status} />}
        </Field>

        {editing && (
          <div className="flex gap-3 pt-2">
            <button onClick={handleSave} disabled={saving} className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
            <button
              onClick={() => { setForm(toForm(app)); setEditing(false) }}
              className="px-4 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
