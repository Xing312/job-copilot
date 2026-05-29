import { NavLink } from 'react-router-dom'

export default function NavBar() {
  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-600 text-white'
        : 'text-gray-600 hover:bg-gray-100'
    }`

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
      <span className="text-indigo-700 font-bold text-lg mr-4">Job Copilot</span>
      <NavLink to="/applications" className={linkClass}>Applications</NavLink>
      <NavLink to="/applications/new" className={linkClass}>+ Add New</NavLink>
      <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
    </nav>
  )
}
