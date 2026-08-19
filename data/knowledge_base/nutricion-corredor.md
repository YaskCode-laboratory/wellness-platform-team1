---
doc_id: KB-006
titulo: Nutrición para el corredor de resistencia
categoria: nutricion
nivel_evidencia: alto
idioma: es
version: "1.0"
fecha_curacion: 2026-08-10
entidades_ontologia:
  - Corredor
  - Sesion
  - CargaEntrenamiento
conceptos_taxonomia:
  - tipos_sesion
  - niveles_corredor
referencias:
  - "Thomas DT, Erdman KA, Burke LM. Position of the Academy of Nutrition and Dietetics, Dietitians of Canada, and the American College of Sports Medicine: Nutrition and Athletic Performance. Med Sci Sports Exerc (2016)"
  - "Jeukendrup A. A step towards personalized sports nutrition: carbohydrate intake during exercise. Sports Med (2014)"
  - "Mountjoy M et al. IOC consensus statement on Relative Energy Deficiency in Sport (RED-S)"
  - "Burke LM et al. Carbohydrates for training and competition. J Sports Sci (2011)"
---

# Nutrición para el corredor de resistencia

## Marco general

La nutrición deportiva en resistencia se organiza alrededor de tres funciones: aportar el sustrato energético que la actividad demanda, sostener los procesos de reparación y adaptación posteriores al esfuerzo, y mantener la salud del atleta a lo largo del tiempo.

La primera es la más visible pero no necesariamente la más determinante. Los fallos nutricionales que comprometen el rendimiento a medio plazo suelen originarse en la tercera.

## Disponibilidad energética

La disponibilidad energética es la energía que queda para las funciones fisiológicas basales una vez descontado el gasto del ejercicio, normalizada por masa magra.

```
Disponibilidad energética = (ingesta energética − gasto del ejercicio) / masa magra
```

Cuando esta disponibilidad cae de forma sostenida por debajo del umbral funcional, el organismo reduce la asignación de recursos a procesos considerados no esenciales. El resultado es el cuadro descrito como **deficiencia energética relativa en el deporte (RED-S)**, cuyas manifestaciones incluyen:

- Alteración de la función endocrina y reproductiva
- Deterioro de la densidad mineral ósea, con incremento del riesgo de fractura por estrés
- Compromiso de la función inmune
- Reducción de la capacidad de adaptación al entrenamiento
- Alteración del estado de ánimo y del sueño

RED-S afecta a ambos sexos y no requiere bajo peso corporal para manifestarse. Es un cuadro subdiagnosticado en corredores recreativos que incrementan volumen sin ajustar la ingesta.

Este es un ámbito donde un sistema automatizado debe ser especialmente prudente: la detección de indicios de deficiencia energética justifica derivación a un profesional, no una recomendación generada por el sistema.

## Hidratos de carbono

### Requerimiento según carga

El aporte de hidratos de carbono se escala con el volumen de entrenamiento:

| Carga de entrenamiento | Ingesta orientativa |
|-----------------------|---------------------|
| Actividad ligera (< 1 h/día) | 3 – 5 g/kg/día |
| Moderada (~1 h/día) | 5 – 7 g/kg/día |
| Alta (1 – 3 h/día) | 6 – 10 g/kg/día |
| Muy alta (> 4 h/día) | 8 – 12 g/kg/día |

Un corredor de 70 kg con una hora diaria de entrenamiento requiere aproximadamente entre 350 y 490 g de hidratos al día.

### Durante el ejercicio

La ingesta durante el esfuerzo cobra relevancia a partir de aproximadamente una hora de duración:

| Duración del esfuerzo | Aporte recomendado |
|----------------------|-------------------|
| < 45 min | No requerido |
| 45 – 75 min | Enjuague bucal o cantidad mínima |
| 1 – 2.5 h | 30 – 60 g/h |
| > 2.5 h | Hasta 90 g/h con hidratos de transporte múltiple |

El límite de 60 g/h corresponde a la capacidad de absorción del transportador intestinal SGLT1, que se satura. Superarlo requiere combinar glucosa con fructosa, que se absorbe por el transportador GLUT5 —independiente— permitiendo tasas superiores.

La tolerancia gastrointestinal a estos aportes es entrenable y **debe ensayarse durante los entrenamientos**, nunca estrenarse el día de la competición.

## Proteína

El requerimiento en atletas de resistencia se sitúa entre **1.2 y 2.0 g/kg/día**, superior al de población sedentaria. Su función no es primordialmente el desarrollo de masa muscular sino la reparación del daño estructural inducido por el impacto repetido y el sostenimiento de las adaptaciones.

La distribución a lo largo del día — porciones de 20 a 40 g repartidas en las comidas principales — resulta más efectiva que concentrar el aporte en una sola toma.

## Recuperación posterior al esfuerzo

Tras sesiones exigentes o cuando el intervalo hasta la siguiente sesión es corto:

- **Hidratos**: 1.0 – 1.2 g/kg en las primeras horas posteriores, para restituir glucógeno
- **Proteína**: 20 – 40 g, para sostener la reparación tisular
- **Fluidos**: aproximadamente 1.25 – 1.5 L por cada kg de peso perdido durante el esfuerzo

La noción de una ventana anabólica estrecha de 30 minutos ha sido matizada por la evidencia posterior. La ventana es considerablemente más amplia de lo que se sostuvo, y lo determinante es la ingesta total diaria. La urgencia solo es real cuando hay que competir o entrenar de nuevo en pocas horas.

## Hidratación

La recomendación contemporánea se orienta a **beber según la sed** en lugar de seguir pautas fijas de volumen. La sobrehidratación con agua sin electrolitos puede derivar en hiponatremia, un cuadro potencialmente grave documentado en corredores de maratón.

Como referencia, una pérdida de peso corporal superior al 2% durante el esfuerzo se asocia a deterioro del rendimiento. Pesarse antes y después de sesiones largas permite estimar la tasa de sudoración individual.

## Micronutrientes de interés específico

**Hierro.** La deficiencia es más prevalente en corredores que en población general, por hemólisis por impacto, pérdidas por sudor y demanda incrementada. Afecta especialmente a mujeres en edad fértil. Los síntomas — fatiga, deterioro del rendimiento, elevación de la frecuencia cardíaca a ritmos habituales — se confunden fácilmente con sobreentrenamiento. Requiere confirmación por analítica; la suplementación sin diagnóstico no está indicada.

**Vitamina D.** Interviene en la salud ósea y la función muscular. La insuficiencia es frecuente en latitudes con baja exposición solar o en quienes entrenan en interiores.

**Calcio.** Relevante para la salud ósea, particularmente en presencia de disponibilidad energética reducida.

## Aplicación al sistema de recomendación

El sistema puede ofrecer orientación nutricional general vinculada a la carga registrada — por ejemplo, señalar que un incremento de volumen debería acompañarse de un incremento proporcional de la ingesta de hidratos.

Los límites deben ser explícitos. El sistema **no debe** emitir prescripciones individualizadas, diagnosticar deficiencias ni recomendar suplementación. Ante indicios de deficiencia energética relativa o sospecha de déficit de micronutrientes, la respuesta apropiada es sugerir consulta con un profesional cualificado.
