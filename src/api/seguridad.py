"""Verificacion de identidad de las peticiones a la API.

EL HUECO QUE CIERRA ESTE MODULO

Hasta ahora el backend no verificaba nada. El frontend enviaba
'Authorization: Bearer <idToken>' en cada llamada -- lo hace desde el Sprint 1,
en authHeader() de api.js -- y el backend lo recibia y lo ignoraba. Ningun
endpoint llamaba a verify_id_token.

Combinado con que el servicio de Cloud Run se publica con
--allow-unauthenticated, que el CORS acepta cualquier origen, y que todos los
endpoints toman el identificador del corredor de la ruta o del cuerpo, el
efecto era que cualquiera que conociera un uid podia leer y escribir el perfil,
las sesiones, los objetivos y el historial de chat de ese corredor con un curl.

Las reglas de seguridad de Firestore no cubren esto: el backend usa el Admin
SDK, que las salta por diseno. La unica capa posible es esta.

DOS COMPROBACIONES, NO UNA

Autenticar y autorizar son cosas distintas y aqui hacen falta las dos:

1. Que el token sea valido y lo haya emitido Firebase para este proyecto.
   Sin esto, cualquiera fabrica una cabecera.
2. Que el uid del token coincida con el corredor cuyos datos se piden.
   Sin esto, un usuario legitimo puede leer los datos de otro con solo
   cambiar el identificador de la URL. Es el caso mas probable en la
   practica, porque no exige saber falsificar nada.

DE DONDE SALE EL IDENTIFICADOR DEL CORREDOR

De la ruta en casi todos los endpoints, pero POST /sessions y POST /goals lo
reciben en el cuerpo. Por eso la comprobacion de propiedad se expone tambien
como funcion suelta, exigir_mismo_uid(), que esos dos handlers invocan sobre
el campo del cuerpo. Una dependencia que solo mirara la ruta habria dejado
sin proteger justo las dos escrituras.
"""

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth

from src.database.firestore_client import init_firebase

logger = logging.getLogger(__name__)

# auto_error=False para responder 401 con un mensaje propio en vez del 403 que
# FastAPI devuelve por defecto ante una cabecera ausente. Un 403 sin token
# sugiere "no tienes permiso" cuando lo correcto es "no te has identificado",
# y esa diferencia importa para quien depura desde el frontend.
_esquema = HTTPBearer(auto_error=False)

# Nombres con los que los endpoints identifican al corredor en la ruta. El
# microservicio de auth uso 'uid' y los demas 'userId'; unificarlos habria
# cambiado URLs que el frontend ya consume.
_PARAMETROS_DE_CORREDOR = ("userId", "uid")

CREDENCIALES_AUSENTES = "Falta la cabecera Authorization con el token de sesion."
TOKEN_INVALIDO = "El token de sesion no es valido o ha expirado."
NO_ES_TU_CUENTA = "No puedes acceder a los datos de otro corredor."


def uid_autenticado(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema),
) -> str:
    """Verifica el token de Firebase y devuelve el uid que declara.

    No comprueba de quien son los datos que se piden: eso es autorizacion y lo
    hace exigir_propiedad(). Se separan para que un endpoint que algun dia
    necesite solo estar autenticado pueda depender unicamente de esta.
    """
    if credenciales is None or not credenciales.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENCIALES_AUSENTES,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Firebase Admin necesita la app inicializada para verificar. Es idempotente
    # y perezosa: si ya lo esta, no hace nada.
    init_firebase()

    try:
        declarado = firebase_auth.verify_id_token(credenciales.credentials)
    except Exception:
        # Se captura de forma amplia a proposito. verify_id_token distingue
        # entre token expirado, revocado, mal formado y firmado por otro
        # proyecto, y esa diferencia le sirve a quien depura, no a quien
        # llama: detallarla en la respuesta le dice a un atacante por que
        # exactamente fallo su intento. El detalle va al log.
        logger.warning("Token rechazado", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=TOKEN_INVALIDO,
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = declarado.get("uid")
    if not uid:
        logger.error("Token verificado sin uid: %s", sorted(declarado))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=TOKEN_INVALIDO
        )

    return uid


def exigir_mismo_uid(uid_token: str, uid_solicitado: str) -> None:
    """Falla si el token no pertenece al corredor cuyos datos se piden.

    Se expone suelta, y no solo dentro de la dependencia, porque POST
    /sessions y POST /goals reciben el userId en el cuerpo y no en la ruta.
    """
    if uid_token != uid_solicitado:
        logger.warning(
            "El corredor %s intento acceder a datos de %s", uid_token, uid_solicitado
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=NO_ES_TU_CUENTA
        )


def exigir_propiedad(
    request: Request, uid: str = Depends(uid_autenticado)
) -> str:
    """Autentica y, si la ruta nombra un corredor, comprueba que sea el mismo.

    Se monta a nivel de router para que un endpoint nuevo quede protegido por
    el hecho de registrarse, sin que nadie tenga que acordarse de anadir la
    dependencia. Es la misma leccion que S2-04 dejo sobre proteger en el punto
    de despacho y no en cada destino.

    Cuando la ruta no nombra ningun corredor -- POST /sessions, POST /goals --
    esta dependencia solo autentica, y el handler completa la comprobacion con
    exigir_mismo_uid() sobre el campo del cuerpo.
    """
    for nombre in _PARAMETROS_DE_CORREDOR:
        solicitado = request.path_params.get(nombre)
        if solicitado is not None:
            exigir_mismo_uid(uid, solicitado)
            break

    return uid
