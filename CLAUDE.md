# SciBack Odoo — Plataforma educativa canónica

> Producto canónico de SciBack para gestión integral de instituciones educativas
> peruanas, construido sobre **Odoo 17 CE + OpenEduCat**. Repo: `github.com/SciBack/sciback-odoo`.

## Qué es y por qué este nombre

Plataforma de gestión académica multinivel: **colegios (EBR), institutos (IEST) y universidades**.
El repo se nombra por la **plataforma base (Odoo)**, igual que los demás repos SciBack se
nombran por su plataforma (`sciback-dspace-alicia`, `sciback-theme-ojs`, `connector-koha`).
NO se usa "edu" porque todos los productos SciBack son educativos — no distingue.

> Renombrado desde `sciback-school` el 2026-05-29 (GitHub redirige el nombre viejo).

## Arquitectura: 1 repo, core compartido + módulos por vertical

Los 3 niveles comparten ~65% (personas, matrícula, pensiones, SUNAT, pagos, portal).
Por eso **un solo repo**, no tres — un fix beneficia a los tres. El nivel se distingue por módulo:

```
src/modules/
├── sciback_school_base/      core común  (renombrar a sciback_*_base en fase posterior)
├── sciback_school_finance/   transversal
├── sciback_school_portal/    transversal
├── sciback_sunat_nubefact/   transversal — facturación SUNAT
├── sciback_payment_{culqi,yape,pagoefectivo}/  transversal — pagos online
│
├── COLEGIOS (EBR):  sciback_cneb_evaluation · sciback_siagie_connector · sciback_ley29733_compliance
├── INSTITUTOS (futuro):    sciback_iest_*
└── UNIVERSIDADES (futuro): sciback_uni_*  (SUNEDU, RENATI, créditos)
```

Cada despliegue instala SOLO los módulos de su nivel.

> ⚠️ Los módulos técnicos `sciback_school_*` (base/finance/portal) aún NO se renombraron
> para no romper la DB del lab. Es fase posterior.

## Modelo de negocio: SaaS multi-tenant

- Varios colegios pequeños en **una sola instancia Odoo** (múltiples DBs, una por colegio).
- Marca pública de la línea colegios = **"SciBack Edu"** (en sciback.com/colegios).
- Planes: Esencial (S/199, ≤300 alumnos) · Profesional (S/599, 300-800) · Enterprise (S/1899, 800+).
- Detalle en memoria `sciback-school-pricing.md` y `sciback-school-features.md`.

## Stack

- Odoo 17 Community + OpenEduCat 17 (repo `openeducat/openeducat_erp` rama 17.0)
- `l10n_pe` (localización SUNAT) + `queue_job` (OCA, async)
- Facturación: **NubeFact** (OSE) — ver `sciback_sunat_nubefact`
- Pagos: Culqi / Yape / PagoEfectivo
- Despliegue: Docker Compose + EC2 Ubuntu 22.04 + Nginx + Let's Encrypt
- **Producción: AWS us-east-2 (Ohio)** · Labs/infra interna: us-east-1 (Virginia)

## Lab local (desarrollo)

`~/proyectos/labs/sciback-odoo/` — OrbStack (Docker) en MacBook M1. Odoo en `localhost:8069`
(admin/admin). DB `sciback_school`. Regenerable desde su README. Producción nunca corre en Mac.

## Estado del roadmap (ver docs/02-cronograma.md)

- ✅ Fase 0 — Entorno, estructura EBR, datos de prueba
- ✅ Fase 2 — Facturación SUNAT vía NubeFact (boletas BBB1 emitidas en sandbox; PDF/XML/QR OK)
- 🔄 Fase 1 — Datos reales Agua Viva (cliente alfa)
- ⏳ Fase 3 SIAGIE · Fase 4 CNEB · Fase 5 Pagos · Fase 6 Portal padres · Fase 7 QA · Fase 8 Go-live

## Hallazgos críticos (ya resueltos — ver docs/12-lab-hallazgos.md)

- **NubeFact:** `demo.nubefact.com` NO existe → usar `api.nubefact.com` en ambos modos.
  tipo_comprobante: 1=Factura 2=Boleta 3=NC 4=ND. IGV inafecto=9 (educación EBR). Campo `codigo_hash`.
- **Odoo 17:** líneas de factura tienen `display_type=='product'` (no `False`).
- **SIAGIE:** NO hay API pública/formal a 2026 (ver docs/11). El estándar de facto es Excel
  bidireccional. Conector EN PAUSA — el usuario no está convencido del enfoque Excel.

## Cliente alfa

Escuela/Comunidad Cristiana **Agua Viva**. Overlay del cliente (config/.env/branding) va
APARTE del canónico. El cliente NUNCA es upstream. Bug fixes: primero aquí, luego `git pull` en EC2.

## Reglas de trabajo (de ~/.claude/CLAUDE.md y ~/proyectos/CLAUDE.md)

- Español siempre. Comandos ejecutables con verificación.
- Flujo deploy: local → commit → push → `git pull` en EC2 (nunca scp).
- Secretos en `~/.secrets/` (`source servicio.env`). NUNCA commitear secretos de cliente.
- Usar sub-agentes especializados (odoo-expert, etc.) y skill `emil-design-eng` para UI.
- NUNCA modificar OpenEduCat/OCA directamente — extender en módulo propio.

## Web del producto

`sciback.com/colegios` (landing "SciBack Edu") — repo SEPARADO `sciback-website` (Astro).
