# Capítulo 10 — Análisis Competitivo

> Estado: Activo | Última revisión: 2026-05-27  
> Fuente de precios Q10: q10.com/Peru/ETDH (verificado mayo 2026)

---

## Nota importante sobre el segmento de Q10 en Perú

Q10 en Perú **no atiende colegios EBR** (Educación Básica Regular — inicial, primaria, secundaria). Su oferta peruana está dirigida a:
- Institutos técnicos y de capacitación (ETDH)
- Educación superior (universidades, institutos)

No existe `/Peru/EBR` en su sitio (404). Esto significa que **SciBack School no tiene competidor digitalizado directo en el segmento EBR peruano**. La comparación con Q10 es útil como referencia de mercado, no como competencia directa.

---

## Precios reales Q10 Perú (ETDH) — verificados

Q10 cobra por **semestre**, no por mes.

| Plan | Semestral | Mensual equiv. | Anual (−10%) | Mensual con desc. anual |
|------|-----------|---------------|-------------|------------------------|
| Básico | S/ 980 + IGV | S/ 163/mes | S/ 1,764/año | S/ 147/mes |
| Profesional | S/ 1,580 + IGV | S/ 263/mes | S/ 2,844/año | S/ 237/mes |
| Avanzado | S/ 2,920 + IGV | S/ 487/mes | S/ 5,256/año | S/ 438/mes |

En dólares (tipo de cambio S/ 3.75):

| Plan | USD/mes sin desc. | USD/mes con desc. anual |
|------|------------------|------------------------|
| Básico | ~$43 | ~$39 |
| Profesional | ~$70 | ~$63 |
| Avanzado | ~$130 | ~$117 |

Límites de usuarios por plan:

| | Básico | Profesional | Avanzado |
|--|--------|------------|---------|
| Administrativos | 2 | 10 | 30 |
| Docentes | 10 | 25 | 50 |
| Estudiantes | Ilimitados | Ilimitados | Ilimitados |
| Almacenamiento | 100 GB | 250 GB | 500 GB |
| Sedes | 1 | 1 | 1 |

---

## Q10 vs SciBack School — tabla comparativa

| Criterio | Q10 (ETDH/Superior) | SciBack School (EBR) |
|----------|--------------------|-----------------------|
| **Segmento objetivo Perú** | Institutos técnicos, universidades | **Colegios EBR** (inicial/primaria/secundaria) |
| **Origen** | Colombia | Perú |
| **Modelo** | SaaS multi-tenant | Single-tenant dedicado |
| **Precio mensual real** | $39–130/mes | $179–349/mes (Pilot/Small) |
| **Precio incluye todo** | ✅ | ✅ |
| **Límite de docentes** | 10–50 según plan | Ilimitados |
| **Límite de admins** | 2–30 según plan | Ilimitados |
| **Datos alojados en** | Colombia | AWS Ohio (us-east-2) — servidor del cliente |
| **Ley 29733 (datos menores)** | ⚠️ Datos fuera de Perú | ✅ Servidor dedicado en EEUU |
| **Facturación electrónica SUNAT** | ✅ Incluida | ✅ NubeFact integrado |
| **SIAGIE / archivo MINEDU** | ❌ No existe | ✅ Genera .xls nativo |
| **Escala CNEB (AD/A/B/C)** | ❌ No aplica (institutos) | ✅ Nativo |
| **Yape / PagoEfectivo / Culqi** | ⚠️ Parcial | ✅ Integrado |
| **App móvil para padres** | ✅ Nativa iOS/Android | ⚠️ Portal web responsive |
| **UX / interfaz** | ✅ Pulida, moderna | ⚠️ Odoo estándar |
| **Soporte local Lima** | ❌ Remoto Colombia | ✅ Local |
| **Multi-sede** | ❌ 1 sede por plan | ✅ Multi-sede |
| **Personalización** | ⚠️ Limitada (SaaS) | ✅ Código fuente abierto |
| **Vendor lock-in** | 🔴 Alto | 🟢 Bajo — PostgreSQL exportable |
| **Tiempo de implementación** | 2–6 semanas | 1–2 semanas (automatizado) |
| **Open source** | ❌ Cerrado | ✅ Odoo + OCA |

---

## Argumentos de venta frente a Q10

1. **Segmento diferente** — Q10 no tiene producto para colegios EBR en Perú. SciBack School es específico para el colegio, no un instituto técnico adaptado.

2. **SIAGIE incluido** — El archivo .xls que exige el MINEDU/UGEL se genera con un clic. Q10 no lo tiene porque sus clientes son institutos, no colegios.

3. **Escala CNEB nativa** — AD/A/B/C, competencias por área, libretas por ciclo. Q10 no maneja el currículo de EBR.

4. **Datos en servidor propio** — Single-tenant en AWS Ohio. El colegio puede exportar toda su base de datos en cualquier momento. Con Q10, los datos viven en Colombia en infraestructura compartida.

5. **Sin límite de docentes ni admins** — Q10 Básico solo permite 10 docentes y 2 admins. Un colegio mediano supera eso fácilmente.

6. **Soporte peruano** — Mismo timezone, mismo contexto MINEDU/SUNAT/UGEL, misma cultura escolar.

---

## Debilidades a trabajar

| Debilidad SciBack School | Plan de mitigación |
|--------------------------|--------------------|
| Precio más alto en términos absolutos | Argumentar valor diferencial (SIAGIE + CNEB + sin límite usuarios) |
| Sin app móvil nativa | Portal responsive + PWA en roadmap fase 3 |
| UX Odoo percibida como "empresarial" | Tema personalizado + onboarding guiado |
| Sin historial de clientes en Perú | Agua Viva como caso de éxito documentado |
| Q10 tiene ISO 27001 + PCI DSS certificados | Apuntar a certificaciones en roadmap o destacar single-tenant como mejor modelo de seguridad |
