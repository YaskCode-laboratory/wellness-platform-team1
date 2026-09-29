/**
 * Comparativa en vivo entre el modo legacy y el modo RAG.
 *
 * Ejecuta ambas arquitecturas sobre el MISMO estado del corredor y muestra las
 * dos respuestas lado a lado, con sus latencias y las fuentes que cada una
 * pudo citar.
 *
 * El modo dual se construyo en el Sprint 1 como valor agregado del equipo y
 * hasta ahora solo se podia observar con curl: el frontend nunca envio el
 * parametro. Esta pantalla es lo que lo vuelve demostrable.
 *
 * La diferencia que hace visible no es de estilo sino de trazabilidad: el modo
 * legacy responde desde conocimiento embebido en el prompt y no puede citar
 * nada; el modo RAG recupera de la knowledge base curada y declara de donde
 * sale cada afirmacion.
 */

import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { compareAgentModes } from '../services/api'
import IsoCorriendo from './IsoCorriendo'

const ms = (valor) => `${(valor / 1000).toFixed(1)} s`

const Columna = ({ titulo, subtitulo, datos, acento }) => {
  const rec = datos?.recomendacion || {}
  return (
    <div className={`runcoach-destello-anillo rounded-2xl border p-4 ${acento}`}>
      <p className="text-sm font-semibold text-gray-800">{titulo}</p>
      <p className="text-[11px] text-gray-500 mb-3">{subtitulo}</p>

      <p className="text-sm text-gray-700 leading-relaxed">{rec.mensaje}</p>

      {rec.alerta && (
        <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded-xl p-2.5">
          <p className="text-[11px] text-yellow-800 font-semibold mb-0.5">Alerta</p>
          <p className="text-xs text-yellow-700">{rec.alerta}</p>
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-gray-200 space-y-1 text-[11px] text-gray-500">
        <p>Tipo: <span className="capitalize text-gray-700">{rec.tipo}</span></p>
        <p>Latencia: <span className="text-gray-700">{ms(datos?.latenciaMs || 0)}</span></p>
        <p>
          Fuentes:{' '}
          {datos?.fuentes?.length > 0 ? (
            <span className="text-gray-700">{[...new Set(datos.fuentes)].join(', ')}</span>
          ) : (
            <span className="text-gray-400">ninguna — no puede citar</span>
          )}
        </p>
      </div>
    </div>
  )
}

/**
 * El resultado se recibe y se eleva por props en vez de vivir aqui, para que
 * sobreviva al cambio de pestana: el componente se desmonta al salir de
 * Comparativa y su estado local se perderia.
 *
 * No se persiste mas alla de la sesion. El endpoint /compare no guarda nada
 * por diseno -- es una operacion de demostracion, no produce una
 * recomendacion que archivar -- y mostrar una comparativa vieja tras recargar
 * seria enganoso: el estado del corredor pudo cambiar entre medias, y toda la
 * gracia de esta pantalla es que ambas arquitecturas vieron EL MISMO estado.
 */
const ComparativaModos = ({ datos, onDatos }) => {
  const { user } = useAuth()
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const comparar = async () => {
    setError('')
    setCargando(true)
    try {
      const res = await compareAgentModes(user.uid)
      onDatos(res.data)
    } catch (err) {
      console.log('Error:', err)
      setError('No se pudo ejecutar la comparativa. Intenta de nuevo.')
    } finally {
      setCargando(false)
    }
  }

  const estado = datos?.estadoCorredor
  const delta = datos?.delta

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl shadow-sm p-4">
        <p className="text-sm text-gray-700 mb-1">Comparativa de arquitecturas</p>
        <p className="text-xs text-gray-500 leading-relaxed mb-3">
          Ejecuta los dos modos sobre el mismo estado del corredor: el legacy responde
          desde conocimiento embebido en el prompt, el RAG recupera de la knowledge base
          curada y cita sus fuentes.
        </p>
        <button
          onClick={comparar}
          disabled={cargando}
          className="w-full bg-gray-800 text-white py-3 rounded-xl text-sm font-semibold hover:bg-gray-900 disabled:opacity-50 transition"
        >
          {cargando ? 'Ejecutando ambos modos…' : 'Comparar legacy vs RAG'}
        </button>
        {error && <p className="text-red-500 text-xs text-center mt-3">{error}</p>}
      </div>

      {cargando && (
        <div className="bg-white rounded-2xl shadow-sm p-5 flex items-center gap-3 pl-8">
          <IsoCorriendo />
          <span className="runcoach-latido text-sm text-gray-400">
            Ejecutando ambas arquitecturas sobre el mismo estado…
          </span>
        </div>
      )}

      {estado && (
        <div className="bg-white rounded-2xl shadow-sm p-4">
          <div className="flex justify-between items-baseline mb-2">
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">
              Mismo estado para ambos modos
            </p>
            {datos?.generadoEn && (
              <p className="text-[11px] text-gray-400">
                {new Date(datos.generadoEn).toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            )}
          </div>
          <div className="grid grid-cols-4 gap-2 text-center">
            <div>
              <p className="text-lg font-bold text-blue-600">{estado.kmSemanaActual}</p>
              <p className="text-[11px] text-gray-500">km esta semana</p>
            </div>
            <div>
              <p className="text-lg font-bold text-gray-400">{estado.kmSemanaAnterior}</p>
              <p className="text-[11px] text-gray-500">km semana previa</p>
            </div>
            <div>
              <p className="text-lg font-bold text-gray-700">{estado.variacionPct}%</p>
              <p className="text-[11px] text-gray-500">variación</p>
            </div>
            <div>
              <p className="text-lg font-bold text-gray-700 capitalize">{estado.nivel}</p>
              <p className="text-[11px] text-gray-500">nivel</p>
            </div>
          </div>
        </div>
      )}

      {/*
        La key remonta las columnas en cada comparacion, que es lo que vuelve
        a disparar el destello: una animacion CSS no se repite sobre el mismo
        nodo aunque cambie su contenido.
      */}
      {datos && (
        <div className="space-y-3" key={datos.generadoEn}>
          <Columna
            titulo="Legacy"
            subtitulo="Prompt estático, conocimiento embebido en el código"
            datos={datos.legacy}
            acento="bg-red-50 border-red-200"
          />
          <Columna
            titulo="RAG"
            subtitulo="Recuperación sobre la knowledge base curada"
            datos={datos.rag}
            acento="bg-blue-50 border-blue-200"
          />

          {delta && (
            <div className="bg-white rounded-2xl shadow-sm p-4">
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-2">
                Diferencia
              </p>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div>
                  <p className="text-lg font-bold text-gray-700">
                    {delta.latenciaMs > 0 ? '+' : ''}{ms(delta.latenciaMs)}
                  </p>
                  <p className="text-[11px] text-gray-500">costo del RAG</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-gray-700">{delta.documentosConsultados}</p>
                  <p className="text-[11px] text-gray-500">documentos citados</p>
                </div>
              </div>
            </div>
          )}

          {datos.rag?.chunksRecuperados?.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm p-4">
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-2">
                Qué recuperó el modo RAG
              </p>
              <p className="text-xs text-gray-500 italic mb-2">
                consulta: «{datos.rag.consultaRecuperacion}»
              </p>
              <div className="space-y-2">
                {datos.rag.chunksRecuperados.map((c, i) => (
                  <div key={i} className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2">
                    <span className="text-gray-400">{c.doc_id || c.docId}</span>{' '}
                    {c.titulo}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ComparativaModos
