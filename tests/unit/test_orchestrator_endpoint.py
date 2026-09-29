"""Pruebas del endpoint HTTP del sistema multiagente (issue S3-02).

POR QUE UN ARCHIVO APARTE DE test_orchestrator.py

Prueban capas distintas. test_orchestrator.py verifica la politica de
delegacion y el flujo interno del coordinador; esto verifica la frontera HTTP:
que el cuerpo se valide, que la traza llegue entera al cliente, y que un fallo
del coordinador no se convierta en una filtracion de informacion interna.

Que el orquestador funcione no implica que el endpoint funcione. El Sprint 3
dio un ejemplo caro de esa distincion: los handlers declarados 'async def'
hacian E/S bloqueante dentro del bucle de eventos y serializaban las peticiones
concurrentes, con la suite entera en verde, porque ninguna prueba pasaba por
FastAPI.

El orquestador se mockea. Lo que se comprueba aqui es el contrato de la ruta,
no la coordinacion: mezclarlos daria una prueba que falla por dos razones
distintas y no distingue cual.
"""

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import orchestrator_routes

# Forma completa de lo que devuelve OrchestratorAgent.procesar(). Se escribe
# entera y no recortada a proposito: si el contrato de la traza cambia, esta
# prueba debe enterarse.
TRAZA = {
    "trazaId": "traza-de-prueba",
    "generadoEn": "2026-09-27T10:00:00+00:00",
    "respuesta": "Tu carga viene subiendo un 12% respecto a la semana pasada.",
    "delegado": True,
    "colaboracion": False,
    "agente": "wellness_coach",
    "agentes": ["wellness_coach"],
    "intencion": "entrenamiento",
    "motivoClasificacion": "pregunta por su progresion de carga",
    "confianza": 0.9,
    "motivoNoDelegacion": None,
    "degradado": False,
    "herramientasInvocadas": ["consultar_progreso"],
    "fuentes": ["KB-001"],
    "pasos": [
        {
            "paso": 1,
            "agente": "wellness_coach",
            "herramientasInvocadas": ["consultar_progreso"],
            "fuentes": ["KB-001"],
            "degradado": False,
            "latenciaMs": 2100,
            "detalle": {},
        }
    ],
    "latencias": {"clasificacionMs": 900, "agentesMs": 2100, "totalMs": 3050},
}


def cliente() -> TestClient:
    """App minima con solo este router montado.

    No se usa src.app.main porque alli conviven otros routers cuyo import
    tiene efectos propios: una prueba de este endpoint no deberia fallar
    porque otro modulo de rutas cambie.
    """
    app = FastAPI()
    app.include_router(orchestrator_routes.router)
    return TestClient(app)


class TestEndpointDeChat(unittest.TestCase):

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_devuelve_la_traza_completa_del_orquestador(self, mock_procesar):
        """El endpoint no resume ni recorta: la traza viaja entera.

        Es lo que permite que la demostracion de S3-07 y la evaluacion de
        S3-06 reconstruyan el recorrido de una solicitud sin leer los logs del
        servidor.
        """
        mock_procesar.return_value = TRAZA

        respuesta = cliente().post(
            "/orchestrator/u-123/chat", json={"mensaje": "como voy de carga?"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), TRAZA)

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_el_userId_de_la_ruta_llega_al_orquestador(self, mock_procesar):
        """El identificador del corredor lo inyecta la ruta desde la URL, no
        el cuerpo del mensaje: es la misma decision que el contrato de
        SolicitudAgente documenta para impedir que un texto induzca a
        consultar datos de otro corredor."""
        mock_procesar.return_value = TRAZA

        cliente().post(
            "/orchestrator/u-456/chat", json={"mensaje": "cuanto corri esta semana?"}
        )

        mock_procesar.assert_called_once_with("u-456", "cuanto corri esta semana?")

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_un_mensaje_vacio_se_rechaza_antes_de_llegar_al_orquestador(
        self, mock_procesar
    ):
        """Clasificar una cadena vacia cuesta una llamada al modelo y devuelve
        'no_reconocida' con total seguridad. El modelo Pydantic lo corta
        antes."""
        respuesta = cliente().post("/orchestrator/u-123/chat", json={"mensaje": ""})

        self.assertEqual(respuesta.status_code, 422)
        mock_procesar.assert_not_called()

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_un_cuerpo_sin_el_campo_mensaje_se_rechaza(self, mock_procesar):
        respuesta = cliente().post("/orchestrator/u-123/chat", json={})

        self.assertEqual(respuesta.status_code, 422)
        mock_procesar.assert_not_called()


class TestErrorInternoNoSeFiltra(unittest.TestCase):
    """El detalle tecnico va al log; al cliente, un mensaje fijo.

    La version anterior devolvia str(e) en 'detail'. El texto de una excepcion
    de Python arrastra rutas del sistema de archivos, nombres de colecciones de
    Firestore e identificadores de proyecto de GCP, y ese cuerpo llega hasta el
    navegador del corredor.
    """

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_el_mensaje_de_la_excepcion_no_viaja_al_cliente(self, mock_procesar):
        secreto = "projects/runcoach-ai-496921/databases/(default)/documents/corredores"
        mock_procesar.side_effect = RuntimeError(f"PermissionDenied en {secreto}")

        respuesta = cliente().post(
            "/orchestrator/u-123/chat", json={"mensaje": "como voy?"}
        )

        self.assertEqual(respuesta.status_code, 500)
        cuerpo = respuesta.text
        self.assertNotIn(secreto, cuerpo)
        self.assertNotIn("PermissionDenied", cuerpo)
        self.assertNotIn("RuntimeError", cuerpo)

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_el_cliente_recibe_un_mensaje_accionable(self, mock_procesar):
        """Un 500 sin texto util deja al corredor sin saber si reintentar."""
        mock_procesar.side_effect = RuntimeError("cualquier fallo interno")

        respuesta = cliente().post(
            "/orchestrator/u-123/chat", json={"mensaje": "como voy?"}
        )

        self.assertEqual(
            respuesta.json()["detail"], orchestrator_routes.ERROR_INTERNO
        )

    @patch.object(orchestrator_routes.orquestador, "procesar")
    def test_el_detalle_tecnico_queda_registrado(self, mock_procesar):
        """Quien depura necesita lo que el cliente no debe ver. Si el detalle
        no queda en el log, quitarlo de la respuesta lo pierde del todo."""
        mock_procesar.side_effect = RuntimeError("PermissionDenied en Firestore")

        with self.assertLogs(orchestrator_routes.logger, level="ERROR") as registro:
            cliente().post("/orchestrator/u-123/chat", json={"mensaje": "como voy?"})

        salida = "\n".join(registro.output)
        self.assertIn("u-123", salida)
        self.assertIn("PermissionDenied en Firestore", salida)


if __name__ == "__main__":
    unittest.main()
