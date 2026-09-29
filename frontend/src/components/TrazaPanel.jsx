/**
 * Panel de traza de una respuesta del sistema multiagente.
 *
 * Muestra lo que el orquestador registro al atender una solicitud: que
 * intencion detecto y con que motivo, a que agentes delego, que le pidio
 * exactamente a cada uno, que consulto y cuanto tardo cada paso.
 *
 * Sin este panel la demo ensena un chatbot; con el ensena el sistema
 * multiagente. Es la respuesta visual al criterio de S3-06 sobre trazabilidad
 * suficiente para comprender el recorrido de una solicitud.
 */

import { useState } from 'react'

const AGENTES = {
  wellness_coach: { etiqueta: 'Wellness Coach', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  nutrition: { etiqueta: 'Nutrition', color: 'bg-purple-50 text-purple-700 border-purple-200' },
}

const MOTIVOS_NO_DELEGACION = {
  confianza_insuficiente: 'No delegó: la clasificación no era lo bastante confiable',
  fuera_de_dominio: 'No delegó: el tema está fuera del dominio de la plataforma',
  intencion_no_reconocida: 'No delegó: el mensaje no permitía identificar una intención',
  dominio_sin_agente: 'No delegó: el dominio aún no tiene un agente asignado',
  colaboracion_sin_agentes_suficientes: 'No delegó: la consulta mixta no resolvió dos agentes',
  delegacion_multiple_no_implementada: 'No delegó: la delegación múltiple no está disponible',
  intencion_sin_destino: 'No delegó: la intención no tiene destino registrado',
}

export const agenteInfo = (nombre) =>
  AGENTES[nombre] || { etiqueta: nombre, color: 'bg-gray-50 text-gray-600 border-gray-200' }

const ms = (valor) => `${(valor / 1000).toFixed(1)} s`

const Dato = ({ etiqueta, valor }) => (
  <div className="bg-gray-50 rounded-xl p-3">
    <p className="text-[11px] text-gray-900 uppercase tracking-wide font-medium">{etiqueta}</p>
    <p className="text-sm text-gray-700 mt-0.5">{valor}</p>
  </div>
)

const Paso = ({ paso }) => {
  const info = agenteInfo(paso.agente)
  return (
    <div className="flex gap-3">
      <span
        className={`flex-none w-6 h-6 rounded-full border text-[11px] flex items-center justify-center ${info.color}`}
      >
        {paso.paso}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-gray-700">
          {info.etiqueta} <span className="text-gray-400">· {ms(paso.latenciaMs)}</span>
        </p>
        <p className="text-xs text-gray-500 leading-relaxed mt-0.5">
          «{paso.mensajeDelegado}»
        </p>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 text-[11px] text-gray-400">
          {paso.fuentes?.length > 0 && <span>fuentes: {paso.fuentes.join(', ')}</span>}
          {paso.herramientasInvocadas?.length > 0 && (
            <span>herramientas: {paso.herramientasInvocadas.join(', ')}</span>
          )}
          {paso.degradado && <span className="text-yellow-600">degradado</span>}
        </div>
      </div>
    </div>
  )
}

const TrazaPanel = ({ traza }) => {
  const [abierto, setAbierto] = useState(false)

  if (!traza) return null

  const { latencias = {}, pasos = [] } = traza

  return (
    <div className="mt-1">
      <button
        onClick={() => setAbierto(!abierto)}
        className="flex items-center gap-2 text-[11px] text-gray-400 hover:text-gray-600 transition"
      >
        <span>{ms(latencias.totalMs || 0)}</span>
        {traza.fuentes?.length > 0 && <span>· {[...new Set(traza.fuentes)].join(', ')}</span>}
        <span className="text-blue-500">{abierto ? 'ocultar traza' : 'ver traza'}</span>
      </button>

      {abierto && (
        <div className="runcoach-destello mt-2 bg-white border border-gray-200 rounded-xl p-3 space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <Dato etiqueta="Intención" valor={traza.intencion} />
            <Dato etiqueta="Confianza" valor={traza.confianza?.toFixed(2)} />
            <Dato etiqueta="Total" valor={ms(latencias.totalMs || 0)} />
          </div>

          {traza.motivoClasificacion && (
            <div>
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-1">
                Motivo de la clasificación
              </p>
              <p className="text-xs text-gray-600 leading-relaxed">
                {traza.motivoClasificacion}
              </p>
            </div>
          )}

          {traza.motivoNoDelegacion && (
            <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2">
              {MOTIVOS_NO_DELEGACION[traza.motivoNoDelegacion] || traza.motivoNoDelegacion}
            </p>
          )}

          {pasos.length > 0 && (
            <div className="border-t border-gray-100 pt-3 space-y-3">
              {pasos.map((paso) => (
                <Paso key={paso.paso} paso={paso} />
              ))}
            </div>
          )}

          <div className="border-t border-gray-100 pt-2 flex justify-between text-[11px] text-gray-400">
            <span>clasificación {ms(latencias.clasificacionMs || 0)}</span>
            <span>agentes {ms(latencias.agentesMs || 0)}</span>
          </div>

          <p className="text-[10px] text-gray-300 font-mono break-all">{traza.trazaId}</p>
        </div>
      )}
    </div>
  )
}

export default TrazaPanel
