"""Repositorio de acceso a datos del corredor.

Concentra todas las consultas a Firestore relacionadas con el estado de un
corredor (perfil, sesiones, carga semanal, objetivos). Antes de esta
extracción, esta lógica vivía duplicada dentro de WellnessAgent; con el
Wellness Coach Agent 2.0 sumándose como segundo consumidor de los mismos
datos, mantenerla en un solo lugar evita que ambos agentes terminen con
copias divergentes de las mismas cuatro consultas.

Nota sobre consultas a Firestore: se evita deliberadamente combinar 'where'
con 'order_by' o múltiples 'where' sobre campos distintos, porque Firestore
exige índices compuestos para esos casos. Se filtra por userId y se resuelve
el resto en memoria: con decenas de documentos por usuario el costo es
despreciable y elimina una dependencia de configuración manual.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from google.cloud.firestore import FieldFilter

from src.database.firestore_client import db


@dataclass
class PerfilCorredor:
    """Perfil declarado del corredor.

    Los campos toman un valor por defecto en vez de lanzar una excepción
    cuando faltan, porque perfiles creados antes de agregar un campo nuevo
    (como 'ciudad') no lo tendrán en Firestore.
    """

    uid: str
    email: str = ""
    nombre: str = ""
    peso: float | None = None
    edad: int | None = None
    nivel: str = "no declarado"
    ciudad: str | None = None

    @classmethod
    def desde_documento(cls, uid: str, datos: dict) -> "PerfilCorredor":
        """Construye un perfil a partir del dict crudo de Firestore.

        Aísla en un solo lugar la decisión de qué valor por defecto usar
        cuando un campo no está presente.
        """
        return cls(
            uid=uid,
            email=datos.get("email", ""),
            nombre=datos.get("nombre", ""),
            peso=datos.get("peso"),
            edad=datos.get("edad"),
            nivel=datos.get("nivel") or "no declarado",
            ciudad=datos.get("ciudad"),
        )


@dataclass
class EstadoCorredor:
    """Estado consolidado de un corredor, listo para pasar a un agente.

    Reúne en una sola estructura lo que antes se armaba como un dict ad hoc
    dentro de WellnessAgent._cargar_estado().
    """

    sessions: list[dict]
    current_km: float
    previous_km: float
    goals: list[dict]
    nivel: str
    ciudad: str | None = None


class RepositorioCorredor:
    """Acceso a los datos de entrenamiento de un corredor en Firestore."""

    def obtener_perfil(self, user_id: str) -> PerfilCorredor:
        doc = db.collection("users").document(user_id).get()
        datos = doc.to_dict() if doc.exists else {}
        return PerfilCorredor.desde_documento(user_id, datos)

    def _sesiones_de_usuario(self, user_id: str) -> list[dict]:
        """Todas las sesiones del usuario, ordenadas por fecha descendente.

        Filtro simple por userId (no requiere índice compuesto) y ordenación
        en memoria.
        """
        docs = (
            db.collection("sessions")
            .where(filter=FieldFilter("userId", "==", user_id))
            .stream()
        )
        sesiones = [d.to_dict() for d in docs]
        return sorted(sesiones, key=lambda s: str(s.get("fecha", "")), reverse=True)

    def obtener_sesiones_recientes(self, user_id: str, n: int = 5) -> list[dict]:
        return self._sesiones_de_usuario(user_id)[:n]

    def calcular_carga_semanal(self, user_id: str) -> tuple[float, float]:
        """Kilometraje de la semana actual y de la anterior."""
        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        last_monday = monday - timedelta(weeks=1)
        last_sunday = monday - timedelta(days=1)

        sesiones = self._sesiones_de_usuario(user_id)

        def km_entre(inicio, fin) -> float:
            total = 0.0
            for s in sesiones:
                fecha = str(s.get("fecha", ""))[:10]
                if str(inicio) <= fecha <= str(fin):
                    total += s.get("distanciaKm", 0) or 0
            return round(total, 2)

        return km_entre(monday, today), km_entre(last_monday, last_sunday)

    def obtener_objetivos_activos(self, user_id: str) -> list[dict]:
        """Objetivos activos del usuario. Filtro de 'activo' en memoria."""
        docs = (
            db.collection("goals")
            .where(filter=FieldFilter("userId", "==", user_id))
            .stream()
        )
        return [g for g in (d.to_dict() for d in docs) if g.get("activo", True)]

    def cargar_estado_corredor(self, user_id: str) -> EstadoCorredor | None:
        """Reúne todos los datos del corredor. None si no hay sesiones."""
        sessions = self.obtener_sesiones_recientes(user_id)
        if not sessions:
            return None

        current_km, previous_km = self.calcular_carga_semanal(user_id)
        perfil = self.obtener_perfil(user_id)

        return EstadoCorredor(
            sessions=sessions,
            current_km=current_km,
            previous_km=previous_km,
            goals=self.obtener_objetivos_activos(user_id),
            nivel=perfil.nivel,
            ciudad=perfil.ciudad,
        )


if __name__ == "__main__":
    # Prueba de humo contra Firestore real. Requiere credenciales de GCP
    # válidas y al menos un usuario con sesiones registradas. No se puede
    # ejecutar todavía sin credenciales propias; la verificación de esta
    # pieza se hace por ahora con tests/unit/test_repositorio_corredor.py.
    import sys

    repo = RepositorioCorredor()
    uid_prueba = sys.argv[1] if len(sys.argv) > 1 else "usuario-demo"

    print(f"Consultando estado de '{uid_prueba}'...\n")
    estado = repo.cargar_estado_corredor(uid_prueba)

    if estado is None:
        print("Sin sesiones registradas para este usuario.")
    else:
        print(f"Nivel             : {estado.nivel}")
        print(f"Ciudad            : {estado.ciudad}")
        print(f"Carga actual      : {estado.current_km} km")
        print(f"Carga anterior    : {estado.previous_km} km")
        print(f"Objetivos activos : {len(estado.goals)}")
        print(f"Sesiones recientes: {len(estado.sessions)}")