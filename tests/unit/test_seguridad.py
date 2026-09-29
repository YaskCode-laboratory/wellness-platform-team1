"""Pruebas de la verificacion de identidad de la API.

El hueco que cierran: hasta ahora el backend no verificaba ningun token. El
frontend enviaba 'Authorization: Bearer <idToken>' desde el Sprint 1 y el
backend lo ignoraba, de modo que cualquiera que conociera un uid podia leer y
escribir los datos de ese corredor.

Se prueban las dos mitades por separado, porque son fallos distintos:
autenticar mal deja entrar a un desconocido; autorizar mal deja que un usuario
legitimo lea los datos de otro. El segundo es el mas probable en la practica,
porque no exige falsificar nada, solo cambiar un identificador en la URL.
"""

import unittest
from unittest.mock import patch

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api import seguridad
from src.api.seguridad import exigir_mismo_uid, exigir_propiedad

UID = "corredor-legitimo"
OTRO = "corredor-ajeno"


def app_de_prueba() -> FastAPI:
    """App con las tres formas en que un endpoint identifica al corredor."""
    app = FastAPI()
    router = APIRouter(dependencies=[Depends(exigir_propiedad)])

    @router.get("/datos/{userId}")
    def por_userId(userId: str):
        return {"userId": userId}

    @router.get("/perfil/{uid}")
    def por_uid(uid: str):
        return {"uid": uid}

    @router.post("/crear")
    def por_cuerpo(payload: dict, quien: str = Depends(exigir_propiedad)):
        exigir_mismo_uid(quien, payload["userId"])
        return {"creado_para": payload["userId"]}

    @router.get("/sin_corredor")
    def sin_corredor():
        return {"ok": True}

    app.include_router(router)
    return app


class TestAutenticacion(unittest.TestCase):
    """Que el token exista, sea valido y lo haya emitido Firebase."""

    def setUp(self):
        self.cliente = TestClient(app_de_prueba())
        parche = patch.object(seguridad, "init_firebase")
        parche.start()
        self.addCleanup(parche.stop)

    def test_sin_cabecera_responde_401_y_no_403(self):
        """Un 403 sin token diria 'no tienes permiso' cuando lo correcto es
        'no te has identificado'. La diferencia importa para quien depura
        desde el frontend."""
        r = self.cliente.get(f"/datos/{UID}")

        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.headers.get("WWW-Authenticate"), "Bearer")

    @patch.object(seguridad.firebase_auth, "verify_id_token")
    def test_un_token_invalido_responde_401(self, mock_verify):
        mock_verify.side_effect = ValueError("firma incorrecta")

        with self.assertLogs(seguridad.logger, level="WARNING"):
            r = self.cliente.get(
                f"/datos/{UID}", headers={"Authorization": "Bearer falso"}
            )

        self.assertEqual(r.status_code, 401)

    @patch.object(seguridad.firebase_auth, "verify_id_token")
    def test_el_motivo_del_rechazo_no_viaja_al_cliente(self, mock_verify):
        """verify_id_token distingue entre expirado, revocado, mal formado y
        firmado por otro proyecto. Ese detalle le sirve a quien depura, no a
        quien llama: decirselo le explica a un atacante por que exactamente
        fallo su intento."""
        mock_verify.side_effect = ValueError("Token expired at 2026-09-01")

        with self.assertLogs(seguridad.logger, level="WARNING"):
            r = self.cliente.get(
                f"/datos/{UID}", headers={"Authorization": "Bearer caducado"}
            )

        self.assertNotIn("expired", r.text.lower())
        self.assertNotIn("2026-09-01", r.text)
        self.assertEqual(r.json()["detail"], seguridad.TOKEN_INVALIDO)

    @patch.object(seguridad.firebase_auth, "verify_id_token")
    def test_un_token_verificado_sin_uid_se_rechaza(self, mock_verify):
        """No deberia ocurrir con Firebase, pero si ocurriera, seguir adelante
        con uid=None compararia None contra el userId de la ruta y el
        resultado dependeria de un detalle de implementacion."""
        mock_verify.return_value = {"email": "alguien@ejemplo.com"}

        with self.assertLogs(seguridad.logger, level="ERROR"):
            r = self.cliente.get(
                f"/datos/{UID}", headers={"Authorization": "Bearer raro"}
            )

        self.assertEqual(r.status_code, 401)


