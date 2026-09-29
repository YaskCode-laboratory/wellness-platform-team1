/**
 * El isotipo de RunCoach corriendo. Indicador de espera de la aplicacion.
 *
 * La imagen es estatica, asi que la carrera se compone: la zancada sube y baja
 * al corredor con una inclinacion minima, y tres estelas barren hacia atras
 * con desfase para dar sensacion de avance. Las animaciones viven en
 * index.css y respetan prefers-reduced-motion.
 *
 * No se deforma el isotipo. Escalarlo o estirarlo daria mas sensacion de
 * esfuerzo, pero dejaria de ser la marca.
 */

// El PNG y no el SVG: runcoachlogomini.svg contiene un dibujo distinto y mal
// construido, un cuadrado azul con una figura que no corresponde al isotipo.
import logoMini from '../assets/runcoachlogomini.png'

const ESTELAS = [
  { ancho: 'w-4', color: 'bg-yellow-400', retraso: '0s' },
  { ancho: 'w-3', color: 'bg-blue-500', retraso: '0.12s' },
  { ancho: 'w-2.5', color: 'bg-yellow-400', retraso: '0.24s' },
]

const IsoCorriendo = ({ alto = 'h-5' }) => (
  <span className="relative inline-flex items-center flex-none" aria-hidden="true">
    <span className="absolute right-full mr-0.5 flex flex-col gap-[3px] pointer-events-none">
      {ESTELAS.map((e, i) => (
        <span
          key={i}
          className={`runcoach-estela block h-[2px] rounded-full ${e.ancho} ${e.color}`}
          style={{ animationDelay: e.retraso }}
        />
      ))}
    </span>
    <img src={logoMini} alt="" className={`runcoach-zancada ${alto} w-auto object-contain`} />
  </span>
)

export default IsoCorriendo
