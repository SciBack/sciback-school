# Capítulo 02 — Roadmap de Implementación

> Inicio: 2026-05-28  
> Go-live objetivo: octubre 2026 (antes del 4to bimestre)  
> Contexto: calendario escolar peruano termina en diciembre — go-live en octubre permite usar el sistema para notas del 4to bimestre y matrículas 2027

---

## Vista general

```
May 28        Jun 11        Jul 2         Jul 23        Aug 6
   │             │             │             │             │
   ├─ FASE 0 ───┤             │             │             │
   │  Setup      ├─ FASE 1 ───┤             │             │
   │  IaC/Docker │  Odoo base  ├─ FASE 2 ───┤             │
   │             │  OpenEduCat │  SUNAT      ├─ FASE 3 ───┤
   │             │             │  NubeFact   │  SIAGIE     │
                                                           │
Aug 6         Aug 20        Sep 10        Sep 24        Oct 8         Oct 15
   │             │             │             │             │             │
   ├─ FASE 3 ───┤             │             │             │             │
   │  SIAGIE     ├─ FASE 4 ───┤             │             │             │
   │             │  CNEB       ├─ FASE 5 ───┤             │             │
   │             │  Ley 29733  │  Pagos      ├─ FASE 6 ───┤             │
   │             │             │  Culqi/Yape │  Portal     ├─ FASE 7 ───┤
   │             │             │             │  padres     │  QA/Sec     │
                                                                         │
Oct 15        Oct 22        Nov 5
   │             │             │
   ├─ FASE 8 ───┤             │
   │  GO-LIVE   ├─ FASE 9 ───┤
   │  Agua Viva  │  Estabiliz  │→ Listo para 2do cliente
```

---

## Fases detalladas

### FASE 0 — Setup (2026-05-28 → 2026-06-11)

**Objetivo:** entorno de desarrollo funcionando, repos inicializados, IaC base.

| Tarea | Detalle |
|-------|---------|
| Crear repo `sciback-odoo` en GitHub | Público, LGPL |
| Crear repo `sciback-ops` en GitHub | Privado, inventario de clientes |
| Inicializar estructura de carpetas | `src/`, `deploy/`, `docs/` |
| `docker-compose.yml` dev funcional | Odoo 17 + PostgreSQL 16 + Redis + Nginx |
| Makefile con comandos base | `make dev`, `make stop`, `make logs` |
| Terraform base en `us-east-2` | VPC + EC2 + RDS + S3 + Secrets Manager |
| Ansible playbook provisioning | Deploy completo en < 2 horas |
| CI GitHub Actions | Lint (ruff + pylint-odoo) en cada PR |
| `CLAUDE.md` en repo | Spec completo como guía permanente |

**Hito:** `make dev` levanta Odoo 17 vacío en localhost.

---

### FASE 1 — Odoo base + OpenEduCat (2026-06-11 → 2026-07-02)

**Objetivo:** sistema académico básico funcionando con datos de Agua Viva.

| Tarea | Detalle |
|-------|---------|
| Instalar OpenEduCat Community 17.0 | `openeducat_core`, `openeducat_admission`, `openeducat_attendance`, `openeducat_exam`, `openeducat_fees`, `openeducat_timetable` |
| Instalar `l10n_pe` | Localización peruana base |
| Instalar `queue_job` (OCA) | Procesamiento async para SUNAT y SIAGIE |
| Configurar estructura académica Agua Viva | Niveles (inicial/primaria/secundaria), grados, secciones |
| Crear módulo `sciback_school_base` | Esqueleto L3, manifest, `__init__.py` |
| Migrar datos maestros | Docentes, estudiantes de prueba, cursos |
| Configurar plan de cuentas `l10n_pe` | COA peruano base |

**Hito:** matrícula de un estudiante de prueba completa en el sistema.

---

### FASE 2 — SUNAT / NubeFact (2026-07-02 → 2026-07-23)

**Objetivo:** emisión de boletas y facturas electrónicas aceptadas por SUNAT en sandbox.

| Tarea | Detalle |
|-------|---------|
| Crear módulo `sciback_sunat_nubefact` | Hereda `account.move` |
| Integrar API NubeFact (sandbox) | Autenticación por token, endpoint `/api/v1/invoice` |
| Flujo async con `queue_job` | Estados: `draft → sent → accepted/rejected/observed` |
| Almacenar CDR como attachment | XML de respuesta SUNAT |
| Boleta (tipo 03) | Para padres de familia personas naturales |
| Factura (tipo 01) | Para empresas que pagan pensiones |
| Nota de crédito (tipo 07) | Anulaciones y descuentos |
| Configurar serie y correlativo | Serie B001 boletas, F001 facturas |
| Gestionar certificado digital SUNAT | Coordinación con Agua Viva para obtenerlo |

