import { NavLink } from 'react-router-dom'
import { isDemoMode } from '../demo'
import useTheme from '../useTheme'

export default function NavBar() {
  const [dark, toggleTheme] = useTheme()
  const demo = isDemoMode()

  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-600 text-white'
        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
    }`

  return (
    <div>
      {demo && (
        <div className="bg-amber-50 dark:bg-amber-900/30 border-b border-amber-200 dark:border-amber-700 px-6 py-2 text-sm">
          <span className="text-amber-800 dark:text-amber-300">
            Demo mode — this is a public sample. Your changes stay in your browser
            and are never saved to a server.
          </span>
        </div>
      )}
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-3 flex items-center gap-4">
        <span className="text-indigo-700 dark:text-indigo-400 font-bold text-lg mr-4">Job Copilot</span>
        <NavLink to="/applications" className={linkClass}>Applications</NavLink>
        <NavLink to="/applications/new" className={linkClass}>+ Add New</NavLink>
        <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 text-base"
            title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {dark ? '☀️' : '🌙'}
          </button>
        </div>
      </nav>
    </div>
  )
}
