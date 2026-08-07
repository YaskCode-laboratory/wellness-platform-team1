import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getWeeklyChart, getSummary } from '../services/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line
} from 'recharts'

const formatearRitmo = (ritmoDecimal) => {
  if (!ritmoDecimal || ritmoDecimal === 0) return '--'
  const minutos = Math.floor(ritmoDecimal)
  const segundos = Math.round((ritmoDecimal - minutos) * 60)
  return `${minutos}:${segundos.toString().padStart(2, '0')}`
}

const formatearFechaSemana = (fechaStr) => {
  if (!fechaStr) return ''
  const parts = fechaStr.split('-')
  return `${parts[2]}/${parts[1]}`
}

const periodos = [
  { label: 'Mensual', semanas: 4 },
  { label: 'Trimestral', semanas: 12 },
  { label: 'Anual', semanas: 52 }
]

const CustomTooltipKm = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-lg">
        <p className="text-xs text-gray-500 mb-1">Semana del {label}</p>
        <p className="text-sm font-bold text-blue-600">{payload[0].value} km</p>
      </div>
    )
  }
  return null
}

const CustomTooltipSesiones = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-lg">
        <p className="text-xs text-gray-500 mb-1">Semana del {label}</p>
        <p className="text-sm font-bold text-green-600">{payload[0].value} sesiones</p>
      </div>
    )
  }
  return null
}

const CustomTooltipRitmo = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-lg">
        <p className="text-xs text-gray-500 mb-1">Semana del {label}</p>
        <p className="text-sm font-bold text-purple-600">
          {formatearRitmo(payload[0].value)} min/km
        </p>
      </div>
    )
  }
  return null
}

const Estadisticas = () => {
  const { user } = useAuth()
  const [chartData, setChartData] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [periodoIdx, setPeriodoIdx] = useState(0)

  const semanas = periodos[periodoIdx].semanas

  const fetchData = async () => {
    setLoading(true)
    try {
      const [chartRes, summaryRes] = await Promise.all([
        getWeeklyChart(user.uid, semanas),
        getSummary(user.uid, semanas)
      ])
      const data = chartRes.data?.data || []
      setChartData(data.map(d => ({
        ...d,
        semana: formatearFechaSemana(d.semana),
        kmTotales: parseFloat(d.kmTotales.toFixed(1)),
        ritmoPromedio: parseFloat(d.ritmoPromedio.toFixed(2))
      })))
      setSummary(summaryRes.data)
    } catch (err) {
      console.log('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [user.uid, periodoIdx])

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-blue-600 text-lg">Cargando estadisticas...</div>
    </div>
  )

  const sinDatos = chartData.every(d => d.kmTotales === 0)

  return (
    <div className="p-4 max-w-lg mx-auto">

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold text-gray-800">Estadisticas</h1>
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
          {periodos.map((p, i) => (
            <button
              key={i}
              onClick={() => setPeriodoIdx(i)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                periodoIdx === i
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-3 mb-6">
          <div className="bg-white rounded-2xl shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">
              {summary.totalKm?.toFixed(1) || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">km totales</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">
              {summary.totalSesiones || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">sesiones</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-purple-600">
              {formatearRitmo(summary.mejorRitmo)}
            </p>
            <p className="text-xs text-gray-500 mt-1">mejor ritmo</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">
              {summary.promedioKmSemanal?.toFixed(1) || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">km/semana promedio</p>
          </div>
        </div>
      )}

      {sinDatos ? (
        <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
          <p className="text-gray-400 text-sm">No hay datos para este periodo.</p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
            <h2 className="text-sm font-semibold text-gray-600 mb-4">Kilometros por semana</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="semana" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltipKm />} />
                <Bar dataKey="kmTotales" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
            <h2 className="text-sm font-semibold text-gray-600 mb-4">Sesiones por semana</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="semana" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltipSesiones />} />
                <Bar dataKey="sesiones" fill="#10b981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
            <h2 className="text-sm font-semibold text-gray-600 mb-4">Ritmo promedio (min/km)</h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="semana" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
                <Tooltip content={<CustomTooltipRitmo />} />
                <Line type="monotone" dataKey="ritmoPromedio" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: '#8b5cf6', r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
            <h2 className="text-sm font-semibold text-gray-600 mb-4">Detalle semanal</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 border-b border-gray-100">
                    <th className="text-left pb-2">Semana</th>
                    <th className="text-right pb-2">km</th>
                    <th className="text-right pb-2">Sesiones</th>
                    <th className="text-right pb-2">Ritmo</th>
                  </tr>
                </thead>
                <tbody>
                  {chartData.slice().reverse().map((row, i) => (
                    <tr key={i} className="border-b border-gray-50">
                      <td className="py-2 text-gray-600">{row.semana}</td>
                      <td className="py-2 text-right font-semibold text-blue-600">{row.kmTotales}</td>
                      <td className="py-2 text-right text-gray-600">{row.sesiones}</td>
                      <td className="py-2 text-right text-purple-600">
                        {row.ritmoPromedio > 0 ? formatearRitmo(row.ritmoPromedio) : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Estadisticas