class TestAutorizacion(unittest.TestCase):
    """Que el token pertenezca al corredor cuyos datos se piden."""

    def setUp(self):
        self.cliente = TestClient(app_de_prueba())
        parche = patch.object(seguridad, "init_firebase")
        parche.start()
        self.addCleanup(parche.stop)

        self.verify = patch.object(
            seguridad.firebase_auth, "verify_id_token", return_value={"uid": UID}
        ).start()
        self.addCleanup(patch.stopall)

    def cabecera(self):
        return {"Authorization": "Bearer valido"}

    def test_el_dueno_accede_a_sus_datos(self):
        r = self.cliente.get(f"/datos/{UID}", headers=self.cabecera())

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"userId": UID})

    def test_no_puede_leer_los_datos_de_otro_corredor(self):
        """El caso mas probable: no exige falsificar nada, solo cambiar el
        identificador de la URL."""
        with self.assertLogs(seguridad.logger, level="WARNING"):
            r = self.cliente.get(f"/datos/{OTRO}", headers=self.cabecera())

        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["detail"], seguridad.NO_ES_TU_CUENTA)

    def test_tambien_cubre_las_rutas_que_llaman_al_parametro_uid(self):
        """El microservicio de auth uso 'uid' y los demas 'userId'.
        Unificarlos habria cambiado URLs que el frontend ya consume, asi que
        la dependencia reconoce los dos nombres. Si solo mirara 'userId',
        /auth/user/{uid} quedaria autenticado pero sin autorizar."""
        with self.assertLogs(seguridad.logger, level="WARNING"):
            r = self.cliente.get(f"/perfil/{OTRO}", headers=self.cabecera())

        self.assertEqual(r.status_code, 403)
        self.assertEqual(
            self.cliente.get(f"/perfil/{UID}", headers=self.cabecera()).status_code, 200
        )

    def test_protege_tambien_cuando_el_userId_viaja_en_el_cuerpo(self):
        """POST /sessions y POST /goals reciben el userId en el JSON. Una
        dependencia que solo mirara la ruta habria dejado sin proteger justo
        las dos escrituras."""
        ok = self.cliente.post(
            "/crear", json={"userId": UID}, headers=self.cabecera()
        )
        self.assertEqual(ok.status_code, 200)

        with self.assertLogs(seguridad.logger, level="WARNING"):
            ajeno = self.cliente.post(
                "/crear", json={"userId": OTRO}, headers=self.cabecera()
            )

        self.assertEqual(ajeno.status_code, 403)

    def test_una_ruta_sin_corredor_solo_exige_estar_autenticado(self):
        r = self.cliente.get("/sin_corredor", headers=self.cabecera())

        self.assertEqual(r.status_code, 200)


class TestCoberturaDeLaApiReal(unittest.TestCase):
    """Toda ruta que toque datos de un corredor debe estar protegida.

    Se comprueba sobre la aplicacion real y no sobre una lista escrita a mano:
    asi, un endpoint nuevo que alguien registre sin dependencia hace fallar la
    suite en vez de publicarse abierto. Es la misma idea que las pruebas de la
    matriz de acceso de S3-05.
    """

    # Unicos endpoints que pueden responder sin token, con su motivo.
    ABIERTOS = {
        "/auth/register": "quien se registra todavia no tiene cuenta",
        "/health": "sonda de Cloud Run, no expone datos",
    }

    def test_ninguna_ruta_de_datos_queda_sin_verificacion(self):
        from fastapi.routing import APIRoute

        from src.app.main import app

        abiertas = []
        for r in app.routes:
            if not isinstance(r, APIRoute):
                continue
            if r.path in self.ABIERTOS or r.path.startswith(("/docs", "/openapi", "/redoc")):
                continue
            nombres = [getattr(d.call, "__name__", "") for d in r.dependant.dependencies]
            if "exigir_propiedad" not in nombres:
                abiertas.append(f"{sorted(r.methods)[0]} {r.path}")

        self.assertEqual(
            abiertas, [], f"Rutas sin verificacion de identidad: {abiertas}"
        )


if __name__ == "__main__":
    unittest.main()
