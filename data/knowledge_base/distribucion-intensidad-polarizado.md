---
doc_id: KB-003
titulo: Distribución de intensidad y entrenamiento polarizado
categoria: distribucion_intensidad
nivel_evidencia: alto
idioma: es
version: "1.0"
fecha_curacion: 2026-08-10
entidades_ontologia:
  - ZonaIntensidad
  - FaseEntrenamiento
  - Sesion
conceptos_taxonomia:
  - zonas_intensidad
  - fases_entrenamiento
  - niveles_corredor
referencias:
  - "Seiler S. Análisis sistemático de la distribución de intensidad en atletas de resistencia de élite"
  - "Fitzgerald M. 80/20 Running (2014)"
  - "Esteve-Lanao J, Zapico AG, Billat V. Estudios sobre distribución de intensidad en corredores de fondo"
  - "FastTalk Labs. Complete Guide to Polarized Training with Dr. Stephen Seiler"
  - "Outside Online. The Case For (and Against) Polarized Training"
---

# Distribución de intensidad y entrenamiento polarizado

## El problema que resuelve

Dado un volumen semanal determinado, ¿cómo debe repartirse entre intensidades? Esta pregunta es independiente de cuánto se entrena y con frecuencia más determinante para el resultado.

La distribución de intensidad describe qué proporción del volumen total se ejecuta en cada región fisiológica.

## Origen del modelo polarizado

El fisiólogo del ejercicio Stephen Seiler fue el primero en analizar sistemáticamente la distribución de intensidad de atletas de resistencia de élite. Su aportación inicial fue **descriptiva, no prescriptiva**: no diseñó una teoría de entrenamiento, sino que documentó lo que los mejores atletas ya hacían.

El hallazgo fue consistente y contraintuitivo. Los atletas de élite de resistencia realizan aproximadamente el **80% de su entrenamiento a baja intensidad** y el **20% restante a intensidad alta**. La zona intermedia — donde muchos deportistas recreativos concentran su trabajo — está notablemente subrepresentada.

El modelo se popularizó bajo la denominación 80/20 tras el libro homónimo de Matt Fitzgerald (2014), que agrupa las dos zonas superiores en una sola categoría "duro".

## Formulación del modelo

En términos de los umbrales fisiológicos:

| Región | Proporción del volumen | Zonas |
|--------|----------------------|-------|
| Baja intensidad (sub-LT1) | ~80% | Z1, Z2 |
| Alta intensidad (sobre-LT2) | ~20% | Z5, parte de Z4 |
| Intensidad media (entre umbrales) | Minoritaria | Z3 |

La proporción se calcula habitualmente sobre **tiempo de entrenamiento**, no sobre número de sesiones ni sobre distancia. Esta distinción importa: una sesión de intervalos ocupa poco tiempo total pero constituye una porción significativa del trabajo de alta intensidad.

## Base fisiológica

El fundamento del modelo descansa en dos observaciones:

**1. El volumen a baja intensidad produce adaptaciones centrales con coste de fatiga bajo.** El trabajo sub-LT1 desarrolla densidad mitocondrial, capilarización y capacidad oxidativa sin generar el estrés neuromuscular ni la demanda de recuperación del trabajo intenso. Permite acumular volumen sostenidamente.

**2. El estímulo de alta intensidad es necesario pero tiene rendimientos decrecientes rápidos.** El trabajo sobre LT2 es el que eleva el consumo máximo de oxígeno y la economía de carrera, pero su coste de recuperación es alto. Incrementar su proporción más allá de cierto punto degrada la calidad de las sesiones y compromete la absorción del estímulo.

La zona intermedia queda atrapada entre ambos: demasiado exigente para acumular volumen, insuficientemente intensa para maximizar la adaptación de alta intensidad.

## Evidencia de respaldo

Los trabajos de Billat, Zapico y Esteve-Lanao, entre otros, han corroborado la observación original de Seiler en poblaciones de corredores de fondo. La evidencia disponible indica que la distribución polarizada resulta más efectiva que distribuciones con mayor proporción de trabajo en zona media para producir mejoras en métricas clave de rendimiento de resistencia, y reduce la probabilidad de estancamiento.

El nivel de evidencia para el modelo polarizado es **alto** en poblaciones de atletas entrenados. La extrapolación a corredores principiantes con volúmenes muy bajos requiere matices.

## Objeciones y matices

El modelo no está exento de debate:

- **Dependencia de la definición de zonas.** La proporción resultante varía sustancialmente según cómo se delimiten las regiones. Un mismo entrenamiento puede clasificarse como polarizado o piramidal según el criterio empleado.
- **Distribución piramidal como alternativa.** Algunos programas de élite muestran una distribución piramidal — mucho volumen bajo, cantidad intermedia de umbral, poco trabajo máximo — con resultados comparables. El debate entre modelo polarizado y piramidal sigue abierto.
- **Aplicabilidad a volúmenes bajos.** En un corredor que entrena tres horas semanales, el 20% equivale a 36 minutos. La granularidad del modelo se vuelve gruesa en volúmenes reducidos.
- **Variación por fase.** La distribución óptima no es constante a lo largo del macrociclo; la fase de construcción específica desplaza la proporción hacia trabajo de calidad.

## Error frecuente: la deriva hacia la intensidad media

El patrón de error más común en corredores recreativos consiste en ejecutar los días fáciles demasiado rápido y los días duros demasiado lentos. El resultado es que la mayor parte del volumen termina en Z3.

Las consecuencias:

- Los rodajes dejan de ser suficientemente suaves para permitir recuperación
- Las sesiones de calidad se ejecutan con fatiga residual y no alcanzan la intensidad objetivo
- La fatiga se acumula sin el estímulo adaptativo que la justificaría

La corrección requiere disciplina en ambos extremos: **más lento en los días fáciles, más rápido en los días duros**.

## Aplicación por fase de entrenamiento

| Fase | Distribución orientativa | Énfasis |
|------|-------------------------|---------|
| Base | 85–90% baja / 10–15% alta | Construcción de volumen aeróbico |
| Construcción específica | 75–80% baja / 20–25% alta | Introducción progresiva de trabajo en Z4 y Z5 |
| Tapering | 80% baja / 20% alta | Se mantiene la proporción, se reduce el volumen |
| Transición | 100% baja | Solo Z1 y Z2 |

## Aplicación al sistema de recomendación

Para evaluar la distribución de intensidad de un corredor el sistema requiere:

- Clasificación por zona de cada sesión del periodo analizado
- Duración de cada sesión (la proporción se calcula sobre tiempo)
- Ventana temporal de análisis suficiente — un mínimo de dos a tres semanas para que la proporción sea representativa

Una desviación sostenida hacia Z3 es un hallazgo accionable: justifica una recomendación de reducir el ritmo de los rodajes antes que de modificar el volumen.
