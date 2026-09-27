/**
 * RunCoach IA — punto de entrada a las capacidades de inteligencia artificial.
 *
 * Tres pestanas sobre la misma pantalla, que corresponden a los tres sprints:
 *
 *   Chat         sistema multiagente con orquestador (Sprint 3)
 *   Recomendacion  agente de un turno, con selector de modo (Sprints 1 y 2)
 *   Comparativa  legacy vs RAG sobre el mismo estado (Sprint 1)
 *
 * Se agrupan aqui en vez de anadir entradas a la navegacion inferior para no
 * tocar el resto de la aplicacion: la barra ya tiene cinco elementos y este
 * cambio no deberia reorganizar la navegacion de la PWA.
 */

import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  analyzeWithAgent,
  clearChatHistory,
  getRecommendation,
  getRecommendations,
} from '../services/api'
import ChatMultiagente from '../components/ChatMultiagente'
import ComparativaModos from '../components/ComparativaModos'
import IsoCorriendo from '../components/IsoCorriendo'
import logoMini from '../assets/runcoachlogomini.png'

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

const PESTANAS = [
  { id: 'chat', label: 'Chat' },
  { id: 'recomendacion', label: 'Recomendación' },
  { id: 'comparativa', label: 'Comparativa' },
]

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
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${prioridadBadge[rec.prioridad] || prioridadBadge.media}`}>
            Prioridad {rec.prioridad}
          </span>
          {rec.modo && (
            <span className="text-xs px-2 py-1 rounded-full font-medium bg-gray-100 text-gray-600">
              modo {rec.modo}
            </span>
          )}
        </div>

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

const SelectorModo = ({ modo, onChange, deshabilitado }) => (
  <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
    <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-2">
      Arquitectura de la recomendación
    </p>
    <div className="flex gap-2">
      {[
        { id: 'rag', label: 'RAG', detalle: 'fundamentada en la base de conocimiento' },
        { id: 'legacy', label: 'Legacy', detalle: 'prompt estático, sin recuperación' },
      ].map((opcion) => (
        <button
          key={opcion.id}
          onClick={() => onChange(opcion.id)}
          disabled={deshabilitado}
          className={`flex-1 text-left rounded-xl border p-3 transition disabled:opacity-50 ${
            modo === opcion.id
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <p className={`text-sm font-semibold ${modo === opcion.id ? 'text-blue-700' : 'text-gray-700'}`}>
            {opcion.label}
          </p>
          <p className="text-[11px] text-gray-500 leading-snug mt-0.5">{opcion.detalle}</p>
        </button>
      ))}
    </div>
  </div>
)

