import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getGoals, createGoal, deleteGoal, getGoalProgress } from '../services/api'

const formatearTiempoObjetivo = (totalMin) => {
  if (!totalMin) return null
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m} min`
}

const MiObjetivo = () => {
  const { user } = useAuth()
  const [goals, setGoals] = useState([])
  const [progressMap, setProgressMap] = useState({})
  const [loading, setLoading] = useState(true)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    tipo: 'semanal',
    kmMeta: '',
    distanciaObjetivoKm: '',
    horasObjetivo: '',
    minutosObjetivo: '',
    segundosObjetivo: '',
    fechaLimite: '',
    descripcion: ''
  })

  const fetchData = async () => {
    try {
      const [goalsRes, progressRes] = await Promise.all([
        getGoals(user.uid),
        getGoalProgress(user.uid)
      ])
      const goalsData = Array.isArray(goalsRes.data?.goals) ? goalsRes.data.goals : []
      setGoals(goalsData)

      const progressData = progressRes.data?.goals || []
      const map = {}
      progressData.forEach(p => { map[p.id] = p })
      setProgressMap(map)
    } catch (err) {
      console.log('Error:', err)
      setGoals([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [user.uid])

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const calcularTiempoObjetivoMin = () => {
    const h = parseInt(form.horasObjetivo || 0)
    const m = parseInt(form.minutosObjetivo || 0)
    const s = parseInt(form.segundosObjetivo || 0)
    return (h * 60) + m + Math.round(s / 60)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const data = { userId: user.uid, tipo: form.tipo }
      if (form.tipo === 'semanal') {
        data.kmMeta = parseFloat(form.kmMeta)
      } else {
        data.distanciaObjetivoKm = parseFloat(form.distanciaObjetivoKm)
        data.fechaLimite = form.fechaLimite
        const tiempoMin = calcularTiempoObjetivoMin()
        if (tiempoMin > 0) data.tiempoObjetivoMin = tiempoMin
        if (form.descripcion) data.descripcion = form.descripcion
      }
      await createGoal(data)
      await fetchData()
      setMostrarForm(false)
      setForm({
        tipo: 'semanal',
        kmMeta: '',
        distanciaObjetivoKm: '',
        horasObjetivo: '',
        minutosObjetivo: '',
        segundosObjetivo: '',
        fechaLimite: '',
        descripcion: ''
      })
    } catch (err) {
      console.log('Error:', err)
      setError('Error al guardar el objetivo')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (goalId) => {
    try {
      await deleteGoal(user.uid, goalId)
      setGoals(goals.filter(g => g.id !== goalId))
      setConfirmDelete(null)
    } catch (err) {
      console.log('Error al eliminar:', err)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-blue-600 text-lg">Cargando...</div>
    </div>
  )

  const goalsSemanal = goals.filter(g => g.tipo === 'semanal')
  const goalsLargoPlazo = goals.filter(g => g.tipo === 'largo_plazo')

  const renderConfirmDelete = (goalId) => (
    <div className="mt-3 bg-red-50 rounded-xl p-3">
      <p className="text-sm text-red-700 mb-2">Confirmar eliminacion?</p>
      <div className="flex gap-2">
        <button
          onClick={() => handleDelete(goalId)}
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
  )

  return (
    <div className="p-4 max-w-lg mx-auto">

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold text-gray-800">Mis objetivos</h1>
        <button
          onClick={() => setMostrarForm(!mostrarForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-blue-700 transition"
        >
          {mostrarForm ? 'Cancelar' : '+ Agregar'}
        </button>
      </div>

      {mostrarForm && (
        <div className="bg-white rounded-2xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Nuevo objetivo</h2>
          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de objetivo
              </label>
              <select
                name="tipo"
                value={form.tipo}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="semanal">Semanal — km por semana</option>
                <option value="largo_plazo">Largo plazo — distancia con fecha limite</option>
              </select>
            </div>

            {form.tipo === 'semanal' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Meta de km semanales
                </label>
                <input
                  type="number"
                  name="kmMeta"
                  value={form.kmMeta}
                  onChange={handleChange}
                  step="0.5"
                  min="1"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ej: 30"
                  required
                />
              </div>
            )}

            {form.tipo === 'largo_plazo' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Distancia objetivo (km)
                  </label>
                  <select
                    name="distanciaObjetivoKm"
                    value={form.distanciaObjetivoKm}
                    onChange={handleChange}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="">Selecciona una distancia</option>
                    <option value="5">5K</option>
                    <option value="10">10K</option>
                    <option value="21">Media Maraton (21K)</option>
                    <option value="42">Maraton (42K)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tiempo objetivo (opcional)
                  </label>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <input
                        type="number"
                        name="horasObjetivo"
                        value={form.horasObjetivo}
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
                        name="minutosObjetivo"
                        value={form.minutosObjetivo}
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
                        name="segundosObjetivo"
                        value={form.segundosObjetivo}
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
                    Fecha limite
                  </label>
                  <input
                    type="date"
                    name="fechaLimite"
                    value={form.fechaLimite}
                    onChange={handleChange}
                    min={new Date().toISOString().split('T')[0]}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descripcion (opcional)
                  </label>
                  <input
                    type="text"
                    name="descripcion"
                    value={form.descripcion}
                    onChange={handleChange}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ej: Correr el maraton de Maracaibo"
                  />
                </div>
              </>
            )}

            {error && (
              <p className="text-red-500 text-sm text-center">{error}</p>
            )}

            <button
              type="submit"
              disabled={saving}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {saving ? 'Guardando...' : 'Guardar objetivo'}
            </button>
          </form>
        </div>
      )}

      {goalsSemanal.length > 0 && (
        <div className="mb-5">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Objetivos semanales
          </h2>
          <div className="space-y-3">
            {goalsSemanal.map(goal => {
              const p = progressMap[goal.id] || {}
              const porcentaje = p.porcentajeCompletado || 0
              const logrado = porcentaje >= 100
              return (
                <div
                  key={goal.id}
                  className={`rounded-2xl shadow-sm p-4 ${logrado ? 'bg-green-50 border border-green-300' : 'bg-white'}`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-gray-800">
                          {goal.kmMeta} km
                          {goal.tiempoObjetivoMin && ` en ${formatearTiempoObjetivo(goal.tiempoObjetivoMin)}`}
                        </p>
                        {p.estado === 'logrado' && (
                          <span className="text-xs bg-green-500 text-white px-2 py-0.5 rounded-full font-semibold">
                            Logrado
                          </span>
                        )}
                        {p.estado === 'distancia_lograda_tiempo_no' && (
                          <span className="text-xs bg-yellow-500 text-white px-2 py-0.5 rounded-full font-semibold">
                            Distancia lograda
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-1">{p.semana || ''}</p>
                    </div>
                    <button
                      onClick={() => setConfirmDelete(goal.id)}
                      className="text-red-400 hover:text-red-600 text-xs transition"
                    >
                      Eliminar
                    </button>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                    <div
                      className={`h-3 rounded-full transition-all ${logrado ? 'bg-green-500' : 'bg-blue-600'}`}
                      style={{ width: `${Math.min(porcentaje, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{p.kmAcumulados?.toFixed(1) || 0} km recorridos</span>
                    <span>{Math.min(porcentaje, 100)}%</span>
                  </div>

                  {confirmDelete === goal.id && renderConfirmDelete(goal.id)}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {goalsLargoPlazo.length > 0 && (
        <div className="mb-5">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Objetivos a largo plazo
          </h2>
          <div className="space-y-3">
            {goalsLargoPlazo.map(goal => {
              const p = progressMap[goal.id] || {}
              const porcentaje = p.porcentajeCompletado || 0
              const logrado = p.estado === 'logrado'
              const distanciaLograda = p.estado === 'distancia_lograda_tiempo_no'
              return (
                <div
                  key={goal.id}
                  className={`rounded-2xl shadow-sm p-4 ${
                    logrado ? 'bg-green-50 border border-green-300' :
                    distanciaLograda ? 'bg-yellow-50 border border-yellow-300' :
                    'bg-white'
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-gray-800">
                          {goal.distanciaObjetivoKm} km
                          {goal.tiempoObjetivoMin && ` en ${formatearTiempoObjetivo(goal.tiempoObjetivoMin)}`}
                        </p>
                        {logrado && (
                          <span className="text-xs bg-green-500 text-white px-2 py-0.5 rounded-full font-semibold">
                            Logrado
                          </span>
                        )}
                      </div>
                      {goal.descripcion && (
                        <p className="text-xs text-gray-500 mt-1">{goal.descripcion}</p>
                      )}
                      <p className="text-xs text-gray-400 mt-1">
                        Fecha limite: {goal.fechaLimite}
                      </p>
                    </div>
                    <button
                      onClick={() => setConfirmDelete(goal.id)}
                      className="text-red-400 hover:text-red-600 text-xs transition"
                    >
                      Eliminar
                    </button>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                    <div
                      className={`h-3 rounded-full transition-all ${
                        logrado ? 'bg-green-500' :
                        distanciaLograda ? 'bg-yellow-500' :
                        'bg-blue-600'
                      }`}
                      style={{ width: `${Math.min(porcentaje, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{p.kmAcumulados?.toFixed(1) || 0} km recorridos</span>
                    <span>{Math.min(porcentaje, 100)}%</span>
                    
                  </div>
                  {distanciaLograda && (
                    <p className="text-xs text-yellow-600 mt-2 font-medium">
                      Distancia alcanzada. Sigue mejorando tu tiempo para lograr el objetivo completo.
                    </p>
                  )}
                  {confirmDelete === goal.id && renderConfirmDelete(goal.id)}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {goals.length === 0 && !mostrarForm && (
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
          <p className="text-gray-400 text-sm">
            No tienes objetivos activos. Presiona Agregar para crear uno.
          </p>
        </div>
      )}

    </div>
  )
}

export default MiObjetivo