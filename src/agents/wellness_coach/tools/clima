"""Herramienta de clima via Open-Meteo (sin API key, sin registro).

Dos llamadas: geocodificacion (nombre de ciudad -> coordenadas) y pronostico
(coordenadas -> condiciones actuales). Ninguna requiere autenticacion, lo
que evita introducir un segundo frente de gestion de credenciales ademas
de las de GCP.
"""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

TIMEOUT_SEGUNDOS = 5


def _geocodificar(ciudad: str) -> tuple[float, float] | None:
    resp = requests.get(GEOCODING_URL, params={"name": ciudad, "count": 1}, timeout=TIMEOUT_SEGUNDOS)
    resp.raise_for_status()
    resultados = resp.json().get("results")
    if not resultados:
        return None
    primero = resultados[0]
    return primero["latitude"], primero["longitude"]


def consultar_clima(ciudad: str | None) -> dict:
    """Condiciones climaticas actuales de la ciudad del corredor.

    Si el corredor no tiene ciudad registrada en su perfil, se devuelve un
    mensaje explicito en vez de intentar adivinar una ubicacion.
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

    return {
        "disponible": True,
        "ciudad": ciudad,
        "temperaturaC": actual.get("temperature_2m"),
        "precipitacionMm": actual.get("precipitation"),
        "vientoKmh": actual.get("wind_speed_10m"),
    }