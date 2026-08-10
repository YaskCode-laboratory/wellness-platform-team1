import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getSessions, deleteSession, updateSession } from '../services/api'
import logoMax from '../assets/runcoachlogomax.png'

const formatearRitmo = (ritmoDecimal) => {
  if (!ritmoDecimal) return '--'
  const minutos = Math.floor(ritmoDecimal)
  const segundos = Math.round((ritmoDecimal - minutos) * 60)
  return `${minutos}:${segundos.toString().padStart(2, '0')}`
}

const formatearTiempo = (segundos) => {
  if (!segundos) return '--'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  const s = segundos % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  return `${m}m ${s}s`
}

const calcularRitmo = (distanciaKm, tiempoSeg) => {
  const dist = parseFloat(distanciaKm)
  const tiempo = parseFloat(tiempoSeg)
  if (dist > 0 && tiempo > 0) return parseFloat(((tiempo / 60) / dist).toFixed(2))
  return 0
}

const EditModal = ({ session, onClose, onSave }) => {
  const [form, setForm] = useState({
    distanciaKm: session.distanciaKm,
    tiempoSeg: session.tiempoSeg,
    fcPromedio: session.fcPromedio || '',
    notas: session.notas || ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const isValid = parseFloat(form.distanciaKm) > 0 && parseFloat(form.tiempoSeg) > 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!isValid) return
    setLoading(true)
    setError('')
    try {
      const ritmoMin = calcularRitmo(form.distanciaKm, form.tiempoSeg)
      await onSave(session.id, {
        distanciaKm: parseFloat(form.distanciaKm),
        tiempoSeg: parseFloat(form.tiempoSeg),
        ritmoMin,
        fcPromedio: form.fcPromedio ? parseInt(form.fcPromedio) : null,
        notas: form.notas || null
      })
    } catch {
      setError('Error al guardar. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  const ritmoPreview = calcularRitmo(form.distanciaKm, form.tiempoSeg)
  const tiempoEnMinutos = form.tiempoSeg ? (parseFloat(form.tiempoSeg) / 60).toFixed(1) : 0

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex justify-between items-center p-5 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-800">Editar sesion</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <p className="text-sm text-gray-500">{session.fecha}</p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Distancia (km)</label>
            <input
              type="number"
              name="distanciaKm"
              value={form.distanciaKm}
              onChange={handleChange}
              step="0.1"
              min="0.1"
              required
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tiempo (segundos)</label>
            <input
              type="number"
              name="tiempoSeg"
              value={form.tiempoSeg}
              onChange={handleChange}
              min="1"
              required
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {form.tiempoSeg && (
              <p className="text-xs text-gray-400 mt-1">{tiempoEnMinutos} minutos</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">FC Promedio (opcional)</label>
            <input
              type="number"
              name="fcPromedio"
              value={form.fcPromedio}
              onChange={handleChange}
              min="0"
              max="220"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notas (opcional)</label>
            <textarea
              name="notas"
              value={form.notas}
              onChange={handleChange}
              rows={2}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {form.distanciaKm && form.tiempoSeg && (
            <div className="bg-blue-50 rounded-xl p-3 text-center">
              <p className="text-xs text-blue-600 font-medium">Ritmo calculado</p>
              <p className="text-xl font-bold text-blue-700 mt-0.5">
                {formatearRitmo(ritmoPreview)} min/km
              </p>
            </div>
          )}

          {error && <p className="text-red-500 text-sm text-center">{error}</p>}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-xl text-sm font-semibold hover:bg-gray-200 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !isValid}
              className="flex-1 bg-blue-600 text-white py-3 rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const Historial = () => {
  const { user } = useAuth()
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [editSession, setEditSession] = useState(null)

  const fetchSessions = async () => {
    try {
      const res = await getSessions(user.uid)
      setSessions(Array.isArray(res.data) ? res.data : res.data.sessions || [])
    } catch (err) {
      console.log('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSessions()
  }, [user.uid])

  const handleDelete = async (sessionId) => {
    try {
      await deleteSession(user.uid, sessionId)
      setSessions(sessions.filter(s => s.id !== sessionId))
      setConfirmDelete(null)
    } catch (err) {
      console.log('Error al eliminar:', err)
    }
  }

  const handleEdit = async (sessionId, updates) => {
    await updateSession(user.uid, sessionId, updates)
    setSessions(sessions.map(s => s.id === sessionId ? { ...s, ...updates } : s))
    setEditSession(null)
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-blue-600 text-lg">Cargando...</div>
    </div>
  )

  return (
    <div className="p-4 max-w-lg mx-auto">

      {editSession && (
        <EditModal
          session={editSession}
          onClose={() => setEditSession(null)}
          onSave={handleEdit}
        />
      )}

      <div className="mb-6">
        <div className="text-center mb-4">
          <img
            src={logoMax}
            alt="RunCoach AI"
            className="mx-auto mb-3 w-40 object-contain"
          />
          <h1 className="text-xl font-bold text-gray-800">Historial</h1>
        </div>
        <div className="flex justify-end">
          <span className="text-sm text-gray-500">{sessions.length} sesiones</span>
        </div>
      </div>

      {sessions.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
          <p className="text-gray-400 text-sm">No tienes sesiones registradas</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <div key={session.id} className="bg-white rounded-2xl shadow-sm p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="font-semibold text-gray-800">{session.fecha}</p>
                  {session.notas && (
                    <p className="text-xs text-gray-400 mt-1">{session.notas}</p>
                  )}
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => setEditSession(session)}
                    className="text-blue-400 hover:text-blue-600 text-xs transition"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => setConfirmDelete(session.id)}
                    className="text-red-400 hover:text-red-600 text-xs transition"
                  >
                    Eliminar
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-blue-600">
                    {session.distanciaKm}
                  </p>
                  <p className="text-xs text-gray-500">km</p>
                </div>
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-blue-600">
                    {formatearTiempo(session.tiempoSeg)}
                  </p>
                  <p className="text-xs text-gray-500">tiempo</p>
                </div>
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-blue-600">
                    {formatearRitmo(session.ritmoMin)}
                  </p>
                  <p className="text-xs text-gray-500">min/km</p>
                </div>
              </div>

              {session.fcPromedio && (
                <p className="text-xs text-gray-400 mt-2">
                  FC: {session.fcPromedio} bpm
                </p>
              )}

              {confirmDelete === session.id && (
                <div className="mt-3 bg-red-50 rounded-xl p-3">
                  <p className="text-sm text-red-700 mb-2">
                    Confirmar eliminacion?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleDelete(session.id)}
                      className="flex-1 bg-red-500 text-white py-2 rounded-lg text-sm font-semibold hover:bg-red-600 transition"
                    >
                      Eliminar
                    </button>
                    <button
                      onClick={() => setConfirmDelete(null)}
                      className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg text-sm font-semibold hover:bg-gray-300 transition"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Historial