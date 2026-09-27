import unittest
from unittest.mock import MagicMock, patch

from src.agents.wellness_coach.memory import (
    MAX_TURNOS_PERSISTIDOS,
    MemoriaConversacional,
    TurnoConversacion,
)


def _doc(datos, existe=True):
    d = MagicMock()
    d.exists = existe
    d.to_dict.return_value = datos
    return d


class TestMemoriaConversacional(unittest.TestCase):

    def setUp(self):
        patcher = patch("src.agents.wellness_coach.memory.db")
        self.mock_db = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_ref = MagicMock()
        self.mock_db.collection.return_value.document.return_value = self.mock_ref

    def test_historial_vacio_si_no_existe_documento(self):
        self.mock_ref.get.return_value = _doc({}, existe=False)
        memoria = MemoriaConversacional()
        self.assertEqual(memoria.obtener_historial("u1"), [])

    def test_agregar_turno_rol_invalido(self):
        memoria = MemoriaConversacional()
        with self.assertRaises(ValueError):
            memoria.agregar_turno("u1", "moderador", "hola")

    def test_agregar_turno_acumula_sobre_existentes(self):
        self.mock_ref.get.return_value = _doc({
            "turnos": [{"rol": "usuario", "contenido": "hola", "timestamp": "t1"}]
        })
        memoria = MemoriaConversacional()
        memoria.agregar_turno("u1", "agente", "hola, como estas")

        args, _ = self.mock_ref.set.call_args
        turnos_guardados = args[0]["turnos"]
        self.assertEqual(len(turnos_guardados), 2)
        self.assertEqual(turnos_guardados[-1]["contenido"], "hola, como estas")

    def test_recorta_al_maximo_persistido(self):
        turnos_previos = [
            {"rol": "usuario", "contenido": f"msg{i}", "timestamp": "t"}
            for i in range(MAX_TURNOS_PERSISTIDOS)
        ]
        self.mock_ref.get.return_value = _doc({"turnos": turnos_previos})
        memoria = MemoriaConversacional()
        memoria.agregar_turno("u1", "agente", "nuevo")

        args, _ = self.mock_ref.set.call_args
        turnos_guardados = args[0]["turnos"]
        self.assertEqual(len(turnos_guardados), MAX_TURNOS_PERSISTIDOS)
        self.assertEqual(turnos_guardados[-1]["contenido"], "nuevo")

    def test_formatear_para_prompt_vacio(self):
        memoria = MemoriaConversacional()
        self.assertEqual(memoria.formatear_para_prompt([]), "Sin conversacion previa.")

    def test_formatear_para_prompt_con_turnos(self):
        memoria = MemoriaConversacional()
        turnos = [
            TurnoConversacion("usuario", "hola", "t1"),
            TurnoConversacion("agente", "hola, en que ayudo?", "t2"),
        ]
        salida = memoria.formatear_para_prompt(turnos)
        self.assertIn("Corredor: hola", salida)
        self.assertIn("RunCoach: hola, en que ayudo?", salida)


if __name__ == "__main__":
    unittest.main()