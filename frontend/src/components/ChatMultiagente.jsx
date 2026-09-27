/**
 * Conversacion con el sistema multiagente.
 *
 * Envia cada mensaje al orquestador, que decide a que agente especializado
 * delegar. Cada respuesta se etiqueta con los agentes que intervinieron y
 * lleva su traza desplegable.
 *
 * LA MEMORIA VIVE EN FIRESTORE, NO AQUI
 *
 * La memoria conversacional del Wellness Coach se persiste desde el issue
 * S2-03 y sobrevive a recargas y a cierres de sesion. La primera version de
 * esta pantalla mantenia los mensajes solo en el estado del componente, con un
 * efecto desconcertante: al cambiar de pestana el chat aparecia vacio y el
 * agente seguia recordando lo hablado.
 *
 * Ahora el historial se carga al montar. Los turnos recuperados se muestran
 * sin traza porque las trazas se registran por solicitud, no por turno: una
 * conversacion reabierta ensena que se dijo, no como se resolvio cada
 * delegacion. Eso ultimo vive en la coleccion 'delegaciones'.
 */

import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { chatWithOrchestrator, getChatHistory } from '../services/api'
import TrazaPanel, { agenteInfo } from './TrazaPanel'
import IsoCorriendo from './IsoCorriendo'
import logoMini from '../assets/runcoachlogomini.png'

const SUGERENCIAS = [
  '¿Cómo voy esta semana respecto a mi meta?',
  '¿Cuánta agua debo tomar mientras corro?',
  '¿Qué como antes de una tirada larga y cómo ajusto el entrenamiento?',
]

const EtiquetasAgentes = ({ traza }) => {
  if (!traza?.agentes?.length) return null

  return (
    <div className="flex flex-wrap gap-1.5 mb-1.5">
      {traza.agentes.map((nombre) => {
        const info = agenteInfo(nombre)
        return (
          <span
            key={nombre}
            className={`text-[11px] px-2 py-0.5 rounded-full border ${info.color}`}
          >
            {info.etiqueta}
          </span>
        )
      })}
      {traza.colaboracion && (
        <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
          colaboración
        </span>
      )}
      {traza.degradado && (
        <span className="text-[11px] px-2 py-0.5 rounded-full bg-yellow-50 text-yellow-700 border border-yellow-200">
          degradado
        </span>
      )}
    </div>
  )
}

/**
 * Indicador de espera.
 *
 * Una conversacion multiagente puede tardar veinte segundos o mas: la
 * clasificacion, el agente y, si colaboran, el segundo agente encadenado. Un
 * texto estatico durante ese rato parece que la aplicacion se colgo, asi que
 * el logo late y los puntos avanzan para que se vea que sigue trabajando.
 */
const Pensando = () => (
  <div className="max-w-[92%]">
    <div className="bg-white shadow-sm rounded-2xl rounded-bl-md pl-8 pr-4 py-3 flex items-center gap-3">
      <IsoCorriendo />
      <span className="runcoach-latido text-sm text-gray-400">
        Consultando a tus especialistas…
      </span>
    </div>
  </div>
)

/**
 * Renderiza la respuesta respetando los encabezados que pone el orquestador
 * cuando colaboran varios agentes. No se reformatea el texto: el orquestador
 * no parafrasea a los agentes para no romper la correspondencia entre
 * afirmacion y fuente, y el frontend mantiene ese principio.
 */
const Respuesta = ({ texto }) =>
  texto.split('\n').map((linea, i) => {
    const encabezado = linea.match(/^\*\*(.+)\*\*$/)
    if (encabezado) {
      return (
        <p key={i} className="text-[11px] text-gray-400 uppercase tracking-wide mt-3 first:mt-0">
          {encabezado[1]}
        </p>
      )
    }
    if (!linea.trim()) return null
    return (
      <p key={i} className="text-sm text-gray-700 leading-relaxed mt-1">
        {linea}
      </p>
    )
  })

