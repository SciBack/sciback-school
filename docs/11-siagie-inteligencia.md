# Capítulo 11 — Inteligencia Técnica SIAGIE

> Estado: Investigación | Última revisión: 2026-05-27

## Hallazgo clave

SIAGIE v5 (`siagie-app-ha.minedu.gob.pe/main`) es una **SPA (Single Page Application)**. El HTML que devuelve es un shell vacío — toda la lógica corre en JavaScript. Esto implica que existe un **backend REST real**, y toda comunicación frontend↔backend son llamadas HTTP interceptables con F12 (Network tab) o un proxy como Charles / mitmproxy.

Esto abre una vía de integración directa que el spec original no contemplaba.

---

## Las tres vías de integración, en orden de viabilidad

### Vía 1 — Interceptar endpoints internos (factible hoy)

Con credenciales válidas de una IE:

1. Abrir SIAGIE v5 en Chrome, F12 → Network → filtrar XHR/Fetch
2. Ejecutar las acciones a automatizar: login, matrícula, registro de notas, asistencia
3. Capturar: URLs, métodos HTTP, headers, payloads JSON, tokens de sesión
4. Replicar los requests desde el backend Odoo

El token de sesión probablemente es JWT — MINEDU usa sistema **PASSPORT** para SSO.

**Riesgo:** no es una API pública con SLA. MINEDU puede cambiar endpoints, agregar CSRF tokens, implementar bot detection o invalidar sesiones automatizadas sin previo aviso. Para 1 colegio piloto: tolerable. Para 50 colegios en producción: bomba de tiempo.

---

### Vía 2 — Solicitud formal a MINEDU bajo Ley 27806 (correcta pero lenta)

Solicitar: *"documentación técnica de los endpoints REST que consume SIAGIE v5, métodos, parámetros de entrada/salida y esquema de autenticación"*.

- MINEDU tiene **7 días hábiles** para responder
- Si la API-NEXUS tiene documentación formal, están obligados a entregarla
- Si niegan: argumentar que SIAGIE es de uso **obligatorio** para IEs privadas por ley — la negativa de documentación impide cumplimiento normativo

Ejecutar cuando tengamos 3–5 clientes activos (masa crítica mínima).

---

### Vía 3 — Convenio con MINEDU vía PIDE (largo plazo, sostenible)

Con 10+ colegios clientes: ir al MINEDU con propuesta formal de acceso autorizado a la API en nombre de las IEs representadas.

- Plazo: 6–18 meses
- Requiere relaciones institucionales
- Es la vía limpia y sostenible a largo plazo

---

## Estrategia por fase

| Fase | Clientes | Estrategia SIAGIE |
|------|----------|-------------------|
| Piloto | 1 (Agua Viva) | **Excel-first** — generación de .xls manual |
| Expansión temprana | 2–5 | Mapear endpoints con F12 + credenciales IE + construir conector REST; mantener Excel como fallback |
| Crecimiento | 5–10 | Iniciar Vía 2 (Ley 27806) para documentación oficial |
| Escala | 10+ | Vía 3 — convenio MINEDU/PIDE |

---

## Pendiente antes de construir conector REST

Antes de escribir una línea de código del conector REST, dedicar medio día a:

1. Entrar a SIAGIE v5 con credenciales de una IE real
2. F12 → Network → XHR/Fetch
3. Ejecutar: login, registro de nota, registro de asistencia, carga de matrícula
4. Documentar: endpoint, método HTTP, headers, payload request y response

**Estado:** pendiente — sin acceso a credenciales de IE real actualmente.

Eso vale más que cualquier suposición. Con los endpoints reales, la integración es días de trabajo, no semanas.

---

## Implicancia para el módulo `sciback_siagie_connector`

