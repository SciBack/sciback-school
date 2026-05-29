# 12. Hallazgos del Lab

## Hallazgos Fase 0 — Setup OrbStack (2026-05-28)

### Entorno

- **Máquina:** MacBook M1 ARM64
- **Runtime:** OrbStack (Docker 29.4.0)
- **Lab local:** `~/proyectos/labs/sciback-odoo/`

### Stack verificado

**Compatibilidad ARM64 — SIN emulación QEMU:**

| Servicio | Imagen | Arquitectura | Estado |
|----------|--------|--------------|--------|
| Odoo 17.0 | `odoo:17.0` (oficial) | ARM64 nativo | ✅ |
| PostgreSQL 16 | `postgres:16-alpine` | ARM64 nativo | ✅ |
| Redis 7 | `redis:7-alpine` | ARM64 nativo | ✅ |

Todos los contenedores con `healthcheck` OK. Pull e inicio sin errores de arquitectura.

### OpenEduCat 17.0 — Verificación

**Repo correcto identificado:**
```
github.com/openeducat/openeducat_erp
Branch: 17.0
```

**Nota crítica:** No usar `openeducat_core` (repositorio separado, deprecated para instalación vía Odoo). La rama `17.0` de `openeducat_erp` es la fuente oficial con 14 módulos integrados.

**Rama activa:** commits de mayo 2026 — proyecto en desarrollo continuo.

**Licencia:** LGPL-3 ✅

### Módulos OpenEduCat instalados

| Módulo | Tiempo | Estado | Notas |
|--------|--------|--------|-------|
| `openeducat_core` | ~14s | ✅ | Base del ecosistema |
| `openeducat_admission` | ~9.8s | ✅ | Arrastra deps: account, payment, product, uom |
| `openeducat_fees` | ~auto | ✅ | Instalación por dependencia |
| `openeducat_attendance` | ~0.4s | ✅ | Rápido, sin deps ocultas |
| `openeducat_exam` | ~0.7s | ✅ | Rápido |
| `openeducat_timetable` | ~0.5s | ⚠️ | Funcional; warning cosmético (ver abajo) |

**Tiempos en Odoo 17 con Python 3.11 en M1.**

### Correcciones necesarias para deploy canónico

#### 1. `addons_path` incorrecto en config

**Problema:**
```
# ❌ INCORRECTO
addons_path=/extra-addons
```

Odoo no encuentra los módulos de OpenEduCat porque están en un subdirectorio específico dentro de `extra-addons`.

**Fix:**
```
# ✅ CORRECTO
addons_path=/extra-addons/openeducat_erp/addons
```

O si hay múltiples fuentes de addons:
```
addons_path=/extra-addons/openeducat_erp/addons,/extra-addons/oca-modules
```

**Dónde cambiar:** `config/odoo.conf` (archivo base del Dockerfile o volumen montado).

**Impacto:** Sin esto, los módulos de OpenEduCat no se cargan en el catálogo; intentos de instalación desde la UI fallan silenciosamente.

---

#### 2. `website` es dependencia oculta de Odoo 17

**Problema:**
```
GET /web/login → HTTP 500
ERROR: module 'website' not found
```

OpenEduCat (como la mayoría de módulos Odoo 17) asume que el módulo `website` está instalado. Sin él, la UI web se rompe.

**Fix:**

Agregar `website` a la lista de módulos base a instalar en la Fase 1. En el script de instalación (p.ej., `entrypoint.sh` o el `--init` del CLI):

```bash
# Fase 1: Base + website
odoo-bin -i web,website,base,account -d <db> --stop-after-init
```

O en `config/odoo.conf`:
```
auto_install = web,website
```

**Dónde cambiar:** Script de inicialización (`entrypoint.sh`) o configuración de base de datos.

**Impacto:** Crítico — sin `website` instalado, la UI web no responde.

---

#### 3. Warning cosmético en `openeducat_timetable`

**Tipo:** Cosmético — no bloquea funcionalidad.

**Mensaje:**
```
UserWarning: Two fields (timing, timing_id) have the same label: Timing.
```

**Causa:** Bug upstream de OpenEduCat — código duplicado en la definición de campos del modelo.

**Solución propuesta:** Registrar issue en `github.com/openeducat/openeducat_erp` solicitando consolidación de campos. De momento, es inofensivo en desarrollo.

**Impacto:** Ninguno — la funcionalidad de horarios funciona normalmente.

---

### Pendiente Fase 0 (en progreso)

