import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getRecommendation, getRecommendations, analyzeWithAgent } from '../services/api'

const prioridadColor = {
  alta: 'bg-red-50 border-red-200 text-red-700',
  media: 'bg-yellow-50 border-yellow-200 text-yellow-700',
  baja: 'bg-green-50 border-green-200 text-green-700'
}

const prioridadBadge = {
  alta: 'bg-red-100 text-red-700',
  media: 'bg-yellow-100 text-yellow-700',
  baja: 'bg-green-100 text-green-700'
}

const tipoIcon = {
  rodaje: '🏃',
  recuperacion: '🧘',
  intervalos: '⚡',
  descanso: '😴'
}

const formatearFecha = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const RecomendacionModal = ({ rec, onClose }) => (
  <div
    className="fixed inset-0 flex items-end justify-center z-50 p-4"
    style={{ backgroundColor: 'rgba(255,255,255,0.4)' }}
  >
    <div className="bg-white rounded-2xl w-full max-w-sm shadow-2xl">
      <div className="p-5 border-b border-gray-100 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{tipoIcon[rec.tipo] || '🏃'}</span>
          <div>
            <p className="font-bold text-gray-800 capitalize">{rec.tipo}</p>
            <p className="text-xs text-gray-400">{formatearFecha(rec.generadoEn)}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition"
        >
          x
        </button>
      </div>

      <div className="p-5 space-y-4">
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${prioridadBadge[rec.prioridad] || prioridadBadge.media}`}>
          Prioridad {rec.prioridad}
        </span>

        <p className="text-gray-700 text-sm leading-relaxed">{rec.mensaje}</p>

        {rec.alerta && (
          <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-3">
            <p className="text-yellow-800 font-semibold text-xs mb-1">Alerta</p>
            <p className="text-yellow-700 text-xs">{rec.alerta}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 pt-2">
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <p className="text-lg font-bold text-blue-600">{rec.kmSemanaActual}</p>
            <p className="text-xs text-gray-500">km esta semana</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <p className="text-lg font-bold text-gray-400">{rec.kmSemanaAnterior}</p>
            <p className="text-xs text-gray-500">km semana anterior</p>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-gray-100">
        <button
          onClick={onClose}
          className="w-full bg-gray-100 text-gray-600 py-3 rounded-xl text-sm font-semibold hover:bg-gray-200 transition"
        >
          Cerrar
        </button>
      </div>
    </div>
  </div>
)

const Recomendacion = () => {
  const { user } = useAuth()
  const [recomendacion, setRecomendacion] = useState(null)
  const [historial, setHistorial] = useState([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [selectedRec, setSelectedRec] = useState(null)

  const fetchData = async () => {
    
    try {
      const [recRes, histRes] = await Promise.all([
        getRecommendation(user.uid),
        getRecommendations(user.uid)
      ])
     
      if (recRes.data?.tipo) setRecomendacion(recRes.data)
      setHistorial(Array.isArray(histRes.data?.recommendations) ? histRes.data.recommendations : [])
    } catch (err) {
      console.log('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [user.uid])

  const handleAnalizar = async () => {
    setError('')
    setAnalyzing(true)
    try {
      const res = await analyzeWithAgent(user.uid)
      setRecomendacion(res.data)
      await fetchData()
    } catch (err) {
      console.log('Error:', err)
      setError('Error al generar recomendacion. Intenta de nuevo.')
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-blue-600 text-lg">Cargando...</div>
    </div>
  )

  return (
    <div className="p-4 max-w-lg mx-auto">

      {selectedRec && (
        <RecomendacionModal
          rec={selectedRec}
          onClose={() => setSelectedRec(null)}
        />
      )}

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold text-gray-800">RunCoach IA</h1>
      </div>

      <button
        onClick={handleAnalizar}
        disabled={analyzing}
        className="w-full bg-blue-600 text-white py-4 rounded-2xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition mb-6"
      >
        {analyzing ? 'Analizando tu historial...' : 'Generar nueva recomendacion'}
      </button>

      {error && (
        <p className="text-red-500 text-sm text-center mb-4">{error}</p>
      )}

      {recomendacion ? (
        <div className="space-y-4 mb-6">
          <div className={`rounded-2xl border p-5 ${prioridadColor[recomendacion.prioridad] || prioridadColor.media}`}>
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">{tipoIcon[recomendacion.tipo] || '🏃'}</span>
              <div>
                <p className="font-bold text-gray-800 capitalize">{recomendacion.tipo}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${prioridadBadge[recomendacion.prioridad] || prioridadBadge.media}`}>
                  Prioridad {recomendacion.prioridad}
                </span>
              </div>
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">{recomendacion.mensaje}</p>
          </div>

          {recomendacion.alerta && (
            <div className="bg-yellow-50 border border-yellow-300 rounded-2xl p-4">
              <p className="text-yellow-800 font-semibold text-sm mb-1">Alerta</p>
              <p className="text-yellow-700 text-sm">{recomendacion.alerta}</p>
            </div>
          )}

          <div className="bg-white rounded-2xl shadow-sm p-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">{recomendacion.kmSemanaActual}</p>
                <p className="text-xs text-gray-500">km esta semana</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-400">{recomendacion.kmSemanaAnterior}</p>
                <p className="text-xs text-gray-500">km semana anterior</p>
              </div>
            </div>
          </div>

          <p className="text-xs text-gray-400 text-center">
            Generado el {formatearFecha(recomendacion.generadoEn)}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center mb-6">
          <p className="text-4xl mb-3">🤖</p>
          <p className="text-gray-500 text-sm">
            Presiona el boton para que el agente analice tu historial y genere una recomendacion personalizada.
          </p>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-sm p-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Historial de recomendaciones
        </h2>
        {historial.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-4">
            Aun no tienes recomendaciones generadas
          </p>
        ) : (
          <div className="space-y-2">
            {historial.map((rec, i) => (
              <button
                key={rec.id || i}
                onClick={() => setSelectedRec(rec)}
                className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 transition text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{tipoIcon[rec.tipo] || '🏃'}</span>
                  <div>
                    <p className="text-sm font-medium text-gray-700 capitalize">{rec.tipo}</p>
                    <p className="text-xs text-gray-400">{formatearFecha(rec.generadoEn)}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${prioridadBadge[rec.prioridad] || prioridadBadge.media}`}>
                  {rec.prioridad}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

    </div>
  )
}

export default Recomendacion