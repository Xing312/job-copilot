import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar'
import Applications from './pages/Applications'
import AddApplication from './pages/AddApplication'
import ApplicationDetail from './pages/ApplicationDetail'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import { isLoggedIn } from './auth'

function Guard({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />
}

export default function App() {
  // Apply saved theme on first load
  useEffect(() => {
    if (localStorage.getItem('theme') === 'dark') {
      document.documentElement.classList.add('dark')
    }
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={
        <Guard>
          <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            <NavBar />
            <Routes>
              <Route path="/" element={<Navigate to="/applications" replace />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/applications/new" element={<AddApplication />} />
              <Route path="/applications/:id" element={<ApplicationDetail />} />
              <Route path="/dashboard" element={<Dashboard />} />
            </Routes>
          </div>
        </Guard>
      } />
    </Routes>
  )
}