- **MVP (piloto Agua Viva):** Excel-first como está en el spec. Estados: `draft → generated → uploaded → confirmed`.
- **v2 (cuando haya credenciales):** agregar modo REST con fallback a Excel. El módulo ya tiene la arquitectura para soportarlo — solo cambiar la capa de transporte.
- **NUNCA** documentar en UI, marketing o contrato que existe "integración directa con SIAGIE" hasta tener Vía 2 o Vía 3 aprobada.

---

## Investigación oficial verificada (2026-05-28)

Fuentes oficiales MINEDU (siagie.minedu.gob.pe, repositorio.minedu.gob.pe, gob.pe).

### 🔑 HALLAZGO QUE CAMBIA EL DISEÑO — el conector RELLENA, no GENERA

La plantilla Excel de SIAGIE **NO es un formato fijo recreable desde cero.** Es un archivo `.xls` (Excel 97-2003, **no** xlsx) **generado dinámicamente por SIAGIE** que contiene:
- Un **identificador interno de sección/periodo en el nombre del archivo** — que NO se debe modificar (SIAGIE lo usa para saber a qué grado/sección/periodo pertenece). Ej: `Mats_XXXXXXXX_..._....xls`.
- Los **estudiantes pre-cargados** (no se ingresan; ya vienen en la plantilla).
- Las **columnas de competencias** según el currículo configurado para esa sección.

**Flujo real del conector (no es "generar .xls", es "rellenar .xls"):**
1. El usuario **descarga** la plantilla desde SIAGIE (paso manual, requiere login IE).
2. Odoo/`sciback_siagie_connector` **rellena** los calificativos/datos en esa plantilla, casando por código de estudiante. (automatizable)
3. El usuario **sube** la plantilla rellena a SIAGIE. (paso manual)

⇒ El módulo debe diseñarse como **"fill template"**: recibe el .xls descargado, lo parsea, mapea estudiantes Odoo↔SIAGIE por código, escribe calificativos, devuelve el .xls listo para subir.

### Carga masiva por Excel — CONFIRMADO disponible en:
| Módulo | Carga Excel | Notas |
|--------|:---:|---|
| Ratificación de matrícula | ✅ | Solo alumnos del año anterior; nuevos = manual con DNI/RENIEC |
| Asistencia mensual | ✅ | Estado por día del mes por sección |
| Notas finales por sección | ✅ | Hoja "NF"; columnas = competencias por área; incluye leyenda AD/A/B/C |
| Notas por periodo | ✅ | Mismo mecanismo (RVM 048-2024) |
| Notas de recuperación | ✅ | Módulo de cierre de año |

NO importable (digitación manual web): matrícula de estudiantes nuevos, config de año/grados/secciones, registro de docentes, aprobación de nóminas, actas, certificados.

### Códigos oficiales
- **Código modular IE**: 7 dígitos (consultable en ESCALE, sin login).
- **Código de estudiante**: 14 dígitos. Con DNI = `000000` + DNI(8) → ej. DNI `74523188` → `00000074523188`. Sin DNI: autogenerado por el director.
- **DNI** validado contra RENIEC en tiempo real al matricular.

### Escala CNEB (RVM 094-2020, mod. RVM 048-2024)
- **AD** Logro destacado · **A** Logro esperado · **B** En proceso · **C** En inicio.
- Inicial Ciclo I/II: solo **conclusiones descriptivas** (sin literal).
- Conclusión descriptiva **obligatoria** para calificativo **C** y **AD** (RVM 048-2024); opcional para A y B.

### Áreas curriculares (catálogo SIAGIE — IDs internos solo visibles en plantilla real)
- **Inicial:** Comunicación, Matemática, Personal Social, Ciencia y Tecnología, Psicomotriz, Tutoría.
- **Primaria:** + Arte y Cultura, Ed. Física, Inglés, Ed. Religiosa, TOE, (EPT).
- **Secundaria:** Comunicación, Matemática, C. Sociales, DPCC, CyT, Arte y Cultura, Ed. Física, Inglés, Ed. Religiosa, EPT, Tutoría.

