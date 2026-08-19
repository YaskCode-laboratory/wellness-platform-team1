# Fuentes de Conocimiento

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

---

## 1. Criterio de selección

El corpus se construyó bajo cuatro criterios explícitos:

1. **Cobertura del dominio modelado.** Cada documento corresponde a una categoría declarada en la taxonomía. No se incorporó conocimiento fuera de las dimensiones del modelo.
2. **Trazabilidad a fuentes verificables.** Cada documento declara en su front-matter las referencias bibliográficas que lo sustentan.
3. **Calificación explícita de evidencia.** Cada documento declara el nivel de respaldo de su contenido, incluyendo cuando ese respaldo es débil.
4. **Aplicabilidad al sistema.** Cada documento cierra con una sección de aplicación que especifica qué datos requiere el sistema para utilizar ese conocimiento.

---

## 2. Inventario del corpus

| ID | Documento | Categoría | Evidencia | Chunks |
|---|---|---|---|---|
| KB-001 | Carga de entrenamiento y progresión del volumen | `carga_entrenamiento` | Moderada | 13 |
| KB-002 | Zonas de intensidad y umbrales fisiológicos | `zonas_fisiologicas` | Alta | 12 |
| KB-003 | Distribución de intensidad y entrenamiento polarizado | `distribucion_intensidad` | Alta | 12 |
| KB-004 | Prevención de lesiones por sobreuso en corredores | `prevencion_lesiones` | Moderada | 14 |
| KB-005 | Tapering y puesta a punto para competición | `tapering` | Alta | 10 |
| KB-006 | Nutrición para el corredor de resistencia | `nutricion` | Alta | 10 |
| KB-007 | Recuperación y sueño en atletas de resistencia | `recuperacion` | Moderada | 11 |

**Total: 7 documentos, 82 chunks.**

---

## 3. Fuentes por documento

### KB-001 — Carga de entrenamiento y progresión

- Nielsen RO et al. *Excessive progression in weekly running distance and risk of running-related injuries*. J Orthop Sports Phys Ther (2014)
- Gabbett TJ. *The training-injury prevention paradox: should athletes be training smarter and harder?* Br J Sports Med (2016)
- Damsted C et al. *ProjectRun21: Association between running experience and running-related injury*. Int J Sports Phys Ther (2018) — PMC6253751
- Revisión sistemática y metaanálisis sobre ACWR para predicción de riesgo de lesión — PMC12487117
- *Increase in the Acute:Chronic Workload Ratio relates to Injury Risk in Competitive Runners* — PubMed 32485779

### KB-002 — Zonas de intensidad y umbrales

- Running Writings. *LT1, LT2, and the scientific basis of heart rate zones for runners* (2025)
- Running Writings. *Individual variation in heart rates at LT1 and LT2 in runners* (2025)
- *Zone 2 Intensity: A Critical Comparison of Individual Variability in Different Submaximal Exercise Intensity Boundaries* — PMC11986187
- CTS. *Blood Lactate in Training, Part 2: LT1 and Zone 2 Training*
- Friel J. Metodología de zonas basadas en frecuencia cardíaca de umbral

### KB-003 — Distribución de intensidad

- Seiler S. Análisis sistemático de la distribución de intensidad en atletas de resistencia de élite
- Fitzgerald M. *80/20 Running* (2014)
- Esteve-Lanao J, Zapico AG, Billat V. Estudios sobre distribución de intensidad en corredores de fondo
- FastTalk Labs. *Complete Guide to Polarized Training with Dr. Stephen Seiler*

### KB-004 — Prevención de lesiones

- *Risk factors for overuse injuries in short- and long-distance running: A systematic review*. J Sport Health Sci (2021)
- *Running-Related Biomechanical Risk Factors for Overuse Injuries in Distance Runners: A Systematic Review*. Sports Med (2022) — PubMed 35247202, PMC9325808
- Nielsen RO et al. *Training errors and running related injuries: a systematic review*
- Gabbett TJ. *The training-injury prevention paradox*. Br J Sports Med (2016)

### KB-005 — Tapering

- Bosquet L, Montpetit J, Arvisais D, Mujika I. *Effects of tapering on performance: a meta-analysis*. Med Sci Sports Exerc (2007)
- Mujika I, Padilla S. *Scientific bases for precompetition tapering strategies*. Med Sci Sports Exerc (2003)
- Mujika I. *Intense training: the key to optimal performance before and during the taper*. Scand J Med Sci Sports (2010)

### KB-006 — Nutrición

