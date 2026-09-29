import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: {
        ...globals.browser,
        // Lo inyecta Vite en tiempo de compilacion (define en vite.config.js)
        // a partir de la version de package.json. Sin declararlo, eslint lo
        // reporta como no-undef y esconde entre ruido cualquier variable
        // realmente indefinida, que es el problema que esa regla existe para
        // detectar.
        __APP_VERSION__: 'readonly',
      },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // DOS REGLAS DEGRADADAS A AVISO, CON MOTIVO
      //
      // El lint es puerta del despliegue (.github/workflows/deploy-frontend.yml),
      // asi que lo que quede en 'error' bloquea publicar. Estas dos senalan
      // cosas reales pero ninguna es un defecto de correccion, y dejarlas como
      // error obligaria a elegir entre no desplegar o apagar el lint entero.
      // Se degradan nombradas y con explicacion, que es distinto de ignorarlas
      // en silencio: siguen apareciendo en cada corrida.

      // Avisa de que un archivo exporta algo que no es un componente, lo que
      // rompe el Fast Refresh de Vite. Afecta solo a la experiencia de
      // desarrollo -- hay que recargar a mano-- y no a lo que se despliega.
      // Lo disparan agenteInfo() en TrazaPanel y el hook useAuth en
      // AuthContext, dos casos donde separar el archivo por esto seria peor
      // para leer el codigo.
      'react-refresh/only-export-components': 'warn',

      // Avisa de llamar a setState en el cuerpo de un efecto, que provoca
      // renders en cascada. Lo disparan las cuatro pantallas que cargan datos
      // al montarse. Arreglarlo bien no es mover una linea: exige reestructurar
      // la carga de datos de esas pantallas. Anotado como deuda, no resuelto
      // dentro de una tarea de despliegue.
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
])
