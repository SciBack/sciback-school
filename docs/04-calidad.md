# Capítulo 04 — Gestión de la Calidad

> PMBOK: Quality Management | Estado: Borrador

## Estándares de código

- Python: `ruff` + `black` + `pylint-odoo`
- Versionado de módulos OCA: `17.0.X.Y.Z`
- Licencia: LGPLv3 para módulos `sciback_*`
- Tests: pytest-odoo, cobertura mínima 60% en módulos críticos (SUNAT, pagos)

## Criterios de aceptación por módulo

| Módulo | Criterio mínimo |
|--------|----------------|
| `sciback_sunat_nubefact` | Boleta aceptada por SUNAT en sandbox |
| `sciback_siagie_connector` | Archivo .xls importado en SIAGIE demo sin errores |
| `sciback_payment_culqi` | Transacción exitosa y webhook verificado con HMAC |
| `sciback_cneb_evaluation` | Libreta exportable a PDF con escala AD/A/B/C |
| `sciback_school_portal` | WCAG 2.1 AA básico, responsive mobile |

## Revisiones

- Code review obligatorio antes de merge a `main`
- Deploy a staging antes de producción
- Revisión de `terraform plan` con segundo par de ojos antes de `apply` destructivo
