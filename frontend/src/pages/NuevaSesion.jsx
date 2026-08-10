import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { createSession } from '../services/api'
import logoMax from '../assets/runcoachlogomax.png'

const formatearRitmo = (ritmoDecimal) => {
  if (!ritmoDecimal || ritmoDecimal === 0) return '0:00 min/km'
  const minutos = Math.floor(ritmoDecimal)
  const segundos = Math.round((ritmoDecimal - minutos) * 60)
  return `${minutos}:${segundos.toString().padStart(2, '0')} min/km`
}

const NuevaSesion = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    fecha: new Date().toISOString().split('T')[0],
    distanciaKm: '',
    horas: '',
    minutos: '',
    segundos: '',
    fcPromedio: '',
    notas: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const calcularTotalSegundos = () => {
    return (
      (parseFloat(form.horas || 0) * 3600) +
      (parseFloat(form.minutos || 0) * 60) +
      parseFloat(form.segundos || 0)
    )
  }

  const calcularRitmo = () => {
    const dist = parseFloat(form.distanciaKm)
    const totalSeg = calcularTotalSegundos()
    if (dist > 0 && totalSeg > 0) {
      return (totalSeg / 60) / dist
    }
    return 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const ritmoMin = calcularRitmo()
      const totalSeg = calcularTotalSegundos()
      await createSession({
        userId: user.uid,
        fecha: form.fecha,
        distanciaKm: parseFloat(form.distanciaKm),
        tiempoSeg: totalSeg,
        ritmoMin: ritmoMin,
        fcPromedio: form.fcPromedio ? parseInt(form.fcPromedio) : null,
        notas: form.notas || null
      })
      navigate('/historial')
    } catch (err) {
      console.log('Error:', err)
      setError('Error al guardar la sesion. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  const tienesTiempo = form.horas || form.minutos || form.segundos
  const ritmoCalculado = calcularRitmo()

  return (
    <div className="p-4 max-w-lg mx-auto">

      <div className="text-center mb-6">
        <img
          src={logoMax}
          alt="RunCoach AI"
          className="mx-auto mb-3 w-40 object-contain"
        />
        <h1 className="text-xl font-bold text-gray-800">Registrar sesion</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">

        <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Fecha
            </label>
            <input
              type="date"
              name="fecha"
              value={form.fecha}
              onChange={handleChange}
              max={new Date().toISOString().split('T')[0]}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Distancia (km)
            </label>
            <input
              type="number"
              name="distanciaKm"
              value={form.distanciaKm}
              onChange={handleChange}
              step="0.1"
              min="0"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ej: 5.5"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tiempo
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <input
                  type="number"
                  name="horas"
                  value={form.horas}
                  onChange={handleChange}
                  min="0"
                  className="w-full border border-gray-300 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
                <p className="text-xs text-gray-400 mt-1 text-center">horas</p>
              </div>
              <div className="flex-1">
                <input
                  type="number"
                  name="minutos"
                  value={form.minutos}
                  onChange={handleChange}
                  min="0"
                  max="59"
                  className="w-full border border-gray-300 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
                <p className="text-xs text-gray-400 mt-1 text-center">min</p>
              </div>
              <div className="flex-1">
                <input
                  type="number"
                  name="segundos"
                  value={form.segundos}
                  onChange={handleChange}
                  min="0"
                  max="59"
                  className="w-full border border-gray-300 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
                <p className="text-xs text-gray-400 mt-1 text-center">seg</p>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              FC Promedio (opcional)
            </label>
            <input
              type="number"
              name="fcPromedio"
              value={form.fcPromedio}
              onChange={handleChange}
              min="0"
              max="220"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Frecuencia cardiaca promedio"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notas (opcional)
            </label>
            <textarea
              name="notas"
              value={form.notas}
              onChange={handleChange}
              rows={3}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Como te sentiste, condiciones del terreno..."
            />
          </div>

        </div>

        {form.distanciaKm && tienesTiempo && (
          <div className="bg-blue-50 rounded-2xl p-4 text-center">
            <p className="text-sm text-blue-600 font-medium">Ritmo calculado</p>
            <p className="text-2xl font-bold text-blue-700 mt-1">
              {formatearRitmo(ritmoCalculado)}
            </p>
          </div>
        )}

        {error && (
          <p className="text-red-500 text-sm text-center">{error}</p>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex-1 border border-gray-300 text-gray-600 py-3 rounded-xl font-semibold text-sm hover:bg-gray-50 transition"
          >
            Volver
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Guardando...' : 'Guardar sesion'}
          </button>
        </div>

      </form>
    </div>
  )
}

export default NuevaSesion