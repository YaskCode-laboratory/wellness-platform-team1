"""Fecha y hora de la plataforma, en la zona horaria del corredor.

EL DEFECTO QUE CIERRA ESTE MODULO

El sistema razonaba sobre el calendario en UTC. 'repositorio_corredor' usaba
datetime.utcnow().date() y 'metrics_service' un _hoy() equivalente, mientras
que los prompts de los agentes usaban date.today(), que en Cloud Run tambien
es UTC porque el contenedor corre en esa zona.

Los corredores de esta plataforma estan en Venezuela, UTC-4. La consecuencia:
cada dia, a partir de las ocho de la noche hora local, el backend cree que ya
es el dia siguiente. Y el domingo a esa hora empieza una semana nueva, de modo
que el kilometraje semanal del corredor se reinicia cuatro horas antes de
tiempo -- justo en la franja en que alguien sale a correr y entra a registrar
la sesion.

No es un detalle de presentacion: 'esta semana' decide que sesiones cuentan
para la carga, que carga se compara con la meta, y que datos recibe el agente
para razonar sobre progresion. Una semana mal delimitada produce una
recomendacion mal fundada.

POR QUE LAS PRUEBAS NO LO DETECTABAN

Porque comparaban contra date.today(), que en el portatil de quien las corre
es hora local. Pasaban dieciseis horas al dia y fallaban ocho, y en CI pasaban
siempre porque el runner de GitHub esta en UTC. Una comprobacion cuyo
resultado depende de la hora a la que se ejecute no esta verificando lo que
dice verificar.

QUE VA EN ZONA LOCAL Y QUE NO

La distincion importa y no es la misma respuesta para todo:

- El CALENDARIO va en la zona del corredor. Que dia es hoy, en que semana
  estamos, cuantos dias hace de una sesion. Son preguntas sobre la vida del
  corredor y se responden donde el corredor vive.

- Los INSTANTES van en UTC. 'createdAt', 'updatedAt', 'generadoEn': marcan
  cuando ocurrio algo, se ordenan y se comparan entre si, y no dependen de
  donde estuviera nadie. Guardarlos en hora local seria el error simetrico.

Por eso este modulo expone las dos cosas por separado, con nombres que dicen
cual es cual.
"""

import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Configurable por si la plataforma se usa desde otra region. El valor por
# defecto es donde estan hoy sus usuarios: no se elige UTC como "neutral"
# porque UTC no es neutral para nadie -- es simplemente la zona de otro sitio.
ZONA_HORARIA = ZoneInfo(os.getenv("ZONA_HORARIA", "America/Caracas"))


def hoy() -> date:
    """Fecha de hoy para el corredor.

    Toda comparacion con el campo 'fecha' de una sesion debe pasar por aqui:
    ese campo lo escribe el corredor desde la interfaz con su fecha local, asi
    que compararlo contra una fecha UTC mezcla dos calendarios distintos.
    """
    return datetime.now(ZONA_HORARIA).date()


def lunes_de_esta_semana() -> date:
    """Lunes de la semana en curso.

    La semana empieza en lunes en toda la plataforma: es lo que hace
    weekday(), lo que asume el script de siembra y lo que espera un corredor
    que planifica su carga semanal.
    """
    actual = hoy()
    return actual - timedelta(days=actual.weekday())


def dias_desde(fecha: date) -> int:
    """Dias transcurridos desde una fecha hasta hoy, en la zona del corredor."""
    return (hoy() - fecha).days


def instante_iso() -> str:
    """Marca de tiempo para persistir, en UTC y con zona explicita.

    En UTC a proposito: registra CUANDO ocurrio algo, no en que dia del
    calendario del corredor. Con zona explicita, y no con utcnow(), que
    devuelve un datetime ingenuo -- sin informacion de zona -- y esta
    deprecado desde Python 3.12.
    """
    return datetime.now(timezone.utc).isoformat()
