---
doc_id: KB-005
titulo: Tapering y puesta a punto para competición
categoria: tapering
nivel_evidencia: alto
idioma: es
version: "1.0"
fecha_curacion: 2026-08-10
entidades_ontologia:
  - FaseEntrenamiento
  - CargaEntrenamiento
  - Objetivo
conceptos_taxonomia:
  - fases_entrenamiento
  - distancias_objetivo
referencias:
  - "Bosquet L, Montpetit J, Arvisais D, Mujika I. Effects of tapering on performance: a meta-analysis. Med Sci Sports Exerc (2007)"
  - "Mujika I, Padilla S. Scientific bases for precompetition tapering strategies. Med Sci Sports Exerc (2003)"
  - "Mujika I. Intense training: the key to optimal performance before and during the taper. Scand J Med Sci Sports (2010)"
---

# Tapering y puesta a punto para competición

## Definición

El tapering es la reducción progresiva de la carga de entrenamiento en el periodo previo a una competición objetivo. Su finalidad es permitir la disipación de la fatiga acumulada preservando las adaptaciones fisiológicas conseguidas durante las fases previas.

Es una de las intervenciones con **mejor respaldo empírico** de todo el dominio del entrenamiento de resistencia, en contraste con otras prácticas ampliamente difundidas pero débilmente sustentadas.

## El modelo fitness-fatiga

El fundamento conceptual del tapering es el modelo de dos componentes: el rendimiento en un momento dado resulta de la diferencia entre el nivel de forma acumulada y la fatiga residual.

La clave está en que ambos componentes tienen **cinéticas distintas**. La fatiga se disipa considerablemente más rápido de lo que se pierde la forma. Por eso existe una ventana en la que reducir la carga elimina la fatiga sin que la forma haya decaído todavía de manera apreciable — y el rendimiento neto alcanza su máximo.

El tapering consiste precisamente en situar la competición dentro de esa ventana.

## Parámetros óptimos según la evidencia

El metaanálisis de referencia sobre efectos del tapering en el rendimiento estableció los siguientes parámetros:

| Variable | Recomendación | Nota |
|----------|--------------|------|
| **Volumen** | Reducción del **41% al 60%** | Es la variable que debe reducirse |
| **Intensidad** | **Se mantiene sin cambios** | Reducirla degrada el resultado |
| **Frecuencia** | **Se mantiene sin cambios** | Reducirla degrada el resultado |
| **Duración** | **2 semanas** aproximadamente | Rango útil de 8 a 14 días |
| **Progresión** | Reducción progresiva, no abrupta | El taper exponencial supera al escalonado |

La mejora de rendimiento asociada a un tapering correctamente ejecutado se sitúa en torno al **3%** en promedio, con un rango reportado aproximado del 0.5% al 6%.

Un 3% de mejora es una magnitud considerable en el contexto del rendimiento de resistencia — equivale a varios minutos en una maratón.

## Los tres errores característicos

### 1. Reducir la intensidad

Es el error más frecuente y el más costoso. La intuición sugiere que descansar implica bajar el ritmo, pero la evidencia es consistente: **la intensidad debe mantenerse**. Es el estímulo que preserva las adaptaciones neuromusculares y metabólicas conseguidas.

El tapering correcto reduce cuánto se corre, no a qué velocidad.

### 2. Reducir la frecuencia de sesiones

Espaciar los entrenamientos altera el patrón habitual y no aporta beneficio adicional sobre la reducción de volumen. Mantener el número de sesiones, acortándolas, es la aproximación respaldada.

### 3. Extender el tapering demasiado

Más allá de aproximadamente dos semanas, la pérdida de forma comienza a superar el beneficio de la disipación de fatiga. Un tapering de cuatro semanas típicamente rinde peor que uno de dos.

## Ejemplo de aplicación

Corredor con volumen habitual de 60 km semanales, con maratón como objetivo:

| Semana | Volumen | Trabajo de calidad |
|--------|---------|-------------------|
| S-3 (última de carga) | 60 km | Normal |
| S-2 | ~40 km (-33%) | Se mantiene la intensidad, series más cortas |
| S-1 | ~28 km (-53%) | Sesión corta de ritmo objetivo |
| Semana de competición | ~15 km + carrera | Activaciones breves |

Obsérvese que el número de sesiones no disminuye y que el trabajo de calidad permanece en el programa, solo que con menor volumen total.

## Relación con la distancia objetivo

La duración del tapering guarda relación con la exigencia del evento:

| Distancia | Duración orientativa |
|-----------|---------------------|
| 5K | 5 a 7 días |
| 10K | 7 a 10 días |
| Media maratón | 10 a 14 días |
| Maratón | 14 a 21 días |

Para maratón se admite una ventana algo más extensa dada la magnitud de la fatiga acumulada en la fase de construcción.

## Fase de transición posterior

Tras la competición objetivo corresponde un periodo de transición de una a tres semanas con volumen mínimo y trabajo exclusivamente en Z1 y Z2. Su función es permitir la recuperación completa —fisiológica y psicológica— antes de iniciar un nuevo macrociclo.

Omitir la transición es un factor asociado a sobreentrenamiento acumulativo a lo largo de temporadas sucesivas.

## Aplicación al sistema de recomendación

El sistema puede determinar automáticamente si el corredor debe estar en tapering:

```
semanas_restantes = (fecha_meta - fecha_actual) / 7

si semanas_restantes <= 3:
    fase = tapering
    volumen_objetivo = volumen_habitual * (1 - reduccion_progresiva)
    intensidad = sin cambios
    frecuencia = sin cambios
```

Es una de las inferencias de mayor valor que el sistema puede ofrecer, porque el tapering tiene respaldo sólido, parámetros cuantificables y es frecuentemente ejecutado de forma incorrecta por corredores recreativos.

Requiere que el objetivo del corredor incluya fecha meta registrada.