**Hito:** boleta de pensión emitida y aceptada por SUNAT en sandbox.

---

### FASE 3 — SIAGIE Connector (2026-07-23 → 2026-08-06)

**Objetivo:** generación del archivo .xls para MINEDU/UGEL sin errores.

| Tarea | Detalle |
|-------|---------|
| Crear módulo `sciback_siagie_connector` | Excel-first (ver doc 11) |
| Mapear campos SIAGIE → campos Odoo | Código modular, DNI, notas por competencia |
| Generador .xls con `xlwt` o `openpyxl` | Formato exacto que acepta SIAGIE |
| Flujo humano-en-el-loop | Estados: `draft → generated → uploaded → confirmed` |
| UI para revisar antes de descargar | Vista tree con validaciones previas |
| Validaciones pre-export | DNI completo, notas en rango, campos obligatorios |
| Test con UGEL | Validar archivo con formato real antes de go-live |

**Hito:** archivo .xls generado importable en SIAGIE demo sin errores.

---

### FASE 4 — CNEB + Ley 29733 (2026-08-06 → 2026-08-20)

**Objetivo:** libreta de notas con escala CNEB y compliance de datos de menores.

| Tarea | Detalle |
|-------|---------|
| Crear módulo `sciback_cneb_evaluation` | Escala AD/A/B/C por competencia y área curricular |
| Libreta de notas exportable a PDF | Por bimestre, por estudiante |
| Configurar áreas curriculares CNEB | Comunicación, Matemática, C&T, PS, Arte, EF, ER, EPT |
| Crear módulo `sciback_ley29733_compliance` | Consentimiento explícito de padres |
| Registro de accesos a datos de menores | Log de quién consulta qué dato |
| Endpoint ARCO | Acceso, Rectificación, Cancelación, Oposición |
| Política de retención de datos | Configuración de tiempo de vida de datos |

**Hito:** libreta de notas del 3er bimestre exportable en PDF con escala AD/A/B/C.

---

### FASE 5 — Pasarelas de pago (2026-08-20 → 2026-09-10)

**Objetivo:** cobro de pensiones online funcional en sandbox.

| Tarea | Detalle |
|-------|---------|
| Crear módulo `sciback_payment_culqi` | Checkout V4, verificación HMAC webhook |
| Crear módulo `sciback_payment_yape` | QR dinámico via Culqi |
| Crear módulo `sciback_payment_pagoefectivo` | Código CIP via Culqi |
| Flujo de cobro de pensión | Selección mes → pago → boleta SUNAT automática |
| Conciliación bancaria | Diario por pasarela, cuenta puente "Por liquidar" |
| Estado de cuenta por familia | Pendientes, pagados, vencidos |
| Activar cuentas en producción | Registro en Culqi con datos de Agua Viva |

**Hito:** pago de pensión con tarjeta Culqi en sandbox → boleta SUNAT generada automáticamente.

---

### FASE 6 — Portal de padres (2026-09-10 → 2026-09-24)

**Objetivo:** padres pueden ver notas, asistencia, estado de cuenta y pagar en línea.

| Tarea | Detalle |
|-------|---------|
| Crear módulo `sciback_school_portal` | Hereda `portal.mixin` de Odoo |
| Login de padre/apoderado | Vinculado a `res.partner` del estudiante |
| Vista de notas por bimestre | Solo lectura, escala CNEB |
| Vista de asistencia | Faltas y tardanzas del mes |
| Estado de cuenta | Pensiones pendientes y pagadas |
| Botón "Pagar" | Integrado con Culqi/Yape/PagoEfectivo |
| Responsive mobile | Funcional en celular (80% del uso esperado) |
| Comunicados del colegio | Noticias y avisos del director |

**Hito:** padre de familia accede al portal, ve notas de su hijo y paga una pensión desde el celular.

---

### FASE 7 — QA y seguridad (2026-09-24 → 2026-10-08)

**Objetivo:** sistema listo para producción, sin vulnerabilidades críticas.

| Tarea | Detalle |
|-------|---------|
| Tests unitarios módulos críticos | SUNAT, pagos — cobertura mínima 60% |
| Penetration test básico | OWASP Top 10, rutas admin expuestas |
| Hardening Nginx | Headers de seguridad, rate limiting |
| Hardening Odoo | `list_db = False`, rutas DB bloqueadas |
| Backup y restore drill | Simular pérdida de datos, restaurar desde S3 |
| Load test | 50 usuarios concurrentes en portal |
| Revisión Ley 29733 | Auditoría de campos sensibles de menores |
| Documentación operativa | Manual del director, manual del secretario |

