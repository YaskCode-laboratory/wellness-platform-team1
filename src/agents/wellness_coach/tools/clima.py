"""Herramienta de clima via Open-Meteo (sin API key, sin registro).

Dos llamadas: geocodificacion (nombre de ciudad -> coordenadas) y pronostico
(coordenadas -> condiciones actuales). Ninguna requiere autenticacion, lo
que evita introducir un segundo frente de gestion de credenciales ademas
de las de GCP.

CORRECCION #13 (hallazgo D, segunda medicion real #15): un 500 real de
Open-Meteo tumbo la conversacion completa del agente -- raise_for_status()
sin captura propagaba la excepcion por toda la pila (consultar_clima ->
despachar -> conversar), dejando al usuario sin respuesta aunque el agente
tuviera otras tres fuentes de informacion disponibles (historial, progreso,
base de conocimiento). El agente esta disenado para razonar con informacion
parcial; una herramienta que consulta un servicio externo debe degradar,
no propagar.

Se aplica a ambas llamadas de red (geocodificacion y pronostico) el mismo
contrato {"disponible": False, "mensaje": ...} que ya usaban los casos de
ciudad ausente y geocodificacion sin resultados -- el modelo ya sabe
interpretarlo (lo demostro en la primera medicion, AG-07). Se captura
requests.RequestException (engloba HTTPError, Timeout, ConnectionError,
TooManyRedirects) y ValueError (respuesta 200 con cuerpo no-JSON o mal
formado). Deliberadamente NO se agregan reintentos con backoff: multiplican
la latencia de una conversacion que ya promedia varios segundos, y el
agente tiene otras fuentes con las que responder sin el clima.
"""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

TIMEOUT_SEGUNDOS = 5

MENSAJE_SERVICIO_NO_DISPONIBLE = "El servicio de clima no está disponible en este momento."


def _geocodificar(ciudad: str) -> tuple[float, float] | None:
    """Devuelve coordenadas de la ciudad, o None si no se pudo resolver.

    None cubre tanto "la ciudad no existe en el servicio de geocodificacion"
    como "el servicio de geocodificacion fallo" -- ambos casos se degradan
    igual en consultar_clima, no hace falta distinguirlos aqui.
    """
    try:
        resp = requests.get(GEOCODING_URL, params={"name": ciudad, "count": 1}, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        resultados = resp.json().get("results")
    except (requests.RequestException, ValueError):
        return None

    if not resultados:
        return None
    primero = resultados[0]
    return primero["latitude"], primero["longitude"]


def consultar_clima(ciudad: str | None) -> dict:
    """Condiciones climaticas actuales de la ciudad del corredor.

    Si el corredor no tiene ciudad registrada, si la ciudad no se pudo
    geocodificar, o si el servicio de pronostico falla, se devuelve un
    mensaje explicito en vez de propagar una excepcion -- en los tres casos
    el agente puede seguir la conversacion con sus otras fuentes de datos.
    """
    if not ciudad:
        return {
            "disponible": False,
            "mensaje": "El corredor no tiene ciudad registrada en su perfil.",
        }

    coords = _geocodificar(ciudad)
    if coords is None:
        return {
            "disponible": False,
            "mensaje": f"No se encontraron coordenadas para '{ciudad}'.",
        }

    lat, lon = coords

    try:
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
            },
            timeout=TIMEOUT_SEGUNDOS,
        )
        resp.raise_for_status()
        actual = resp.json().get("current", {})
    except (requests.RequestException, ValueError):
        return {
            "disponible": False,
            "mensaje": MENSAJE_SERVICIO_NO_DISPONIBLE,
        }

    return {
        "disponible": True,
        "ciudad": ciudad,
        "temperaturaC": actual.get("temperature_2m"),
        "precipitacionMm": actual.get("precipitation"),
        "vientoKmh": actual.get("wind_speed_10m"),
    }