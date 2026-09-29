"""Verificacion de que cada agente accede solo a los datos de su responsabilidad.

Criterio de aceptacion de S3-05: "verificar que el acceso a datos corresponda a
la responsabilidad de cada agente".

Hasta ahora esa correspondencia se sostenia por construccion -- el Nutrition
Agent no consulta sesiones porque nadie escribio ese codigo -- lo cual no es
una garantia sino una coincidencia que sobrevive mientras nadie la rompa. Estas
pruebas la convierten en un invariante: si alguien amplia un agente hacia datos
que no le corresponden, la suite lo dice.

LA MATRIZ DE ACCESO

                        perfil  sesiones  objetivos  memoria  KB-entren.  KB-nutric.  clima
  Orchestrator            -         -         -         -          -           -        -
  Wellness Coach          si       si        si        si         si          no       si
  Nutrition               si       no        no        no         no          si       no

El orquestador no accede a ningun dato del corredor: clasifica y delega. Si
empezara a consultar por su cuenta dejaria de ser un coordinador.

COBERTURA DE LAS TRES FILAS

La primera version cubria el Nutrition Agent y el orquestador, pero no el
Coach. Es la fila mas ancha -- seis de las siete columnas -- y justamente por
eso la que mas necesita cobertura: con tantos accesos legitimos, uno
ilegitimo no llamaria la atencion.

El Coach se verifica a traves del despachador de herramientas y no invocando
su ciclo ReAct completo. Su acceso a datos pasa siempre por ahi desde la
correccion S2-04, que centralizo el despacho, y probarlo en ese punto no
depende de que el modelo decida invocar cada herramienta en una corrida
concreta.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agents.nutrition.agent import CATEGORIA_NUTRICION, NutritionAgent
from src.agents.wellness_coach.tools.conocimiento import CATEGORIAS_COACH
from src.agents.wellness_coach.tools.registro import _HERRAMIENTAS, despachar
from src.orchestration.delegation import registro as registro_delegaciones
from src.orchestration.orchestrator import agent as modulo_orquestador

RAIZ = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE = RAIZ / "data" / "knowledge_base"


def categorias_de_la_taxonomia() -> set[str]:
    """Categorias declaradas en el front-matter de la knowledge base."""
    categorias = set()
    for archivo in KNOWLEDGE_BASE.glob("*.md"):
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.startswith("categoria:"):
                categorias.add(linea.split(":", 1)[1].strip())
                break
    return categorias


class TestFronteraDocumental(unittest.TestCase):
    """El reparto de la taxonomia entre agentes debe ser total y disjunto."""

    def test_los_dominios_documentales_no_se_solapan(self):
        """Si una categoria perteneciera a dos agentes, la frontera dejaria de
        serlo: los dos podrian responder sobre lo mismo."""
        self.assertNotIn(CATEGORIA_NUTRICION, CATEGORIAS_COACH)

    def test_toda_categoria_de_la_taxonomia_tiene_dueno(self):
        """Guarda contra la laguna silenciosa: un documento nuevo con una
        categoria que no pertenece a ningun agente seria irrecuperable, y nadie
        se enteraria hasta que un corredor preguntara por ese tema y recibiera
        una respuesta sin fundamento."""
        declaradas = set(CATEGORIAS_COACH) | {CATEGORIA_NUTRICION}
        reales = categorias_de_la_taxonomia()

        self.assertTrue(reales, "no se encontraron categorias en la knowledge base")
        huerfanas = reales - declaradas
        self.assertEqual(
            huerfanas,
            set(),
            f"categorias sin agente asignado: {sorted(huerfanas)}. "
            "Asignalas a un agente o creale uno.",
        )

    def test_ningun_agente_declara_una_categoria_inexistente(self):
        """Filtrar por una categoria que no existe no da error: da cero
        resultados. Un agente quedaria mudo sin que nada lo indicara."""
        declaradas = set(CATEGORIAS_COACH) | {CATEGORIA_NUTRICION}
        reales = categorias_de_la_taxonomia()

        inexistentes = declaradas - reales
        self.assertEqual(
            inexistentes,
            set(),
            f"categorias declaradas que no existen en la knowledge base: "
            f"{sorted(inexistentes)}",
        )


class TestAccesoDelNutritionAgent(unittest.TestCase):
    """El Nutrition Agent solo necesita el perfil y su categoria documental."""

    def setUp(self):
        parche_repo = patch("src.agents.nutrition.agent.RepositorioCorredor")
        self.MockRepo = parche_repo.start()
        self.addCleanup(parche_repo.stop)
        self.MockRepo.return_value.obtener_perfil.return_value = MagicMock(
            nivel="intermedio", peso=68
        )

        parche_recuperar = patch("src.agents.nutrition.agent.recuperar")
        self.mock_recuperar = parche_recuperar.start()
        self.addCleanup(parche_recuperar.stop)
        self.mock_recuperar.return_value = [
            {
                "texto": "...",
                "similitud": 0.9,
                "metadata": {
                    "doc_id": "KB-006",
                    "titulo": "Nutricion",
                    "seccion": "Hidratacion",
                    "categoria": "nutricion",
                },
            }
        ]

        parche_generar = patch("src.agents.nutrition.agent.generar")
        self.mock_generar = parche_generar.start()
        self.addCleanup(parche_generar.stop)
        self.mock_generar.return_value = {
            "respuesta": "...", "fuentes": [], "cubierto": True
        }

    def test_consulta_el_perfil_porque_las_pautas_dependen_del_peso(self):
        NutritionAgent().responder("u1", "cuantos carbohidratos?")

        self.MockRepo.return_value.obtener_perfil.assert_called_once_with("u1")

    def test_no_accede_al_historial_de_entrenamiento(self):
        """Las sesiones, la carga semanal y los objetivos son del dominio del
        Coach. Que el Nutrition Agent los leyera no romperia nada de inmediato,
        pero difuminaria la frontera que S3-03 establecio."""
        NutritionAgent().responder("u1", "cuantos carbohidratos?")

        repo = self.MockRepo.return_value
        repo.obtener_ultimas_sesiones.assert_not_called()
        repo.calcular_carga_semanal.assert_not_called()
        repo.obtener_objetivos_activos.assert_not_called()
        repo.cargar_estado_corredor.assert_not_called()

    def test_su_recuperacion_se_restringe_a_su_categoria(self):
        NutritionAgent().responder("u1", "cuanto debo correr esta semana?")

        _, kwargs = self.mock_recuperar.call_args
        self.assertEqual(kwargs["categoria"], CATEGORIA_NUTRICION)
        self.assertNotIn("categorias", kwargs)


class TestAccesoDelWellnessCoach(unittest.TestCase):
    """La fila del Coach en la matriz, celda por celda.

    Las pruebas anteriores cubrian el Nutrition Agent y el orquestador, pero
    no el Coach, que es el agente con la fila mas ancha: accede a seis de las
    siete columnas. Justamente por eso es donde una ampliacion indebida
    pasaria mas facilmente inadvertida -- con tantos accesos legitimos, uno
    ilegitimo no llama la atencion.

    Se verifica a traves del despachador de herramientas y no invocando el
    ciclo ReAct completo: el acceso a datos del Coach ocurre siempre por ahi
    (es la conclusion de la correccion S2-04, que centralizo el despacho), y
    probarlo en ese punto no depende de que el modelo decida invocar cada
    herramienta.
    """

    def setUp(self):
        parche_repo = patch("src.agents.wellness_coach.tools.historial._repo")
        self.repo = parche_repo.start()
        self.addCleanup(parche_repo.stop)
        self.repo.obtener_sesiones_recientes.return_value = [{"distanciaKm": 8}]
        self.repo.calcular_carga_semanal.return_value = (24.0, 20.0)
        self.repo.obtener_objetivos_activos.return_value = [{"kmMeta": 30}]

        parche_recuperar = patch(
            "src.agents.wellness_coach.tools.conocimiento.recuperar"
        )
        self.recuperar = parche_recuperar.start()
        self.addCleanup(parche_recuperar.stop)
        self.recuperar.return_value = []

    def test_accede_al_historial_de_sesiones(self):
        despachar("consultar_historial_sesiones", {}, user_id="u1")

        self.repo.obtener_sesiones_recientes.assert_called_once()
        self.assertEqual(self.repo.obtener_sesiones_recientes.call_args[0][0], "u1")

    def test_accede_a_la_carga_semanal_y_a_los_objetivos(self):
        """Ambos pertenecen a su dominio: el progreso respecto a la meta es
        precisamente lo que el criterio de S3-03 le asigna."""
        despachar("consultar_progreso_objetivo", {}, user_id="u1")

        self.repo.calcular_carga_semanal.assert_called_once_with("u1")
        self.repo.obtener_objetivos_activos.assert_called_once_with("u1")

    def test_el_user_id_lo_inyecta_el_despachador_no_el_modelo(self):
        """Los argumentos que produce el modelo nunca incluyen el
        identificador del corredor: lo pone el despachador desde el contexto
        de la peticion. Es lo que impide que una salida del modelo induzca a
        leer datos de otro usuario."""
        despachar("consultar_historial_sesiones", {"user_id": "otro-corredor"},
                  user_id="u1")

        self.assertEqual(self.repo.obtener_sesiones_recientes.call_args[0][0], "u1")

    def test_su_recuperacion_se_restringe_a_sus_seis_categorias(self):
        despachar("consultar_base_conocimiento", {"consulta": "zona 2"}, user_id="u1")

        _, kwargs = self.recuperar.call_args
        self.assertEqual(kwargs["categorias"], CATEGORIAS_COACH)
        self.assertNotIn("categoria", kwargs)

    def test_no_puede_recuperar_documentacion_de_nutricion(self):
        """La celda que cierra la frontera. Se comprueba sobre la lista de
        categorias y no sobre un resultado, porque el filtro es lo que da la
        garantia: mientras 'nutricion' no este ahi, no hay consulta que pueda
        traerla."""
        despachar("consultar_base_conocimiento", {"consulta": "que como antes?"},
                  user_id="u1")

        _, kwargs = self.recuperar.call_args
        self.assertNotIn(CATEGORIA_NUTRICION, kwargs["categorias"])

    def test_la_descripcion_de_la_herramienta_no_promete_nutricion(self):
        """El filtro impide RECUPERAR nutricion, no impide que el modelo crea
        que deberia encontrarla. La descripcion de la FunctionDeclaration es
        lo que lee para decidir si invoca, y durante S3-03 a S3-05 siguio
        anunciando nutricion pese a que el filtro ya la excluia. El modelo
        invocaba, no recibia nada, y quedaba ante un vacio aparente de la base
        de conocimiento en lugar de reconocer que el tema es de otro agente.

        Garantia estructural y descripcion cubren huecos distintos: hace falta
        que coincidan."""
        herramienta = next(
            h for h in _HERRAMIENTAS if h["name"] == "consultar_base_conocimiento"
        )
        descripcion = herramienta["description"].lower()

        self.assertIn("no cubre nutricion", descripcion)

    def test_no_accede_a_los_datos_de_otro_corredor(self):
        """Ninguna herramienta del Coach recibe un identificador ajeno: todas
        las que tocan datos lo toman del despachador."""
        for nombre in ("consultar_historial_sesiones", "consultar_progreso_objetivo"):
            self.repo.reset_mock()
            despachar(nombre, {}, user_id="u-propio")

            usados = {
                posicionales[0]
                for _, posicionales, _ in self.repo.method_calls
                if posicionales
            }
            self.assertEqual(usados, {"u-propio"}, f"{nombre} uso {usados}")


class TestAccesoDelOrquestador(unittest.TestCase):
    """El orquestador coordina: no consulta datos del corredor.

    Se comprueba de forma estatica, sobre los nombres que el modulo importa. Un
    acceso a datos empieza siempre por una importacion, asi que si el modulo no
    conoce al repositorio ni al retriever, no puede consultarlos -- y la prueba
    lo detecta en el momento en que alguien agregue el import, sin depender de
    que exista un caso que ejercite ese camino.
    """

    def test_no_importa_el_repositorio_del_corredor(self):
        self.assertFalse(
            hasattr(modulo_orquestador, "RepositorioCorredor"),
            "el orquestador no debe acceder a los datos del corredor: "
            "si empieza a resolver por su cuenta deja de ser un coordinador",
        )

    def test_no_importa_el_retriever_ni_la_base_de_conocimiento(self):
        for nombre in ("recuperar", "consultar_base_conocimiento", "buscar"):
            self.assertFalse(
                hasattr(modulo_orquestador, nombre),
                f"el orquestador no debe consultar la base de conocimiento ({nombre})",
            )

    def test_no_importa_el_cliente_de_firestore_directamente(self):
        """Su unico contacto con Firestore es el registro de delegaciones, y lo
        recibe inyectado para poder sustituirlo."""
        self.assertFalse(hasattr(modulo_orquestador, "db"))


class TestRegistroDeDelegaciones(unittest.TestCase):
    """El registro escribe donde debe y no rompe la solicitud si falla."""

    @patch("src.orchestration.delegation.registro.db")
    def test_escribe_en_la_coleccion_de_delegaciones(self, mock_db):
        ok = registro_delegaciones.RegistroDelegaciones().registrar(
            {"trazaId": "abc", "agentes": ["nutrition"]}
        )

        self.assertTrue(ok)
        mock_db.collection.assert_called_once_with(registro_delegaciones.COLECCION)
        mock_db.collection.return_value.document.assert_called_once_with("abc")

    @patch("src.orchestration.delegation.registro.db")
    def test_un_fallo_de_firestore_no_propaga(self, mock_db):
        """El corredor no tiene por que quedarse sin respuesta porque no se
        pudo escribir una traza."""
        mock_db.collection.side_effect = ConnectionError("Firestore caido")

        with self.assertLogs("src.orchestration.delegation.registro", level="ERROR"):
            ok = registro_delegaciones.RegistroDelegaciones().registrar({"trazaId": "abc"})

        self.assertFalse(ok)

    @patch("src.orchestration.delegation.registro.db")
    def test_una_traza_sin_identificador_se_descarta(self, mock_db):
        """Sin trazaId no hay clave con la que guardarla ni con la que
        recuperarla despues."""
        with self.assertLogs("src.orchestration.delegation.registro", level="ERROR"):
            ok = registro_delegaciones.RegistroDelegaciones().registrar({"agentes": []})

        self.assertFalse(ok)
        mock_db.collection.assert_not_called()


if __name__ == "__main__":
    unittest.main()