# Capítulo 01 — Gestión del Alcance

> PMBOK: Scope Management | Estado: Borrador

## Módulos en alcance (MVP)

### L1 — Base Odoo
- `base`, `mail`, `account`, `hr`, `web`, `portal`
- `l10n_pe` (localización Peru)
- `l10n_pe_edi` o equivalente OCA (SUNAT UBL 2.1)

### L2 — OCA + OpenEduCat
- `openeducat_core`, `openeducat_admission`, `openeducat_attendance`
- `openeducat_exam`, `openeducat_fees`, `openeducat_timetable`
- `queue_job` (OCA — procesamiento async)

### L3 — Módulos SciBack (desarrollo propio)
- `sciback_siagie_connector` — generación de archivos Excel MINEDU
- `sciback_sunat_nubefact` — emisión de boletas/facturas via NubeFact
- `sciback_payment_culqi` — cobro con tarjeta
- `sciback_payment_yape` — cobro QR Yape
- `sciback_payment_pagoefectivo` — código CIP para pago en agentes
- `sciback_cneb_evaluation` — escala AD/A/B/C, competencias CNEB
- `sciback_ley29733_compliance` — consentimiento y ARCO de menores
- `sciback_school_finance` — pensiones, mora, estado de cuenta por familia
- `sciback_school_portal` — portal para padres de familia

## Fuera de alcance (MVP)

- Módulo de biblioteca
- App móvil nativa (solo portal web responsive)
- Integración directa con SIAGIE (no existe API pública)
- Biometría / control de acceso físico
- EBA / EBE (Educación Básica Alternativa / Especial)
- Pasarelas Niubiz y Mercado Pago (fase 2)