const ChatMultiagente = () => {
  const { user } = useAuth()
  const [mensajes, setMensajes] = useState([])
  const [entrada, setEntrada] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const finRef = useRef(null)

  useEffect(() => {
    const cargarHistorial = async () => {
      try {
        const res = await getChatHistory(user.uid)
        const turnos = (res.data?.turnos || []).map((t) => ({
          rol: t.rol === 'usuario' ? 'usuario' : 'agente',
          texto: t.contenido,
          recuperado: true,
        }))
        setMensajes(turnos)
      } catch (err) {
        console.log('Error al cargar el historial:', err)
      } finally {
        setCargando(false)
      }
    }
    cargarHistorial()
  }, [user.uid])

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, enviando])

  const enviar = async (texto) => {
    const mensaje = (texto ?? entrada).trim()
    if (!mensaje || enviando) return

    setError('')
    setEntrada('')
    setMensajes((previos) => [...previos, { rol: 'usuario', texto: mensaje }])
    setEnviando(true)

    try {
      const res = await chatWithOrchestrator(user.uid, mensaje)
      setMensajes((previos) => [
        ...previos,
        { rol: 'agente', texto: res.data.respuesta, traza: res.data },
      ])
    } catch (err) {
      console.log('Error:', err)
      // El detalle del backend se muestra tal cual. Un mensaje generico es
      // adecuado para el corredor pero inservible cuando algo falla durante
      // una demostracion: ahi hace falta saber que fallo, no que reintente.
      const detalle =
        err.response?.data?.detail ||
        (err.response ? `${err.response.status} ${err.response.statusText}` : err.message)
      setError(detalle)
      setMensajes((previos) => [
        ...previos,
        {
          rol: 'agente',
          texto: 'No pude completar tu consulta en este momento.',
          error: true,
        },
      ])
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div>
      {mensajes.length > 0 && (
        <p className="text-[11px] text-gray-400 mb-3">
          El coach recuerda esta conversación entre sesiones
        </p>
      )}

      {/*
        El espacio inferior deja sitio a la barra de escritura, que esta fija
        sobre la navegacion: sin el, los ultimos mensajes quedarian tapados.
      */}
      <div className="space-y-4" style={{ paddingBottom: '5.5rem', minHeight: '55vh' }}>
        {cargando && (
          <p className="text-sm text-gray-400 text-center py-8">Cargando conversación…</p>
        )}

        {!cargando && mensajes.length === 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-6 text-center">
            <img src={logoMini} alt="" className="h-9 w-auto object-contain mx-auto mb-3" />
            <p className="text-gray-500 text-sm mb-4">
              Pregúntale a tu coach sobre entrenamiento o alimentación. Si tu consulta
              toca ambos temas, responderán los dos especialistas.
            </p>
            <div className="space-y-2">
              {SUGERENCIAS.map((s) => (
                <button
                  key={s}
                  onClick={() => enviar(s)}
                  className="w-full text-left text-xs text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-xl px-3 py-2 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {mensajes.map((m, i) =>
          m.rol === 'usuario' ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5">
                <p className="text-sm leading-relaxed">{m.texto}</p>
              </div>
            </div>
          ) : (
            <div key={i} className="max-w-[92%]">
              <EtiquetasAgentes traza={m.traza} />
              <div
                className={`rounded-2xl rounded-bl-md px-4 py-3 ${
                  m.error ? 'bg-red-50 border border-red-200' : 'bg-white shadow-sm'
                }`}
              >
                <Respuesta texto={m.texto} />
              </div>
              <TrazaPanel traza={m.traza} />
            </div>
          )
        )}

        {enviando && <Pensando />}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3">
            <p className="text-[11px] text-red-500 uppercase tracking-wide mb-1">
              Detalle del error
            </p>
            <p className="text-xs text-red-700 font-mono break-all">{error}</p>
          </div>
        )}

        <div ref={finRef} />
      </div>

      {/*
        Barra de escritura fija justo encima de la navegacion inferior, que
        mide 4rem. Fija y no sticky: con sticky la caja flotaba a media
        pantalla cuando la conversacion era corta.
      */}
      <div className="fixed bottom-16 left-0 right-0 z-30 bg-gray-50 border-t border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-3">
          <div className="flex gap-2 items-end">
            <textarea
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  enviar()
                }
              }}
              rows={1}
              placeholder="Pregúntale a tu coach…"
              className="flex-1 resize-none bg-white border border-gray-200 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-blue-400 transition"
            />
            <button
              onClick={() => enviar()}
              disabled={enviando || !entrada.trim()}
              className="flex-none w-11 h-11 rounded-full bg-blue-600 text-white disabled:opacity-40 hover:bg-blue-700 transition"
              aria-label="Enviar"
            >
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatMultiagente
