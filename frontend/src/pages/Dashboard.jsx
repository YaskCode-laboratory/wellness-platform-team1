import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getWeeklyMetrics, getGoalProgress, getAlerts, getUser } from '../services/api'
import logoMax from '../assets/runcoachlogomax.png'
import logoMini from '../assets/runcoachlogomini.png'
import newSessionIcon from '../assets/new_session.png'
import iaIcon from '../assets/ia_recommendations.png'
import timerIcon from '../assets/timer.png'


const formatearRitmo = (ritmoDecimal) => {
  if (!ritmoDecimal) return '--'
  const minutos = Math.floor(ritmoDecimal)
  const segundos = Math.round((ritmoDecimal - minutos) * 60)
  return `${minutos}:${segundos.toString().padStart(2, '0')}`
}

const formatearTiempo = (totalSegundos) => {
  const h = Math.floor(totalSegundos / 3600)
  const m = Math.floor((totalSegundos % 3600) / 60)
  const s = totalSegundos % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  return `${m}m ${s}s`
}

// ── Modal Calculadora ─────────────────────────────
const CalculadoraModal = ({ onClose }) => {
  const [tab, setTab] = useState('ritmo')
  const [distancia, setDistancia] = useState('')
  const [horas, setHoras] = useState('')
  const [minutos, setMinutos] = useState('')
  const [segundos, setSegundos] = useState('')
  const [ritmoH, setRitmoH] = useState('')
  const [ritmoM, setRitmoM] = useState('')
  const [ritmoS, setRitmoS] = useState('')
  const [resultado, setResultado] = useState(null)

  const calcularRitmo = () => {
    const dist = parseFloat(distancia)
    const totalSeg = (parseFloat(horas || 0) * 3600) + (parseFloat(minutos || 0) * 60) + parseFloat(segundos || 0)
    if (!dist || !totalSeg) return
    const ritmoSeg = totalSeg / dist
    const rMin = Math.floor(ritmoSeg / 60)
    const rSeg = Math.round(ritmoSeg % 60)
    setResultado({
      label: 'Ritmo necesario',
      valor: `${rMin}:${rSeg.toString().padStart(2, '0')} min/km`,
      detalle: `Para correr ${dist} km en ${formatearTiempo(totalSeg)}`
    })
  }

  const calcularTiempo = () => {
    const dist = parseFloat(distancia)
    const ritmoTotalSeg = (parseFloat(ritmoH || 0) * 3600) + (parseFloat(ritmoM || 0) * 60) + parseFloat(ritmoS || 0)
    if (!dist || !ritmoTotalSeg) return
    const totalSeg = Math.round(ritmoTotalSeg * dist)
    setResultado({
      label: 'Tiempo estimado',
      valor: formatearTiempo(totalSeg),
      detalle: `Corriendo ${dist} km a ${ritmoM || 0}:${(ritmoS || 0).toString().padStart(2, '0')} min/km`
    })
  }

  const inputClass = "w-full border border-gray-300 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"

  return (
    <div className="fixed inset-0 flex items-end justify-center z-50 p-4" style={{ backgroundColor: 'rgba(255,255,255,0.4)' }}>
      <div className="bg-white rounded-2xl w-full max-w-sm shadow-2xl">

        <div className="flex justify-between items-center p-5 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-800">Calculadora de ritmo</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition">
            x
          </button>
        </div>

        <div className="flex gap-2 p-4 pb-0">
          <button
            onClick={() => { setTab('ritmo'); setResultado(null) }}
            className={`flex-1 py-2 rounded-xl text-sm font-semibold transition ${tab === 'ritmo' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}
          >
            Calcular ritmo
          </button>
          <button
            onClick={() => { setTab('tiempo'); setResultado(null) }}
            className={`flex-1 py-2 rounded-xl text-sm font-semibold transition ${tab === 'tiempo' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}
          >
            Calcular tiempo
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Distancia (km)</label>
            <input
              type="number"
              value={distancia}
              onChange={(e) => { setDistancia(e.target.value); setResultado(null) }}
              className={inputClass}
              placeholder="Ej: 10"
              step="0.1"
              min="0"
            />
          </div>

          {tab === 'ritmo' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tiempo objetivo</label>
              <div className="flex gap-2">
                <div className="flex-1">
                  <input type="number" value={horas} onChange={(e) => { setHoras(e.target.value); setResultado(null) }} className={inputClass} placeholder="0" min="0" />
                  <p className="text-xs text-gray-400 mt-1 text-center">horas</p>
                </div>
                <div className="flex-1">
                  <input type="number" value={minutos} onChange={(e) => { setMinutos(e.target.value); setResultado(null) }} className={inputClass} placeholder="0" min="0" max="59" />
                  <p className="text-xs text-gray-400 mt-1 text-center">min</p>
                </div>
                <div className="flex-1">
                  <input type="number" value={segundos} onChange={(e) => { setSegundos(e.target.value); setResultado(null) }} className={inputClass} placeholder="0" min="0" max="59" />
                  <p className="text-xs text-gray-400 mt-1 text-center">seg</p>
                </div>
              </div>
            </div>
          )}

          {tab === 'tiempo' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ritmo objetivo (min/km)</label>
              <div className="flex gap-2">
                <div className="flex-1">
                  <input type="number" value={ritmoM} onChange={(e) => { setRitmoM(e.target.value); setResultado(null) }} className={inputClass} placeholder="0" min="0" />
                  <p className="text-xs text-gray-400 mt-1 text-center">min</p>
                </div>
                <div className="flex-1">
                  <input type="number" value={ritmoS} onChange={(e) => { setRitmoS(e.target.value); setResultado(null) }} className={inputClass} placeholder="0" min="0" max="59" />
                  <p className="text-xs text-gray-400 mt-1 text-center">seg</p>
                </div>
              </div>
            </div>
          )}

          <button
            onClick={tab === 'ritmo' ? calcularRitmo : calcularTiempo}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition"
          >
            Calcular
          </button>

          {resultado && (
            <div className="bg-blue-50 rounded-2xl p-4 text-center">
              <p className="text-xs text-blue-500 font-medium mb-1">{resultado.label}</p>
              <p className="text-2xl font-bold text-blue-700">{resultado.valor}</p>
              <p className="text-xs text-gray-500 mt-1">{resultado.detalle}</p>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100">
          <button onClick={onClose} className="w-full bg-gray-100 text-gray-600 py-3 rounded-xl text-sm font-semibold hover:bg-gray-200 transition">
            Cerrar
          </button>
        </div>

      </div>
    </div>
  )
}

// ── Modal Notificaciones ──────────────────────────
const NotificacionesModal = ({ alerts, onClose, onVerIA }) => (
  <div
    className="fixed inset-0 flex items-start justify-end z-50 p-4 pt-16"
    style={{ backgroundColor: 'rgba(0,0,0,0.05)' }}
    onClick={onClose}
  >
    <div
      className="bg-white rounded-2xl w-72 shadow-2xl border border-gray-100"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex justify-between items-center p-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <img src={logoMini} alt="RunCoach" className="w-6 h-6 object-contain" />
          <h3 className="text-sm font-bold text-gray-800">Notificaciones</h3>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 w-6 h-6 flex items-center justify-center rounded-full hover:bg-gray-100 transition text-xs"
        >
          x
        </button>
      </div>
      <div className="p-3">
        {alerts.length === 0 ? (
          <p className="text-gray-400 text-xs text-center py-4">Sin notificaciones</p>
        ) : (
          alerts.map((alert, i) => (
            <button
              key={i}
              onClick={() => { onClose(); onVerIA() }}
              className="w-full text-left bg-yellow-50 border border-yellow-200 rounded-xl p-3 mb-2 hover:bg-yellow-100 transition"
            >
              <div className="flex items-center gap-2 mb-1">
                <img src={logoMini} alt="RunCoach" className="w-4 h-4 object-contain" />
                <p className="text-xs font-semibold text-yellow-800">Alerta de entrenamiento</p>
              </div>
              <p className="text-xs text-yellow-700 line-clamp-2">
                {alert.mensaje.length > 80 ? alert.mensaje.substring(0, 80) + '...' : alert.mensaje}
              </p>
              <p className="text-xs text-yellow-500 mt-1 font-medium">Ver recomendacion completa</p>
            </button>
          ))
        )}
      </div>
    </div>
  </div>
)

// ── Dashboard ─────────────────────────────────────
const Dashboard = () => {
  const { user, logout, darkMode, toggleDarkMode } = useAuth()
  const navigate = useNavigate()
  const [metrics, setMetrics] = useState(null)
  const [progress, setProgress] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [nombre, setNombre] = useState('')
  const [loading, setLoading] = useState(true)
  const [showCalculadora, setShowCalculadora] = useState(false)
  const [showNotificaciones, setShowNotificaciones] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [metricsRes, progressRes, alertsRes, userRes] = await Promise.all([
          getWeeklyMetrics(user.uid),
          getGoalProgress(user.uid),
          getAlerts(user.uid),
          getUser(user.uid)
        ])
        setMetrics(metricsRes.data)
        setProgress(progressRes.data)
        setAlerts(alertsRes.data?.alerts || [])
        setNombre(userRes.data?.nombre || '')
      } catch (err) {
        console.log('Error cargando datos:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [user.uid])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-blue-600 text-lg">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-lg mx-auto">

      {showCalculadora && <CalculadoraModal onClose={() => setShowCalculadora(false)} />}
      {showNotificaciones && (
        <NotificacionesModal
          alerts={alerts}
          onClose={() => setShowNotificaciones(false)}
          onVerIA={() => navigate('/recomendacion')}
        />
      )}

      {/* Status bar */}
      <div className="flex items-center justify-between mb-4">
        <Link to="/perfil">
          <div className="w-9 h-9 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold text-sm hover:bg-blue-700 transition">
            {nombre?.charAt(0)?.toUpperCase() || 'U'}
          </div>
        </Link>
        <img src={logoMax} alt="RunCoach AI" className="w-32 object-contain" />
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNotificaciones(!showNotificaciones)}
            className="relative w-9 h-9 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            {alerts.length > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </button>
          <button
            onClick={toggleDarkMode}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 transition"
          >
            {darkMode ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          <button
            onClick={logout}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-red-50 hover:bg-red-100 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>

      {/* Saludo */}
      <div className="text-center mb-5">
        <h1 className="text-xl font-bold text-gray-800">Hola, {nombre || 'corredor'}!</h1>
        <p className="text-sm text-gray-500">{user.email}</p>
      </div>

      {/* Metricas semanales */}
      <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Esta semana
        </h2>
        {metrics && metrics.kmTotales > 0 ? (
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{metrics.kmTotales?.toFixed(1)}</p>
              <p className="text-xs text-gray-500 mt-1">km totales</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{metrics.sesiones}</p>
              <p className="text-xs text-gray-500 mt-1">sesiones</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{formatearRitmo(metrics.ritmoPromedio)}</p>
              <p className="text-xs text-gray-500 mt-1">min/km</p>
            </div>
          </div>
        ) : (
          <p className="text-gray-400 text-sm text-center py-2">Sin entrenamientos esta semana</p>
        )}
      </div>

      {/* Progreso objetivos */}
      <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Mi objetivo
        </h2>
        {progress && progress.goals && progress.goals.length > 0 ? (
          <div className="space-y-3">
            {progress.goals.slice(0, 2).map((goal, i) => (
              <div key={i}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-600 capitalize">
                    {goal.tipo === 'semanal' 
                      ? `Semanal: ${goal.kmMeta} km` 
                      : `${goal.distanciaObjetivoKm} km${goal.tiempoObjetivoMin ? ` en ${Math.floor(goal.tiempoObjetivoMin/60)}h ${goal.tiempoObjetivoMin%60}m` : ''}${goal.descripcion ? `` : ''}`
                    }
                  </span>
                  <span className="text-gray-500">{goal.porcentajeCompletado}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${goal.porcentajeCompletado >= 100 ? 'bg-green-500' : 'bg-blue-600'}`}
                    style={{ width: `${Math.min(goal.porcentajeCompletado, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm text-center py-2">No tienes objetivos activos</p>
        )}
      </div>

      {/* Botonera de accesos rapidos */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <Link
          to="/nueva-sesion"
          className="bg-white border border-blue-200 text-blue-600 rounded-2xl p-4 text-center hover:bg-blue-50 transition block"
        >
          <img src={newSessionIcon} alt="Registrar" className="w-10 h-10 mx-auto mb-1 object-contain" />
          <p className="text-xs font-semibold">Registrar</p>
        </Link>
        <Link
          to="/recomendacion"
          className="bg-white border border-blue-200 text-blue-600 rounded-2xl p-4 text-center hover:bg-blue-50 transition block"
        >
          <img src={iaIcon} alt="IA" className="w-10 h-10 mx-auto mb-1 object-contain" />
          <p className="text-xs font-semibold">Ver IA</p>
        </Link>
        <button
          onClick={() => setShowCalculadora(true)}
          className="bg-white border border-purple-200 text-purple-600 rounded-2xl p-4 text-center hover:bg-purple-50 transition"
        >
          <img src={timerIcon} alt="Calcular" className="w-10 h-10 mx-auto mb-1 object-contain" />
          <p className="text-xs font-semibold">Calcular</p>
        </button>
      </div>

      {/* Feedback */}
      <button
        onClick={() => window.open('https://forms.gle/wxL5P9txNLRAgozS8', '_blank')}
        className="w-full bg-gray-100 text-gray-600 py-3 rounded-2xl text-sm font-medium hover:bg-gray-200 transition"
      >
        Reportar problema o sugerencia
      </button>

    </div>
  )
}

export default Dashboard