"""Pruebas del Nutrition Agent (issue S3-03).

El agente es deliberadamente simple -- una recuperacion y una generacion, sin
ciclo ReAct ni memoria -- asi que lo que hay que verificar no es un flujo de
decisiones sino tres propiedades: que respete su frontera de dominio, que no
deje pasar citas inventadas, y que declare los vacios de cobertura en vez de
rellenarlos.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.agents.nutrition.agent import (
    CATEGORIA_NUTRICION,
    MENSAJE_SIN_COBERTURA,
    NutritionAgent,
)


def chunk(doc_id, titulo="Nutricion para el corredor de resistencia",
          seccion="Carbohidratos", texto="Consumir 30-60 g de carbohidratos por hora."):
    return {
        "texto": texto,
        "similitud": 0.9,
        "metadata": {
            "doc_id": doc_id,
            "titulo": titulo,
            "seccion": seccion,
            "categoria": "nutricion",
            "nivel_evidencia": "alto",
        },
    }


class TestNutritionAgent(unittest.TestCase):

    def setUp(self):
        parche_repo = patch("src.agents.nutrition.agent.RepositorioCorredor")
        self.MockRepo = parche_repo.start()
        self.addCleanup(parche_repo.stop)

        self.MockRepo.return_value.obtener_perfil.return_value = MagicMock(
            nivel="intermedio", peso=68
        )

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_responde_con_las_fuentes_validadas(self, mock_recuperar, mock_generar):
        mock_recuperar.return_value = [chunk("KB-006")]
        mock_generar.return_value = {
            "respuesta": "Consume entre 30 y 60 g de carbohidratos por hora.",
            "fuentes": ["KB-006"],
            "cubierto": True,
        }

        resultado = NutritionAgent().responder("u1", "que como en una tirada larga?")

        self.assertIn("carbohidratos", resultado["respuesta"])
        self.assertEqual(resultado["fuentes"], ["KB-006"])
        self.assertEqual(resultado["fuentesInventadas"], [])
        self.assertEqual(resultado["fragmentosRecuperados"], ["KB-006"])
        self.assertTrue(resultado["cubierto"])

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_una_cita_inventada_se_separa_de_las_validas(
        self, mock_recuperar, mock_generar
    ):
        """El Sprint 1 documento que un modelo puede citar documentos que nunca
        recibio. En un sistema cuya ventaja es la trazabilidad, una cita
        inventada anula el beneficio, y el prompt reduce la frecuencia del
        problema pero no lo elimina: la validacion tiene que ser programatica."""
        mock_recuperar.return_value = [chunk("KB-006")]
        mock_generar.return_value = {
            "respuesta": "Segun KB-006 y KB-001...",
            "fuentes": ["KB-006", "KB-001"],
            "cubierto": True,
        }

        resultado = NutritionAgent().responder("u1", "que como?")

        self.assertEqual(resultado["fuentes"], ["KB-006"])
        self.assertEqual(resultado["fuentesInventadas"], ["KB-001"])

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_la_recuperacion_se_restringe_al_dominio_nutricional(
        self, mock_recuperar, mock_generar
    ):
        """La frontera entre agentes se aplica en el filtro de recuperacion,
        no solo en el prompt: aunque el prompt fallara, los documentos de
        entrenamiento no llegan al contexto de este agente."""
        mock_recuperar.return_value = [chunk("KB-006")]
        mock_generar.return_value = {"respuesta": "...", "fuentes": [], "cubierto": True}

        NutritionAgent().responder("u1", "cuanto debo correr esta semana?")

        _, kwargs = mock_recuperar.call_args
        self.assertEqual(kwargs["categoria"], CATEGORIA_NUTRICION)

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_sin_fragmentos_declara_el_vacio_sin_llamar_al_modelo(
        self, mock_recuperar, mock_generar
    ):
        """Si no hay nada que fundamentar, generar una respuesta solo puede
        producir contenido no verificado. Se declara el vacio y se ahorra la
        llamada."""
        mock_recuperar.return_value = []

        resultado = NutritionAgent().responder("u1", "que suplementos tomo?")

        self.assertEqual(resultado["respuesta"], MENSAJE_SIN_COBERTURA)
        self.assertFalse(resultado["cubierto"])
        self.assertEqual(resultado["fuentes"], [])
        self.assertEqual(resultado["fragmentosRecuperados"], [])
        mock_generar.assert_not_called()

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_el_peso_del_corredor_llega_al_prompt(self, mock_recuperar, mock_generar):
        """Las pautas nutricionales se expresan en gramos por kilogramo, asi
        que el peso es lo que permite convertirlas en cantidades concretas."""
        mock_recuperar.return_value = [chunk("KB-006")]
        mock_generar.return_value = {"respuesta": "...", "fuentes": [], "cubierto": True}

        NutritionAgent().responder("u1", "cuantos carbohidratos?")

        prompt = mock_generar.call_args[0][0]
        self.assertIn("68 kg", prompt)
        self.assertIn("intermedio", prompt)

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_sin_peso_registrado_se_declara_en_vez_de_inventarlo(
        self, mock_recuperar, mock_generar
    ):
        self.MockRepo.return_value.obtener_perfil.return_value = MagicMock(
            nivel="principiante", peso=None
        )
        mock_recuperar.return_value = [chunk("KB-006")]
        mock_generar.return_value = {"respuesta": "...", "fuentes": [], "cubierto": True}

        NutritionAgent().responder("u1", "cuantos carbohidratos?")

        prompt = mock_generar.call_args[0][0]
        self.assertIn("no registrado", prompt)

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_el_vacio_declarado_por_el_modelo_se_propaga(
        self, mock_recuperar, mock_generar
    ):
        """Los fragmentos existen pero no responden la pregunta, y el modelo lo
        declara con cubierto=false.

        Eso NO es una degradacion. Desde la correccion S2-04, 'degradado'
        significa que una capacidad fallo; que la base de conocimiento no cubra
        un tema es el sistema funcionando -- el agente comprobo que no
        alcanzaba y lo dijo, en vez de rellenarlo con conocimiento no
        verificado. El adaptador _invocar_nutrition() lo refleja: marca
        degradado unicamente ante fuentes inventadas, y la cobertura viaja en
        el detalle para medirse por separado. Contar un vacio documental como
        fallo registraria la conducta correcta igual que un error y
        contaminaria la medicion de S3-06.
        """
        mock_recuperar.return_value = [chunk("KB-006")]
        mock_generar.return_value = {
            "respuesta": "La base de conocimiento no cubre suplementacion.",
            "fuentes": [],
            "cubierto": False,
        }

        resultado = NutritionAgent().responder("u1", "que suplementos tomo?")

        self.assertFalse(resultado["cubierto"])
        self.assertEqual(resultado["fuentes"], [])

    @patch("src.agents.nutrition.agent.generar")
    @patch("src.agents.nutrition.agent.recuperar")
    def test_los_fragmentos_recuperados_llegan_al_prompt_con_su_doc_id(
        self, mock_recuperar, mock_generar
    ):
        """El modelo solo puede citar lo que ve. Si el doc_id no aparece en el
        prompt, cualquier cita seria necesariamente inventada."""
        mock_recuperar.return_value = [
            chunk("KB-006", seccion="Hidratacion", texto="Beber segun la sed.")
        ]
        mock_generar.return_value = {"respuesta": "...", "fuentes": [], "cubierto": True}

        NutritionAgent().responder("u1", "cuanto tomo de agua?")

        prompt = mock_generar.call_args[0][0]
        self.assertIn("KB-006", prompt)
        self.assertIn("Hidratacion", prompt)
        self.assertIn("Beber segun la sed.", prompt)


if __name__ == "__main__":
    unittest.main()