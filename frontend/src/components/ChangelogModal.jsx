import changelog from '../data/changelog.json'
import logoMini from '../assets/runcoachlogomini.png'

const tipoColor = {
  feature: 'bg-blue-100 text-blue-700',
  fix: 'bg-red-100 text-red-700',
  mejora: 'bg-green-100 text-green-700'
}

const ChangelogModal = ({ onClose }) => {
  return (
    <div className="fixed inset-0 flex items-end justify-center z-50 p-4" style={{ backgroundColor: 'rgba(255,255,255,0.4)' }}>
      <div className="bg-white rounded-2xl w-full max-w-sm max-h-[80vh] flex flex-col shadow-2xl relative">

        <div className="flex flex-col items-center p-5 border-b border-gray-100">
            <img src={logoMini} alt="RunCoach AI" className="w-32 h-32 object-contain mb-2" />
            <h2 className="text-lg font-bold text-gray-800">Novedades</h2>
            
            <button
                onClick={onClose}
                className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 text-xl font-bold transition w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100"
            >
                x
            </button>
        </div>

        <div className="overflow-y-auto p-5 space-y-6">
          {changelog.map((release, i) => (
            <div key={i}>
              <div className="flex items-center gap-3 mb-3">
                <span className="bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                  {release.version}
                </span>
                <span className="text-xs text-gray-400">{release.fecha}</span>
              </div>
              <p className="text-sm font-semibold text-gray-700 mb-2">{release.titulo}</p>
              <div className="space-y-2">
                {release.cambios.map((cambio, j) => (
                  <div key={j} className="flex items-start gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${tipoColor[cambio.tipo] || tipoColor.feature}`}>
                      {cambio.codigo}
                    </span>
                    <p className="text-xs text-gray-600 leading-relaxed">{cambio.descripcion}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
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
}

export default ChangelogModal