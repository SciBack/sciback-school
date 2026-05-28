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
