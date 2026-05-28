# Capítulo 07 — Gestión de Riesgos

> PMBOK: Risk Management | Estado: Borrador

## Registro de riesgos

| ID | Riesgo | Prob | Impacto | Severidad | Mitigación |
|----|--------|------|---------|-----------|------------|
| R01 | NubeFact cambia su API sin aviso | Media | Alto | Alta | Versionar contrato API, tests de integración automatizados |
| R02 | MINEDU cambia formato .xls SIAGIE | Alta | Alto | Crítica | Diseño modular; actualización como mantenimiento estándar |
| R03 | Cliente alfa abandona el piloto | Baja | Alto | Media | Contrato de compromiso mínimo 6 meses |
| R04 | Costo AWS supera proyección por crecimiento inesperado | Baja | Medio | Baja | Budget alerts + rightsizing trimestral |
| R05 | Fuga de datos de menores (Ley 29733) | Baja | Crítico | Alta | Módulo compliance, auditoría de accesos, cifrado en tránsito y reposo |
| R06 | OpenEduCat 18 incompatible con módulos L3 | Media | Alto | Alta | Fijar Odoo 17 LTS; no migrar hasta OpenEduCat 18 estable |
| R07 | Rechazo SUNAT por error en UBL 2.1 | Media | Alto | Alta | Tests exhaustivos en sandbox, CDR almacenado |
| R08 | Competidor replica producto antes de escalar | Media | Medio | Media | Velocidad de ejecución + relación con cliente |

## Plan de respuesta prioritario

**R02 (SIAGIE formato):** monitorear circulares MINEDU/UGEL trimestralmente. El módulo SIAGIE tiene la lógica de generación de columnas parametrizada en `ir.config_parameter`.

**R05 (Ley 29733):** módulo `sciback_ley29733_compliance` implementa consentimiento explícito, registro de accesos y endpoint ARCO. Auditoría anual recomendada.
