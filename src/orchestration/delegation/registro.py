"""Registro persistente de las delegaciones realizadas.

Entregable de S3-04 ("registro basico de las delegaciones realizadas") y base
de la observabilidad que exige S3-06 ("logs o trazas suficientes para
reconstruir el flujo de una solicitud").

POR QUE PERSISTIR Y NO SOLO LOGUEAR

El orquestador ya escribe en el log de la aplicacion, pero un log de servidor
se pierde entre reinicios, no se puede consultar desde la demo y obliga a tener
acceso a la maquina. Guardar la traza en Firestore la vuelve consultable: la
evaluacion de S3-06 puede recorrer las delegaciones de una corrida completa, y
la demo de S3-07 puede mostrar el recorrido de una solicitud sin abrir una
terminal.

Se guarda una traza por solicitud del corredor, identificada por traza_id. Un
flujo con dos agentes produce UN documento con dos pasos, no dos documentos:
la unidad de analisis es la solicitud, no la invocacion.

NUNCA ROMPE LA SOLICITUD

Registrar es una operacion auxiliar. Si Firestore falla, la conversacion debe
continuar: el corredor no tiene por que quedarse sin respuesta porque no se
pudo escribir una traza. Es la misma politica que la correccion S2-04 aplico a
las herramientas y S3-02 a los agentes, aplicada ahora a la observabilidad.
"""

import logging

from src.database.firestore_client import db

logger = logging.getLogger(__name__)

COLECCION = "delegaciones"


class RegistroDelegaciones:
    """Persiste la traza de cada solicitud atendida por el orquestador."""

    def registrar(self, traza: dict) -> bool:
        """Guarda la traza. Devuelve si lo consiguio.

        El valor de retorno existe para las pruebas y para que quien llame
        pueda decidir si le importa; el orquestador lo ignora a proposito.
        """
        traza_id = traza.get("trazaId")
        if not traza_id:
            logger.error("Se intento registrar una traza sin trazaId; se descarta.")
            return False

        try:
            db.collection(COLECCION).document(traza_id).set(traza)
            return True
        except Exception:
            logger.exception(
                "No se pudo registrar la traza %s. La solicitud continua igual.",
                traza_id,
            )
            return False