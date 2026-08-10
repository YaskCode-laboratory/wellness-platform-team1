import { NavLink } from 'react-router-dom'
import navHome from '../assets/nav_home.png'
import navHistorial from '../assets/nav_historial.png'
import navStats from '../assets/nav_stats.png'
import navObjetivo from '../assets/nav_objetivo.png'
import navIA from '../assets/nav_ia.png'

const navItems = [
  { to: '/dashboard', icon: navHome, label: 'Inicio' },
  { to: '/historial', icon: navHistorial, label: 'Historial' },
  { to: '/estadisticas', icon: navStats, label: 'Stats' },
  { to: '/mi-objetivo', icon: navObjetivo, label: 'Objetivo' },
  { to: '/recomendacion', icon: navIA, label: 'IA' },
]

const BottomNav = () => (
  <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex justify-around items-center h-16 z-50">
    {navItems.map(({ to, icon, label }) => (
      <NavLink
        key={to}
        to={to}
        className={({ isActive }) =>
          `flex flex-col items-center text-xs gap-1 px-2 ${
            isActive ? 'text-blue-600 font-semibold' : 'text-gray-500'
          }`
        }
      >
        {({ isActive }) => (
          <>
            <img
              src={icon}
              alt={label}
              className="w-7 h-7 object-contain"
              style={{ opacity: isActive ? 1 : 0.5 }}
            />
            <span>{label}</span>
          </>
        )}
      </NavLink>
    ))}
  </nav>
)

export default BottomNav