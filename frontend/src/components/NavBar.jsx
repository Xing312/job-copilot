import { NavLink, useNavigate } from 'react-router-dom'
import { clearToken } from '../auth'

export default function NavBar() {
  const navigate = useNavigate()

  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-100'
    }`

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
      <span className="text-indigo-700 font-bold text-lg mr-4">Job Copilot</span>
      <NavLink to="/applications" className={linkClass}>Applications</NavLink>
      <NavLink to="/applications/new" className={linkClass}>+ Add New</NavLink>
      <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
      <button
        onClick={handleLogout}
        className="ml-auto text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-md hover:bg-gray-100"
      >
        Log out
      </button>
    </nav>
  )
}
