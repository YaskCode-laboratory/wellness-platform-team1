"""Cliente Firestore de la plataforma."""

import firebase_admin
from firebase_admin import credentials, firestore

from src.utils.config import GCP_PROJECT


def init_firebase() -> firestore.Client:
    """Inicializa la app de Firebase (si no existe) y devuelve el cliente Firestore."""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {"projectId": GCP_PROJECT})
    return firestore.client()


class _ClienteFirestorePerezoso:
    """Envoltura que retrasa la conexión real a Firestore hasta el primer uso.

    Antes, la línea `db = init_firebase()` se ejecutaba al importar este
    módulo, lo que disparaba una conexión real a Firestore incluso cuando
    solo se necesitaba importar el módulo (por ejemplo, en tests con mocks
    de otros componentes que dependen indirectamente de este). Con esta
    envoltura, `db.collection(...)` sigue funcionando exactamente igual
    para quien ya lo usa así en agent.py, agent_routes.py y auth_service.py
    — la conexión real ocurre en el primer acceso, no al importar.

    IMPORTANTE: se excluyen explícitamente los nombres que empiezan con
    guion bajo (privados o "dunder", como __func__ o _is_coroutine_marker)
    de disparar la conexión. Herramientas de introspección como
    unittest.mock consultan varios de estos atributos internos antes de
    reemplazar un objeto por un mock, y esa consulta pasa por __getattr__
    igual que un uso real. Sin esta exclusión, el solo hecho de mockear
    este objeto en un test dispara una conexión real a Firestore. El
    cliente real de Firestore tampoco expone su API pública con nombres
    de guion bajo, así que responder "no existe" aquí es seguro.
    """

    def __init__(self) -> None:
        self._cliente: firestore.Client | None = None

    def _obtener_cliente(self) -> firestore.Client:
        if self._cliente is None:
            self._cliente = init_firebase()
        return self._cliente

    def __getattr__(self, nombre):
        if nombre.startswith("_"):
            raise AttributeError(nombre)
        return getattr(self._obtener_cliente(), nombre)


db = _ClienteFirestorePerezoso()