- [ ] Instalar `l10n_pe` — localización peruana (formatos de fecha, moneda S/., normas peruanas)
- [ ] Instalar `queue_job` (OCA) — procesamiento async para reportes y cálculos pesados

Ambos se incluirán en la Fase 1 del deploy canónico.

---

### Recomendaciones para deploy canónico

1. **Incorporar correcciones 1 y 2** al Dockerfile / config base antes de release.
2. **Documentar addons_path** en README de setup con ejemplos para múltiples fuentes.
3. **Crear checklist de deps ocultas** — `website`, `account`, `sale`, etc. — para evitar sorpresas en otros clientes.
4. **Registrar issue upstream** de OpenEduCat para el warning de `openeducat_timetable`.
5. **Plan Fase 1:** módulos base + OpenEduCat core + `l10n_pe` + `queue_job`.

---

---

## Hallazgos Fase 1 — Estructura académica EBR (2026-05-28)

### Módulo `sciback_school_base` creado en:
`~/proyectos/sciback/sciback-odoo/src/modules/sciback_school_base/`

### Decisiones de diseño notables

- **`noupdate="1"` en datos EBR** — preserva customizaciones del cliente en actualizaciones
- **Tab "Integraciones" con `groups="base.group_system"`** — tokens ocultos para no-admins
- **Método helper `get_config()` en el singleton** — todos los módulos L3 lo usan para obtener tokens
- **Batch codes con prefijo de nivel** (`PRI-1`, `SEC-1`) — facilita filtrado en SIAGIE y CNEB

### Correcciones críticas — campos reales de OpenEduCat 17.0

**IMPORTANTE:** Los campos reales difieren de la documentación. Usar SIEMPRE estos valores verificados en lab:

| Modelo | Campo INCORRECTO | Campo CORRECTO |
|--------|-----------------|----------------|
| `op.academic.year` | `date_start` | `start_date` |
| `op.academic.year` | `date_stop` | `end_date` |
| `op.academic.year` | `code` | ❌ No existe |
| `op.academic.year` | — | `term_structure` (obligatorio — usar `'four_Quarter'` para EBR bimestral) |
| `op.academic.term` | `date_start` | `term_start_date` |
| `op.academic.term` | `date_stop` | `term_end_date` |
| `op.academic.term` | `code` | ❌ No existe |

### Estructura EBR configurada en lab (`sciback_school_dev`)

- **3 niveles:** Educación Inicial, Primaria, Secundaria (`op.course`)
- **Año académico 2026** con `term_structure = 'four_Quarter'`
- **4 términos:** BIM1-BIM4 con fechas reales del calendario escolar peruano 2026

---

---

## Hallazgos Fase 2 — SUNAT / NubeFact (2026-05-28)

### Módulo `sciback_sunat_nubefact` — test end-to-end completado

**Boleta enviada y aceptada:** BBB1-2 → NubeFact sandbox → HTTP 200 ✅

**Resultado de la consulta:**
```json
{
  "serie": "BBB1",
  "numero": 2,
  "aceptada_por_sunat": false,
  "sunat_soap_error": "",
  "enlace_del_pdf": "https://www.nubefact.com/cpe/34a28cd3-ee40-4573-9fd8-e22b4d440d68.pdf",
  "enlace_del_xml": "https://www.nubefact.com/cpe/34a28cd3-ee40-4573-9fd8-e22b4d440d68.xml",
  "codigo_hash": "I3lBtF70Qy8HuQz3ppUiTsuXWy0FsY+hqFR5q/YgJ9Q=",
  "cadena_para_codigo_qr": "10108673261 | 03 | BBB1 | 000002 | 0.00 | 300.00 | ..."
}
```

`aceptada_por_sunat: false` es **esperado** en la cuenta demo — el RUC `10108673261` no tiene habilitación SUNAT real. `sunat_soap_error: ""` confirma que el XML está bien formado y NubeFact lo procesó correctamente. PDF, XML, QR y hash se generan igual.

---

### Bugs críticos corregidos en `account_move.py`

#### 1. URL de demo inexistente

`demo.nubefact.com` es NXDOMAIN — **no existe**. Ambos modos usan `api.nubefact.com`:

```python
# ❌ INCORRECTO (causa ConnectionError)
'demo': 'https://demo.nubefact.com/api/v1/{url_token}'

# ✅ CORRECTO — mismo host, la diferencia es la cuenta NubeFact
'demo': 'https://api.nubefact.com/api/v1/{url_token}'
'produccion': 'https://api.nubefact.com/api/v1/{url_token}'
```

