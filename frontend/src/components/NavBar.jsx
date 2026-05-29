import { NavLink, useNavigate } from 'react-router-dom'
import { clearToken } from '../auth'
import useTheme from '../useTheme'

export default function NavBar() {
  const navigate = useNavigate()
  const [dark, toggleTheme] = useTheme()

  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-600 text-white'
        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
    }`

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  return (
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
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 px-3 py-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          Log out
        </button>
      </div>
    </nav>
  )
}
