"""Memoria conversacional de largo plazo del Wellness Coach Agent.

Se usa un unico hilo de conversacion por corredor (conversation_id == user_id):
simplifica el modelo de datos para el alcance de este sprint. Gestionar
multiples conversaciones paralelas por usuario no fue pedido por el issue #12
y se deja como posible extension futura.

Persistida en Firestore, coleccion 'conversations', un documento por usuario
con un arreglo 'turnos'. Se recorta a MAX_TURNOS_PERSISTIDOS para no crecer
sin limite; se expone al modelo solo una ventana reciente (VENTANA_CONTEXTO)
para no inflar el prompt con historial completo en cada turno.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from src.database.firestore_client import db

MAX_TURNOS_PERSISTIDOS = 50
VENTANA_CONTEXTO = 10

ROLES_VALIDOS = ("usuario", "agente")


@dataclass
class TurnoConversacion:
    rol: str
    contenido: str
    timestamp: str


class MemoriaConversacional:
    """Historial de conversacion persistido por corredor."""

    def _referencia(self, user_id: str):
        return db.collection("conversations").document(user_id)

    def obtener_historial(self, user_id: str, n: int = VENTANA_CONTEXTO) -> list[TurnoConversacion]:
        doc = self._referencia(user_id).get()
        if not doc.exists:
            return []
        turnos_crudos = doc.to_dict().get("turnos", [])
        turnos = [TurnoConversacion(**t) for t in turnos_crudos]
        return turnos[-n:]

    def agregar_turno(self, user_id: str, rol: str, contenido: str) -> None:
        if rol not in ROLES_VALIDOS:
            raise ValueError(f"Rol invalido '{rol}'. Debe ser uno de {ROLES_VALIDOS}.")

        ref = self._referencia(user_id)
        doc = ref.get()
        turnos = doc.to_dict().get("turnos", []) if doc.exists else []

        nuevo = TurnoConversacion(
            rol=rol,
            contenido=contenido,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        turnos.append(asdict(nuevo))
        turnos = turnos[-MAX_TURNOS_PERSISTIDOS:]

        ref.set({
            "userId": user_id,
            "turnos": turnos,
            "actualizadoEn": datetime.now(timezone.utc).isoformat(),
        })

    def formatear_para_prompt(self, turnos: list[TurnoConversacion]) -> str:
        """Representacion en texto plano del historial, lista para insertar
        en el prompt del modelo."""
        if not turnos:
            return "Sin conversacion previa."
        lineas = []
        for t in turnos:
            etiqueta = "Corredor" if t.rol == "usuario" else "RunCoach"
            lineas.append(f"{etiqueta}: {t.contenido}")
        return "\n".join(lineas)

    def limpiar_historial(self, user_id: str) -> None:
        """Reinicia la conversacion de un corredor."""
        self._referencia(user_id).delete()


if __name__ == "__main__":
    # Prueba de humo contra Firestore real. Requiere credenciales de GCP.
    memoria = MemoriaConversacional()
    uid_prueba = "usuario-demo-memoria"

    memoria.limpiar_historial(uid_prueba)
    memoria.agregar_turno(uid_prueba, "usuario", "Hola, quiero saber si debo entrenar hoy")
    memoria.agregar_turno(uid_prueba, "agente", "Cuentame como te sientes primero")

    historial = memoria.obtener_historial(uid_prueba)
    print(memoria.formatear_para_prompt(historial))