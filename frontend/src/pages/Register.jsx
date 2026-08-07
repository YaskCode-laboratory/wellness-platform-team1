import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { registerUser } from '../services/api'
import logoMax from '../assets/runcoachlogomax.png'

const Register = () => {
    const { register, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    nombre: '',
    email: '',
    password: '',
    edad: '',
    peso: '',
    nivel: 'principiante'
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
        // 1. Auth Service crea el usuario en Firebase y guarda el perfil
        await registerUser({
        nombre: form.nombre,
        email: form.email,
        password: form.password,
        edad: parseInt(form.edad),
        peso: parseFloat(form.peso),
        nivel: form.nivel
        })

        // 2. Login con Firebase SDK para obtener el token
        await login(form.email, form.password)

        navigate('/dashboard')
    } catch (err) {
        console.log('Error completo:', err)
        console.log('Response:', err.response)
        console.log('Response data:', err.response?.data)
        if (err.response?.status === 400) {
            setError('Este correo ya está registrado')
        } else if (err.code === 'auth/weak-password') {
            setError('La contraseña debe tener al menos 6 caracteres')
        } else {
            setError('Error al registrar. Intenta de nuevo.')
        }
        setLoading(false)
    
    } finally {
        setLoading(false)
    }
    }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-8">
        <div className="text-center mb-6">
          <img
            src={logoMax}
            alt="RunCoach AI"
            className="mx-auto mb-3 w-48 object-contain"
          />
          <h1 className="text-2xl font-bold text-gray-800">Crear cuenta</h1>
          <p className="text-gray-500 text-sm mt-1">Comienza tu entrenamiento</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
            <input
              name="nombre"
              value={form.nombre}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Tu nombre"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Correo</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="correo@ejemplo.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Mínimo 6 caracteres"
              required
            />
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Edad</label>
              <input
                type="number"
                name="edad"
                value={form.edad}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Años"
                required
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Peso (kg)</label>
              <input
                type="number"
                name="peso"
                value={form.peso}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="kg"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nivel</label>
            <select
              name="nivel"
              value={form.nivel}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="principiante">Principiante</option>
              <option value="intermedio">Intermedio</option>
              <option value="avanzado">Avanzado</option>
            </select>
          </div>

          {error && (
            <p className="text-red-500 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition mt-2"
          >
            {loading ? 'Creando cuenta...' : 'Crear cuenta'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-blue-600 font-semibold">
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Register