#### 2. Constantes de tipo de comprobante incorrectas

```python
# ❌ INCORRECTO
TIPO_NC = 7
TIPO_ND = 8

# ✅ CORRECTO (confirmado en ejemplos oficiales NubeFact)
TIPO_NC = 3   # Nota de Crédito
TIPO_ND = 4   # Nota de Débito
```

#### 3. Constante IGV_INAFECTO incorrecta

```python
# ❌ INCORRECTO
IGV_INAFECTO = 8  # 8 es EXONERADO, no inafecto

# ✅ CORRECTO (Catálogo 07 SUNAT)
IGV_EXONERADO = 8
IGV_INAFECTO  = 9  # EBR — servicios educativos son inafectos (Art. 2 TUO IGV)
```

#### 4. Filtro de líneas — `display_type` en Odoo 17

En Odoo 17, las líneas de producto tienen `display_type == 'product'` (string truthy), **NO** `display_type == False` como en versiones anteriores:

```python
# ❌ INCORRECTO — excluye TODAS las líneas en Odoo 17
product_lines = self.invoice_line_ids.filtered(lambda l: not l.display_type)

# ✅ CORRECTO
product_lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
```

**Causa del error:** mensaje "Faltan items o lineas al documento" de NubeFact.

#### 5. `total_igv` — no usar `self.amount_tax`

`self.amount_tax` refleja los impuestos configurados en Odoo, no la afectación SUNAT real. Para líneas inafectas el IGV debe ser 0 aunque el producto tenga impuesto configurado:

```python
# ❌ INCORRECTO — puede incluir IGV de líneas inafectas
total_igv = self.amount_tax

# ✅ CORRECTO — calcular desde tipo_de_igv
total_igv = round(
    sum(l.price_subtotal for l in product_lines
        if self._get_tipo_igv_linea(l) == IGV_GRAVADO) * 0.18, 2
)
```

#### 6. Campo `codigo_hash` en respuesta NubeFact

NubeFact retorna `codigo_hash`, **no** `hash`:

```python
# ❌ INCORRECTO
'sunat_hash': response.get('hash', '')

# ✅ CORRECTO
'sunat_hash': response.get('codigo_hash', '') or response.get('hash', '')
```

#### 7. DNS del contenedor Docker

El contenedor Odoo no resuelve `api.nubefact.com` por defecto. Fix en `docker-compose.yml`:

```yaml
services:
  odoo:
    dns:
      - 8.8.8.8
      - 1.1.1.1
```

#### 8. Moneda — siempre PEN para servicios educativos

Si la empresa tiene USD como moneda por defecto, el payload incluye `"moneda": 2` y NubeFact exige `tipo_de_cambio`. Solución: asegurarse de que las facturas escolares se emiten en PEN.

---

### Serie configurada en NubeFact demo

| Serie | Tipo | Estado en demo |
|-------|------|----------------|
| `BBB1` | Boleta (03) | ✅ Habilitada en cuenta demo |
| `B001` | Boleta (03) | ❌ Rechaza: "No puedes emitir con esta serie" |
| `FFF1` | Factura (01) | Según ejemplos oficiales, habilitada |

**Importante:** las series disponibles en demo son las que están en los ejemplos JSON oficiales de NubeFact (carpeta `docs/nubefact-ejemplos/`). Usar exactamente esas series en los tests.

---

### Configuración NubeFact en Odoo

Los tokens no viven en `~/.secrets/sunat.env` — viven en el modelo `sciback.school.config` (Odoo DB):

```python
config = env['sciback.school.config'].search([], limit=1)
url_token = config.nubefact_url_token   # UUID de la cuenta
api_token  = config.nubefact_api_token  # Secreto — nunca loguear
```

---

### Payload de boleta inafecta — estructura correcta

```json
{
  "tipo_de_comprobante": 2,
  "serie": "BBB1",
  "moneda": 1,
  "tipo_de_cambio": "",
  "total_gravada": "",
  "total_inafecta": 300.0,
  "total_igv": "",
  "total": 300.0,
  "items": [{
    "tipo_de_igv": 9,
    "igv": 0,
    "subtotal": 300.0,
    "total": 300.0
  }]
}
```

---

## Siguiente paso: Fase 1 — datos de prueba Agua Viva

Cargar estructura académica EBR completa de Agua Viva con datos realistas de prueba:
estudiantes, docentes, grados, secciones y plan de estudios 2026.
