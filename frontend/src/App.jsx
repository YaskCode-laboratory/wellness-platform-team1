import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import BottomNav from './components/BottomNav'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import NuevaSesion from './pages/NuevaSesion'
import Historial from './pages/Historial'
import MiObjetivo from './pages/MiObjetivo'
import Recomendacion from './pages/Recomendacion'
import Estadisticas from './pages/Estadisticas'
import Perfil from './pages/Perfil'

const Layout = ({ children }) => (
  <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-16">
    {children}
    <BottomNav />
  </div>
)

const AppContent = () => {
  const { darkMode } = useAuth()

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={
        <ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>
      } />
      <Route path="/nueva-sesion" element={
        <ProtectedRoute><Layout><NuevaSesion /></Layout></ProtectedRoute>
      } />
      <Route path="/historial" element={
        <ProtectedRoute><Layout><Historial /></Layout></ProtectedRoute>
      } />
      <Route path="/mi-objetivo" element={
        <ProtectedRoute><Layout><MiObjetivo /></Layout></ProtectedRoute>
      } />
      <Route path="/recomendacion" element={
        <ProtectedRoute><Layout><Recomendacion /></Layout></ProtectedRoute>
      } />
      <Route path="/estadisticas" element={
        <ProtectedRoute><Layout><Estadisticas /></Layout></ProtectedRoute>
      } />
      <Route path="/perfil" element={
        <ProtectedRoute><Layout><Perfil /></Layout></ProtectedRoute>
      } />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

const App = () => <AppContent />

export default App