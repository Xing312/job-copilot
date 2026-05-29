import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { login } from '../api/applications'
import { isLoggedIn, setToken } from '../auth'
import { enterDemo, isDemoMode } from '../demo'

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  if (isLoggedIn() || isDemoMode()) return <Navigate to="/applications" replace />

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { token } = await login(password)
      setToken(token)
      navigate('/applications')
    } catch {
      setError('Incorrect password')
    } finally {
      setLoading(false)
    }
  }

  function handleDemo() {
    enterDemo()
    navigate('/applications')
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">Job Copilot</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          Personal job application tracker with AI-powered auto-fill.
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            autoFocus
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-2 bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <button
            onClick={handleDemo}
            className="w-full py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Try Demo
          </button>
          <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
            Sample data — no sign-in required
          </p>
        </div>
      </div>
    </div>
  )
}