- Thomas DT, Erdman KA, Burke LM. *Position of the Academy of Nutrition and Dietetics, Dietitians of Canada, and the ACSM: Nutrition and Athletic Performance*. Med Sci Sports Exerc (2016)
- Jeukendrup A. *A step towards personalized sports nutrition: carbohydrate intake during exercise*. Sports Med (2014)
- Mountjoy M et al. *IOC consensus statement on Relative Energy Deficiency in Sport (RED-S)*
- Burke LM et al. *Carbohydrates for training and competition*. J Sports Sci (2011)

### KB-007 — Recuperación y sueño

- *The Prevalence of Use of Various Post-Exercise Recovery Methods after Training among Elite Endurance Athletes* — PMC8583677
- *Monitoring Sleep and Nightly Recovery with Wrist-Worn Wearables: Links to Training Load and Performance Adaptations* — PMC11768492
- *Evidence That Sleep Is an Indicator of Overtraining during the Competition Phase of Adolescent Sprinters* — PMC8041504
- *The Sleep and Recovery Practices of Athletes*. Nutrients (2021)

---

## 4. Hallazgo de la curación: la regla del 10 %

El hallazgo más significativo del proceso de curación afecta directamente al sistema previo al sprint.

### Contexto

El agente desarrollado en la asignatura de Ingeniería del Software y Bases de Datos codificaba de forma rígida en `build_prompt()` la regla del 10 %: *no incrementar el volumen semanal más de un 10 % respecto a la semana anterior*. Era el único conocimiento de dominio embebido en el sistema.

### Lo que reveló la revisión de fuentes

| Hallazgo | Fuente |
|---|---|
| La regla no procede de un estudio fundacional; se popularizó en literatura de divulgación de los años 80 | Revisión histórica |
| En un estudio con **486 corredores novatos** no se hallaron diferencias en prevalencia de lesión (21 %) entre incremento graduado al 10 % y programa estándar | Nielsen et al. |
| No se halló diferencia significativa entre incrementos medios del 10 % y del 24 % | Análisis comparativos |
| El control de **picos de carga en sesión individual** predice lesión mejor que el volumen semanal agregado (seguimiento de ~5.200 corredores) | Literatura de carga |
| Corredores bien entrenados toleran incrementos del orden del **20–25 %** | Literatura de carga |

### Implicación para el sistema

La regla no es dañina, pero es **insuficiente y potencialmente excesivamente conservadora**. Un sistema que la aplique universalmente:

- sobre-restringe a corredores experimentados
- ofrece falsa seguridad a novatos, porque el volumen semanal no es el predictor más relevante
- ignora que 10 % más de rodaje suave no impone el mismo estrés que 10 % más de trabajo de calidad

Este hallazgo motivó la creación del nivel de evidencia `practica_consolidada` en la taxonomía, y constituye el caso de demostración empleado para contrastar el flujo *legacy* contra el flujo *RAG* (ver `docs/evaluation/response-quality.md`).

---

## 5. Limitaciones del corpus

Se documentan por transparencia metodológica:

**Cobertura acotada.** Siete documentos cubren las dimensiones principales del dominio pero no lo agotan. Quedan fuera: entrenamiento de fuerza complementario, factores psicológicos de adherencia, entrenamiento en condiciones ambientales adversas y especificidades de poblaciones (edad avanzada, embarazo, patologías).

**Idioma del corpus frente a idioma de las fuentes.** Los documentos están redactados en español mientras la bibliografía es predominantemente anglófona. La síntesis introduce una capa de interpretación del equipo curador que, aunque documentada, no es trazable línea por línea a la fuente original.

**Registro técnico.** Los documentos emplean terminología especializada —*disponibilidad energética*, *ACWR*, *LT1/LT2*— que no coincide con el registro coloquial del usuario final. Esta brecha produjo la única falla de recuperación del conjunto de evaluación (caso EV-16), analizada en `docs/evaluation/retrieval-metrics.md`.

**Ausencia de versionado de fuentes.** El corpus refleja el estado de la evidencia en agosto de 2026. No existe mecanismo automatizado de detección de literatura posterior. La actualización es manual.

---

## 6. Evolución prevista

El pipeline de ingesta se diseñó **idempotente y dirigido por metadata**, sin rutas ni identificadores fijos. Cada documento se identifica por `doc_id` y se reemplaza limpiamente al reindexar.

Esta decisión habilita un módulo administrativo de gestión documental en sprints posteriores: carga de documentos por interfaz, reindexación automática y versionado del corpus. La única pieza faltante sería la capa de API y UI sobre el pipeline existente.

Precisión terminológica pertinente: ese módulo **no realiza autoentrenamiento**. El modelo de lenguaje no se modifica. Lo que cambia es el corpus recuperable, mediante re-indexación. La distinción es relevante para la caracterización correcta del sistema.
