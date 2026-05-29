# Capítulo 00 — Acta de Constitución del Proyecto

> PMBOK: Project Charter | Estado: Borrador

## Identificación

| Campo | Valor |
|-------|-------|
| Nombre del proyecto | SciBack School |
| Patrocinador | Alberto Sánchez (SciBack) |
| Fecha de inicio | 2026-05 |
| Cliente alfa | Escuela Cristiana Agua Viva, Lima, Perú |
| Tipo de proyecto | Desarrollo de producto SaaS B2B |

## Propósito

Crear un sistema de gestión escolar integral para colegios privados peruanos sobre Odoo Community 17.0 + OpenEduCat, con cumplimiento nativo de SUNAT, CNEB y SIAGIE.

## Objetivo de negocio

Validar el producto con Agua Viva como cliente alfa y luego replicarlo a otros colegios sin reescribir el core (modelo canónico SciBack).

## Entregables principales

- Producto canónico desplegable (`sciback-odoo`)
- Instancia cliente Agua Viva en producción
- Documentación operativa completa
- IaC (Terraform + Ansible) para provisioning < 2 horas

## Restricciones

- Sin Odoo Enterprise (licencia paga)
- Sin Kubernetes (overhead para single-tenant)
- Sin API SIAGIE (no existe; Excel-first)
- Datos en AWS `sa-east-1` (Perú / LATAM)

## Criterios de éxito del MVP

- [ ] Matrícula completa de un ciclo académico
- [ ] Emisión de boletas SUNAT vía NubeFact
- [ ] Generación de archivo SIAGIE (.xls)
- [ ] Portal de padres funcional
- [ ] Provisioning de instancia nueva en < 2 horas