**Hito:** penetration test sin hallazgos críticos, backup restaurado exitosamente.

---

### FASE 8 — Go-live Agua Viva (2026-10-08 → 2026-10-15)

**Objetivo:** instancia de producción funcionando con datos reales.

| Tarea | Detalle |
|-------|---------|
| Provisionar EC2 producción | `make provision CLIENT=agua-viva TIER=pilot` |
| Configurar DNS | `erp.aguaviva.edu.pe` → IP EC2 |
| Certificado SSL | Let's Encrypt via certbot |
| Migrar datos reales | Estudiantes, docentes, plan de estudios 2026 |
| Activar NubeFact producción | Con certificado digital real de Agua Viva |
| Activar Culqi producción | Cuenta verificada de Agua Viva |
| Capacitación usuarios | Director, secretaria, docentes (1 día) |
| Go / No-go checklist | 20 puntos antes de abrir a padres |

**Hito: sistema en producción, primer boleta real emitida a SUNAT.**

---

### FASE 9 — Estabilización (2026-10-15 → 2026-11-05)

**Objetivo:** sistema estable, bugs resueltos, listo para replicar a segundo cliente.

| Tarea | Detalle |
|-------|---------|
| Soporte post-lanzamiento | Resolución de bugs en < 24h |
| Ajustes UX basados en uso real | Feedback de secretaria y docentes |
| Monitoreo CloudWatch | Alarmas activas, revisar métricas semana 1 |
| Documentar lecciones aprendidas | Para mejorar el proceso con el 2do cliente |
| Pulir IaC | Cualquier ajuste que requirió el deploy real |
| Preparar caso de éxito | Testimonio de Agua Viva para marketing |
| Prospección 2do cliente | Con el caso de éxito en mano |

**Hito: Agua Viva opera de forma autónoma, SciBack School listo para segundo cliente.**

---

## Resumen ejecutivo

| Fase | Período | Semanas | Hito |
|------|---------|---------|------|
| 0 — Setup | May 28 – Jun 11 | 2 | Odoo vacío en localhost |
| 1 — Odoo + OpenEduCat | Jun 11 – Jul 2 | 3 | Matrícula de prueba completa |
| 2 — SUNAT / NubeFact | Jul 2 – Jul 23 | 3 | Boleta aceptada en sandbox |
| 3 — SIAGIE | Jul 23 – Ago 6 | 2 | .xls importable en SIAGIE demo |
| 4 — CNEB + Ley 29733 | Ago 6 – Ago 20 | 2 | Libreta PDF con AD/A/B/C |
| 5 — Pagos | Ago 20 – Sep 10 | 3 | Pago → boleta SUNAT automática |
| 6 — Portal padres | Sep 10 – Sep 24 | 2 | Padre paga desde celular |
| 7 — QA / Seguridad | Sep 24 – Oct 8 | 2 | Pentest sin hallazgos críticos |
| 8 — Go-live | Oct 8 – Oct 15 | 1 | **Primera boleta real en SUNAT** |
| 9 — Estabilización | Oct 15 – Nov 5 | 3 | Listo para 2do cliente |
| **Total** | | **23 semanas** | |

---

## Dependencias críticas (gestionar desde ya)

| Dependencia | Responsable | Plazo máximo |
|-------------|-------------|-------------|
| Certificado digital SUNAT de Agua Viva | Agua Viva + SciBack | Antes de Fase 2 (Jul 2) |
| Cuenta Culqi verificada de Agua Viva | Agua Viva | Antes de Fase 5 (Ago 20) |
| Dominio institucional `aguaviva.edu.pe` | Agua Viva | Antes de Fase 8 (Oct 8) |
| Credenciales SIAGIE de Agua Viva (para validación) | Agua Viva | Antes de Fase 3 (Jul 23) |
| Datos maestros: nómina de estudiantes y docentes | Agua Viva | Antes de Fase 1 (Jun 11) |

---

## Calendario escolar referencia

| Período | Fechas | Relevancia |
|---------|--------|------------|
| 3er bimestre | Jul – Sep 2026 | Sistema debe estar listo para notas |
| 4to bimestre | Oct – Dic 2026 | **Go-live en producción** |
| Matrículas 2027 | Nov – Dic 2026 | Primera matrícula real en el sistema |
| Inicio año 2027 | Mar 2027 | Sistema operando a plena capacidad |
