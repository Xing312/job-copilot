import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createApplication, extractFromUrl, extractFromText } from '../api/applications'

const WORK_TYPES = ['Remote', 'Hybrid', 'Onsite']
const PLATFORMS = ['LinkedIn', 'Greenhouse', 'Lever', 'Workday', 'Company Site', 'Indeed', 'Other']
const STATUSES = ['Applied', 'OA', 'Phone Screen', 'Interview', 'Offer', 'Rejected', 'Ghosted']

function todayLocal() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getEmptyForm() {
  return {
    company: '',
    title: '',
    location: '',
    salary_min: '',
    salary_max: '',
    work_type: '',
    platform: '',
    source_url: '',
    applied_date: todayLocal(),
    status: 'Applied',
  }
}

function Field({ label, children, required }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {children}
    </div>
  )
}

const inputClass =
  'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent'

export default function AddApplication() {
  const [form, setForm] = useState(getEmptyForm)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const [pasteInput, setPasteInput] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState(null)
  const [filledFields, setFilledFields] = useState([])

  const isUrl = /^https?:\/\/\S+$/.test(pasteInput.trim())
  const inputType = pasteInput.trim() ? (isUrl ? 'url' : 'text') : null

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleExtract() {
    setExtracting(true)
    setExtractError(null)
    setFilledFields([])
    try {
      const data = isUrl
        ? await extractFromUrl(pasteInput.trim())
        : await extractFromText(pasteInput.trim())

      const filled = []
      const patch = {}
      const fieldMap = {
        title: 'title', company: 'company', location: 'location',
        salary_min: 'salary_min', salary_max: 'salary_max',
        work_type: 'work_type', platform: 'platform', source_url: 'source_url',
      }
      for (const [key, formKey] of Object.entries(fieldMap)) {
        if (data[key] != null && data[key] !== '') {
          patch[formKey] = String(data[key])
          filled.push(key)
        }
      }
      setForm((f) => ({ ...f, ...patch }))
      setFilledFields(filled)
    } catch (e) {
      setExtractError(e.message)
    } finally {
      setExtracting(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
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
      await createApplication(payload)
      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="max-w-lg mx-auto mt-20 text-center">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">Application saved!</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">{form.title} @ {form.company}</p>
        <div className="flex justify-center gap-3">
          <button
            onClick={() => { setForm(getEmptyForm()); setPasteInput(''); setFilledFields([]); setExtractError(null); setSuccess(false) }}
            className="px-4 py-2 rounded-md bg-indigo-600 text-white text-sm hover:bg-indigo-700"
          >
            Add another
          </button>
          <button
            onClick={() => navigate('/applications')}
            className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            View all
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Add Application</h1>

      {/* Auto-fill section */}
      <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium text-indigo-800 dark:text-indigo-300">Auto-fill from job posting</p>
          {inputType && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              inputType === 'url'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                : 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
            }`}>
              {inputType === 'url' ? '🔗 URL' : '📄 JD Text'}
            </span>
          )}
        </div>
        <textarea
          value={pasteInput}
          onChange={(e) => setPasteInput(e.target.value)}
          placeholder="Paste a job URL or full job description…"
          rows={isUrl ? 2 : 4}
          className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none mb-2"
        />
        <div className="flex items-center justify-between">
          <div>
            {extractError && <p className="text-xs text-red-600 dark:text-red-400">{extractError}</p>}
            {filledFields.length > 0 && (
              <p className="text-xs text-indigo-700 dark:text-indigo-400">Filled: {filledFields.join(', ')}</p>
            )}
          </div>
          <button
            type="button"
            onClick={handleExtract}
            disabled={extracting || !pasteInput.trim()}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
          >
            {extracting ? 'Extracting…' : 'Extract'}
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Company" required>
            <input
              className={inputClass}
              value={form.company}
              onChange={set('company')}
              required
              placeholder="Google"
            />
          </Field>
          <Field label="Job Title" required>
            <input
              className={inputClass}
              value={form.title}
              onChange={set('title')}
              required
              placeholder="Software Engineer"
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Location">
            <input
              className={inputClass}
              value={form.location}
              onChange={set('location')}
              placeholder="New York, NY"
            />
          </Field>
          <Field label="Work Type">
            <select className={inputClass} value={form.work_type} onChange={set('work_type')}>
              <option value="">Select…</option>
              {WORK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Salary Min ($)">
            <input
              type="number"
              className={inputClass}
              value={form.salary_min}
              onChange={set('salary_min')}
              placeholder="80000"
            />
          </Field>
          <Field label="Salary Max ($)">
            <input
              type="number"
              className={inputClass}
              value={form.salary_max}
              onChange={set('salary_max')}
              placeholder="120000"
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Platform">
            <select className={inputClass} value={form.platform} onChange={set('platform')}>
              <option value="">Select…</option>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </Field>
          <Field label="Applied Date">
            <input
              type="date"
              className={inputClass}
              value={form.applied_date}
              onChange={set('applied_date')}
            />
          </Field>
        </div>

        <Field label="Job Posting URL">
          <input
            className={inputClass}
            value={form.source_url}
            onChange={set('source_url')}
            placeholder="https://..."
          />
        </Field>

        <Field label="Status">
          <select className={inputClass} value={form.status} onChange={set('status')}>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 px-4 bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Saving…' : 'Save Application'}
        </button>
      </form>
    </div>
  )
}