### Normativa clave
- **RVM 094-2020-MINEDU** — evaluación de competencias (escala AD/A/B/C).
- **RVM 048-2024-MINEDU** — conclusiones descriptivas obligatorias para C y AD.
- **RM 432-2020 / RM 452-2025-MINEDU** — registro de trayectoria educativa en SIAGIE (revisar la de 2025, la más reciente).

### ⚠️ Insumo que FALTA para construir (pendiente del usuario)
Descargar desde SIAGIE de Agua Viva (credenciales de director) **una plantilla real**:
1. Plantilla de **notas finales/por periodo** de una sección (hoja "NF": nombres/orden exactos de columnas, IDs de área/competencia).
2. Plantilla de **asistencia mensual**.
3. (Opcional) Plantilla de **ratificación de matrícula**.

Con esos archivos reales se confirma el formato exacto y el conector se construye en días. Sin ellos, cualquier columna es suposición.

### Manuales oficiales (PDF)
- Guía rápida v3.3.0: `siagie.minedu.gob.pe/archivos/guias_actualizacion_s330_soa.pdf`
- Instructivo 3.9.0: `siagie.minedu.gob.pe/archivos/guias_instructivo_3.9.0.pdf`
- Validación de procesamiento de calificaciones: `siagie.minedu.gob.pe/archivos/7_validacion_procesamiento_calificaciones.pdf`
- RVM 048-2024: `cdn.www.gob.pe/uploads/document/file/6275055/5518274-resolucion_vice_ministerial-00048-2024-m.pdf`

---

## ¿Existe API pública de SIAGIE? — Investigación (2026-05-28)

Pregunta: ¿se puede integrar Odoo↔SIAGIE por API en vez de Excel?

| Vía | Estado (verificado con fuentes oficiales) |
|---|---|
| Portal de desarrolladores MINEDU | ❌ No existe (no hay developer/api.minedu.gob.pe) |
| SIAGIE publicado en PIDE | ❌ En PIDE solo está "Grados y Títulos por DNI", no la data operativa de SIAGIE |
| RM/RVM que ordene abrir APIs SIAGIE | ❌ Base legal vigente (RM 609/665/712-2018, RVM 025-2019, RM 432-2020) no la mandata |
| OAuth/SSO MINEDU para terceros | ❌ PASSPORT es login interno, no IdP para apps externas |
| Datos abiertos individuales | ❌ Solo agregados (ESCALE/datos abiertos); data de menores no se publica |
| Convenio privado vía PIDE (DS 029-2021-PCM) | 🟡 Legal pero MINEDU debe publicar primero el servicio (no lo ha hecho); proceso de meses/años + Ley 29733 |

**Competencia (qué hacen los ERP escolares peruanos hoy):** ninguno tiene API con SIAGIE.
- SieWeb (líder): sin integración API documentada.
- Smiledu: lo llama "Formatos masivos de descarga a SIAGIE" → es Excel.
- SIGEDU: integra Google/Zoom/SUNAT, NO SIAGIE.
- El propio MINEDU documenta el flujo como "Uso Básico": descargar plantilla → llenar → subir.

**Conclusión:** a 2026 NO hay vía API formal. El estándar de facto del mercado es Excel bidireccional. El convenio PIDE es el único camino API formal y depende de que MINEDU publique el servicio (vigilar el catálogo PIDE).

**Estado de decisión:** el usuario NO está convencido del enfoque Excel (2026-05-28) y va a investigar por su cuenta vías alternativas antes de construir. Conector EN PAUSA hasta nueva información.

Fuentes: gob.pe/741-plataforma-de-interoperabilidad-del-estado · busquedas.elperuano.pe (DS 029-2021-PCM) · siagie.minedu.gob.pe/baselegal · passport.minedu.gob.pe · sieweb.com.pe · smiledu.com · sigedu.pe
