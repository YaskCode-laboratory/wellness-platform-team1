import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getUser, updateProfile } from '../services/api'

const Perfil = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    nombre: '',
    peso: '',
    edad: '',
    nivel: 'principiante',
    ciudad: ''
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState(false)

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await getUser(user.uid)
        setForm({
          nombre: res.data.nombre || '',
          peso: res.data.peso || '',
          edad: res.data.edad || '',
          nivel: res.data.nivel || 'principiante',
          ciudad: res.data.ciudad || ''
        })
      } catch (err) {
        console.log('Error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchProfile()
  }, [user.uid])

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setExito(false)
    setSaving(true)
    try {
      await updateProfile(user.uid, {
        nombre: form.nombre,
        peso: parseFloat(form.peso),
        edad: parseInt(form.edad),
        nivel: form.nivel,
        ciudad: form.ciudad || null
      })
      setExito(true)
      setTimeout(() => setExito(false), 3000)
    } catch (err) {
      console.log('Error:', err)
      setError('Error al actualizar el perfil')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-blue-600 text-lg">Cargando...</div>
    </div>
  )

  return (
    <div className="p-4 max-w-lg mx-auto">

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold text-gray-800">Mi perfil</h1>
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-gray-500 hover:text-gray-700 transition"
        >
          Volver
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
        <div className="flex items-center gap-4 mb-5 pb-5 border-b border-gray-100">
          <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-2xl font-bold text-blue-600">
              {form.nombre?.charAt(0)?.toUpperCase() || 'U'}
            </span>
          </div>
          <div>
            <p className="font-bold text-gray-800">{form.nombre}</p>
            <p className="text-sm text-gray-500">{user.email}</p>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium capitalize">
              {form.nivel}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nombre
            </label>
            <input
              type="text"
              name="nombre"
              value={form.nombre}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Tu nombre"
              required
            />
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Peso (kg)
              </label>
              <input
                type="number"
                name="peso"
                value={form.peso}
                onChange={handleChange}
                step="0.1"
                min="0"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="kg"
                required
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Edad
              </label>
              <input
                type="number"
                name="edad"
                value={form.edad}
                onChange={handleChange}
                min="0"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="años"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nivel
            </label>
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ciudad
            </label>
            <input
              type="text"
              name="ciudad"
              value={form.ciudad}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ej: Maracaibo"
            />
            <p className="text-xs text-gray-400 mt-1">
              Permite que el coach consulte el clima antes de recomendarte un
              entrenamiento. Si la dejas vacía, te lo dirá en vez de suponerlo.
            </p>
          </div>

          {error && (
            <p className="text-red-500 text-sm text-center">{error}</p>
          )}

          {exito && (
            <p className="text-green-500 text-sm text-center font-medium">
              Perfil actualizado correctamente
            </p>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </button>

        </form>
      </div>

      <button
        onClick={handleLogout}
        className="w-full bg-red-50 text-red-500 py-3 rounded-xl font-semibold text-sm hover:bg-red-100 transition"
      >
        Cerrar sesion
      </button>

    </div>
  )
}

export default Perfil