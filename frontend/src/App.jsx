import { Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar'
import Applications from './pages/Applications'
import AddApplication from './pages/AddApplication'
import ApplicationDetail from './pages/ApplicationDetail'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <Routes>
        <Route path="/" element={<Navigate to="/applications" replace />} />
        <Route path="/applications" element={<Applications />} />
        <Route path="/applications/new" element={<AddApplication />} />
        <Route path="/applications/:id" element={<ApplicationDetail />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </div>
  )
}