const PanelRecomendacion = () => {
  const { user } = useAuth()
  // Una recomendacion por arquitectura, no una sola compartida. Son productos
  // de dos sistemas distintos sobre el mismo estado del corredor: mostrar la
  // de RAG mientras el selector marca legacy haria creer que legacy la
  // produjo, que es justo lo contrario de lo que esta pantalla quiere
  // demostrar.
  const [porModo, setPorModo] = useState({ rag: null, legacy: null })
  const [historial, setHistorial] = useState([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [selectedRec, setSelectedRec] = useState(null)
  const [modo, setModo] = useState('rag')

  const recomendacion = porModo[modo]

  const fetchData = async () => {
    try {
      const [recRes, histRes] = await Promise.all([
        getRecommendation(user.uid),
        getRecommendations(user.uid)
      ])

      const lista = Array.isArray(histRes.data?.recommendations)
        ? histRes.data.recommendations
        : []
      setHistorial(lista)

      // Los dos casilleros se derivan del historial completo, no solo de la
      // ultima recomendacion. Con lo segundo, al recargar la pagina se
      // recuperaba la mas reciente y la de la otra arquitectura desaparecia
      // aunque siguiera existiendo en la lista de abajo.
      //
      // Las recomendaciones anteriores al Sprint 3 no traen 'modo' porque el
      // campo no existia: se asumen RAG, que era el modo por defecto del
      // endpoint.
      const candidatas = [recRes.data?.tipo ? recRes.data : null, ...lista].filter(Boolean)
      const masReciente = { rag: null, legacy: null }

      for (const rec of candidatas) {
        const suModo = rec.modo === 'legacy' ? 'legacy' : 'rag'
        const actual = masReciente[suModo]
        if (!actual || String(rec.generadoEn) > String(actual.generadoEn)) {
          masReciente[suModo] = rec
        }
      }

      setPorModo(masReciente)
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
      const res = await analyzeWithAgent(user.uid, modo)
      setPorModo((previos) => ({ ...previos, [modo]: res.data }))
      await fetchData()
    } catch (err) {
      console.log('Error:', err)
      setError('Error al generar recomendacion. Intenta de nuevo.')
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <div className="text-blue-600 text-sm">Cargando...</div>
    </div>
  )

  return (
    <>
      {selectedRec && (
        <RecomendacionModal rec={selectedRec} onClose={() => setSelectedRec(null)} />
      )}

      <SelectorModo modo={modo} onChange={setModo} deshabilitado={analyzing} />

      <button
        onClick={handleAnalizar}
        disabled={analyzing}
        className="w-full bg-blue-600 text-white py-4 rounded-2xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition mb-6"
      >
        {analyzing ? 'Analizando tu historial…' : `Generar recomendación en modo ${modo}`}
      </button>

      {error && <p className="text-red-500 text-sm text-center mb-4">{error}</p>}

      {analyzing && (
        <div className="bg-white rounded-2xl shadow-sm p-5 mb-6 flex items-center gap-3 pl-8">
          <IsoCorriendo />
          <span className="runcoach-latido text-sm text-gray-400">
            Analizando tu historial en modo {modo}…
          </span>
        </div>
      )}

      {analyzing ? null : recomendacion ? (
        <div className="space-y-4 mb-6">
          {/*
            La key hace que React remonte la tarjeta cuando llega una
            recomendacion distinta, que es lo que vuelve a disparar el
            destello: una animacion no se repite sobre el mismo nodo.
          */}
          <div
            key={recomendacion.id || recomendacion.generadoEn}
            className={`runcoach-destello-anillo rounded-2xl border p-5 ${prioridadColor[recomendacion.prioridad] || prioridadColor.media}`}
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">{tipoIcon[recomendacion.tipo] || '🏃'}</span>
              <div>
                <p className="font-bold text-gray-800 capitalize">{recomendacion.tipo}</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${prioridadBadge[recomendacion.prioridad] || prioridadBadge.media}`}>
                    Prioridad {recomendacion.prioridad}
                  </span>
                  {recomendacion.modo && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-white/70 text-gray-600">
                      modo {recomendacion.modo}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">{recomendacion.mensaje}</p>
          </div>

          {recomendacion.fuentes?.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm p-4">
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-1">
                Fundamentada en
              </p>
              <p className="text-xs text-gray-600">
                {[...new Set(recomendacion.fuentes)].join(', ')}
              </p>
            </div>
          )}

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
            {recomendacion.latenciaMs ? ` · ${(recomendacion.latenciaMs / 1000).toFixed(1)} s` : ''}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center mb-6">
          <img src={logoMini} alt="" className="h-9 w-auto object-contain mx-auto mb-4" />
          <p className="text-gray-700 text-sm font-medium mb-1">
            Todavía no hay una recomendación en modo {modo}
          </p>
          <p className="text-gray-500 text-sm">
            {porModo[modo === 'rag' ? 'legacy' : 'rag']
              ? `Ya generaste una con la otra arquitectura. Pulsa el botón para que el agente analice tu historial en modo ${modo} y puedas comparar.`
              : 'Pulsa el botón para que el agente analice tu historial y genere una recomendación personalizada.'}
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
                <div className="flex items-center gap-2">
                  {rec.modo && (
                    <span className="text-[11px] text-gray-400">{rec.modo}</span>
                  )}
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${prioridadBadge[rec.prioridad] || prioridadBadge.media}`}>
                    {rec.prioridad}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

const Recomendacion = () => {
  const { user } = useAuth()
  const [pestana, setPestana] = useState('chat')
  // Reiniciar la conversacion desmonta y vuelve a montar el chat cambiando su
  // key. Asi el componente recarga el historial -- ahora vacio -- por el mismo
  // camino que usa al abrirse, en vez de tener dos formas distintas de llegar
  // al mismo estado.
  const [claveChat, setClaveChat] = useState(0)
  const [reiniciando, setReiniciando] = useState(false)
  // La comparativa vive aqui y no en su componente para que sobreviva al
  // cambio de pestana. No se persiste mas alla de la sesion: /compare no
  // guarda nada por diseno, y una comparativa vieja tras recargar seria
  // enganosa porque el estado del corredor pudo cambiar entre medias.
  const [comparativa, setComparativa] = useState(null)

  const reiniciarConversacion = async () => {
    if (reiniciando) return
    setReiniciando(true)
    try {
      await clearChatHistory(user.uid)
      setClaveChat((k) => k + 1)
    } catch (err) {
      console.log('Error al reiniciar:', err)
    } finally {
      setReiniciando(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      {/*
        Cabecera fija. El chat puede crecer mucho y obligaba a subir hasta
        arriba para cambiar de pestana o reiniciar la conversacion, que es
        justo lo que hace falta a mano durante una demostracion.
      */}
      <div className="sticky top-0 z-30 bg-gray-50 px-4 pt-4 pb-3 border-b border-gray-100">
        <div className="flex justify-between items-center mb-3">
          <h1 className="text-xl font-bold text-gray-800">RunCoach IA</h1>
          {pestana === 'chat' && (
            <button
              onClick={reiniciarConversacion}
              disabled={reiniciando}
              className="text-[11px] text-gray-400 hover:text-red-500 disabled:opacity-50 transition"
            >
              {reiniciando ? 'reiniciando…' : 'reiniciar conversación'}
            </button>
          )}
        </div>

        <div className="flex bg-white rounded-2xl shadow-sm p-1">
          {PESTANAS.map((p) => (
            <button
              key={p.id}
              onClick={() => setPestana(p.id)}
              className={`flex-1 text-xs py-2 rounded-xl transition ${
                pestana === p.id
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 pt-4 pb-4">
        {pestana === 'chat' && <ChatMultiagente key={claveChat} />}
        {pestana === 'recomendacion' && <PanelRecomendacion />}
        {pestana === 'comparativa' && (
          <ComparativaModos datos={comparativa} onDatos={setComparativa} />
        )}
      </div>
    </div>
  )
}

export default Recomendacion
