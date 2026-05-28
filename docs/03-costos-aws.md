# Capítulo 03 — Costos e Inversión AWS

> Área de conocimiento PMBOK: Gestión de los Costos del Proyecto  
> Región AWS producción (clientes): `us-east-2` (Ohio)  
> Región AWS labs / infra interna SciBack: `us-east-1` (Virginia)  
> Última revisión: 2026-05-27

---

## 1. Arquitectura de costos por cliente

Cada cliente recibe una instancia **completamente independiente**. No hay recursos compartidos entre clientes (sin multi-tenant). Esto simplifica el modelo de costos: `costo_total = costo_fijo_SciBack + Σ(costo_por_cliente)`.

```
┌─────────────────────────────────────────────────────────────┐
│  Cuenta AWS SciBack (us-east-1 Virginia — labs/infra)       │
│  ├── Route 53 (DNS global)                                  │
│  ├── ECR (imágenes Docker canónicas)                        │
│  └── S3 tfstate + backups cross-region                      │
│                                                             │
│  Cuenta AWS cliente-A (us-east-2 Ohio — producción)  ← aislada │
│  ├── VPC dedicada                                           │
│  ├── EC2 (Odoo + Nginx)                                     │
│  ├── RDS PostgreSQL                                         │
│  ├── S3 (adjuntos, backups)                                 │
│  ├── Elastic IP                                             │
│  └── Secrets Manager                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Tiers de dimensionamiento

### Criterios de selección de tier

| Criterio | Pilot | Small | Medium | Large |
|----------|-------|-------|--------|-------|
| Estudiantes | < 200 | 200–600 | 600–1 500 | > 1 500 |
| Docentes/admin | < 15 | 15–40 | 40–100 | > 100 |
| Transacciones SUNAT/mes | < 200 | 200–800 | 800–3 000 | > 3 000 |
| Caso típico | Piloto, IIEE pequeña | Colegio medio | Colegio grande | Consorcio / red |

---

## 3. Costos mensuales por tier (USD, precios bajo demanda `sa-east-1`)

### 3.1 Tier Pilot — ~USD 55–65/mes

> Caso uso: Escuela Cristiana Agua Viva (cliente alfa), validación de producto.

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| EC2 `t3.medium` | 2 vCPU / 4 GB RAM, 30 GB gp3 | 30.37 |
| EBS gp3 | 50 GB adicional (adjuntos Odoo) | 4.00 |
| RDS PostgreSQL `db.t3.micro` | 1 vCPU / 1 GB RAM, 20 GB gp2, Single-AZ | 12.41 |
| Elastic IP | IP estática asignada | 3.60 |
| S3 Standard | 20 GB adjuntos + backups DB | 0.46 |
| S3 Glacier IR | Backups antiguos (60 GB) | 1.20 |
| Secrets Manager | 5 secretos × $0.40 | 2.00 |
| CloudWatch | Métricas básicas + 2 alarmas | 1.00 |
| Data Transfer OUT | ~10 GB/mes | 0.90 |
| Route 53 | 1 zona hospedada + queries | 2.00 |
| **TOTAL estimado** | | **~58–63** |

> Saving: Reserved Instance 1 año (no upfront) `t3.medium` en Ohio reduce EC2 a ~$18/mes → **total ~$45–50/mes**.

---

### 3.2 Tier Small — ~USD 90–105/mes

> Caso uso: Colegio privado establecido, 200–600 estudiantes.

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| EC2 `t3.large` | 2 vCPU / 8 GB RAM, 30 GB gp3 | 48.14 |
| EBS gp3 | 100 GB adjuntos | 8.00 |
| RDS PostgreSQL `db.t3.small` | 2 vCPU / 2 GB RAM, 50 GB gp2, Single-AZ | 24.82 |
| Elastic IP | | 3.60 |
| S3 Standard | 50 GB | 1.15 |
| S3 Glacier IR | Backups (150 GB) | 3.00 |
| Secrets Manager | 8 secretos | 3.20 |
| CloudWatch | Logs + métricas + 5 alarmas | 3.00 |
| Data Transfer OUT | ~25 GB/mes | 2.25 |
| Route 53 | | 2.00 |
| **TOTAL estimado** | | **~99–108** |

> Saving: Reserved Instance 1 año `t3.large` Ohio → EC2 ~$30/mes → **total ~$76–85/mes**.

---

### 3.3 Tier Medium — ~USD 230–280/mes

> Caso uso: Colegio grande o con múltiples sedes, 600–1 500 estudiantes.

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| EC2 `t3.xlarge` | 4 vCPU / 16 GB RAM, 30 GB gp3 | 96.29 |
| EBS gp3 | 200 GB adjuntos | 16.00 |
| RDS PostgreSQL `db.t3.medium` | 2 vCPU / 4 GB RAM, 100 GB gp2, **Multi-AZ** | 83.59 |
| ALB (Application Load Balancer) | Para health checks y failover | 16.43 |
| Elastic IP | | 3.60 |
| S3 Standard | 150 GB | 3.45 |
| S3 Glacier IR | Backups (500 GB) | 10.00 |
| Secrets Manager | 12 secretos | 4.80 |
| CloudWatch | Logs completos + dashboards + 10 alarmas | 8.00 |
| Data Transfer OUT | ~60 GB/mes | 5.40 |
| Route 53 | | 2.00 |
| **TOTAL estimado** | | **~250–270** |

> Saving: Reserved 1 año Ohio → EC2 ~$60 + RDS Multi-AZ ~$54 → **total ~$195–215/mes**.

---

### 3.4 Tier Large — ~USD 600–900/mes

> Caso uso: Red de colegios, consorcio educativo, > 1 500 estudiantes.

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| EC2 `m6i.2xlarge` | 8 vCPU / 32 GB RAM | 280.32 |
| EBS gp3 | 500 GB | 40.00 |
| RDS PostgreSQL `db.r6g.large` | 2 vCPU / 16 GB RAM, 200 GB gp3, Multi-AZ | 210.24 |
| ALB | | 25.00 |
| ElastiCache Redis `cache.t3.medium` | Para colas Odoo (queue_job) | 38.69 |
| Elastic IP | | 3.60 |
| S3 Standard | 500 GB | 11.50 |
| S3 Glacier IR | Backups (2 TB) | 40.00 |
| Secrets Manager | 20 secretos | 8.00 |
| CloudWatch | Completo | 15.00 |
| Data Transfer OUT | ~150 GB/mes | 17.10 |
| Route 53 + WAF | | 12.00 |
| **TOTAL estimado** | | **~700–900** |

---

## 4. Inversión inicial (one-time) por cliente

| Ítem | Costo estimado (USD) |
|------|---------------------|
| Tiempo de provisioning (`make provision`) | $0 — automatizado |
| Certificado digital SUNAT (si no tiene) | $80–150 (compra con cliente) |
| Registro en OSE NubeFact (plan anual) | $0 plan básico / $200 plan profesional |
| Dominio institucional (si no tiene) | $12–30/año |
| Configuración inicial Odoo + datos maestros | 8–16h desarrollo ($400–800 a $50/h) |
| Capacitación usuarios (incluida en contrato) | Incluida |
| **Total inversión setup típica** | **USD 480–1 200** |

---

## 5. Costos SciBack (infraestructura interna)

Independiente de los clientes — corresponde a la operación de SciBack como empresa.

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| ECR (Docker registry) | 3 repos × ~2 GB | 0.90 |
| S3 sciback-ops backups cross-region | 50 GB | 1.15 |
| Route 53 sciback.com | Zona + queries | 2.00 |
| GitHub Actions | Plan Team | 4.00 |
| NubeFact cuenta maestra (testing) | Plan dev | 0.00 |
| **TOTAL infra SciBack** | | **~$8–10/mes** |

---

## 6. Proyección financiera — modelo de ingresos vs costos AWS

### Supuesto: tarifa mensual al cliente

| Tier | Costo AWS/mes (Ohio) | Margen objetivo | **Precio cliente/mes** |
|------|---------------------|-----------------|----------------------|
| Pilot | ~$60 | 3× | **$179–249** |
| Small | ~$100 | 2.5× | **$249–349** |
| Medium | ~$260 | 2× | **$520–699** |
| Large | ~$680 | 1.8× | **$999–1 500** |

> El margen cubre: AWS + soporte + actualizaciones + operaciones SciBack.

### Break-even operativo

Con tarifas conservadoras:

| Clientes activos | Ingresos brutos/mes | Costos AWS/mes | Margen bruto/mes |
|-----------------|--------------------|--------------|--------------------|
| 1 (Agua Viva) | $250 | $70 | $180 |
| 3 | $800 | $250 | $550 |
| 5 | $1 400 | $430 | $970 |
| 10 | $3 000 | $900 | $2 100 |
| 20 | $6 000 | $1 900 | $4 100 |

> Break-even de desarrollo (estimado 200h × $50/h = $10 000): con 3 clientes a $250/mes ≈ **33 meses**. Con precio $399 ≈ **21 meses**. Agregar cliente = $0 marginal en desarrollo.

---

## 7. Comparativa vs alternativas

| Alternativa | Costo mensual típico | Ventaja SciBack School |
|-------------|---------------------|----------------------|
| SIANET (Peru) | $150–400/mes | — |
| Gedux | $200–500/mes | — |
| Odoo Enterprise self | $310/mes (10 users) + localizaciones | Odoo Enterprise tiene lock-in de licencia |
| Google Workspace Edu + hojas | $0–4/usuario | Sin facturación SUNAT, sin notas integradas |
| **SciBack School Pilot** | **$199–299/mes** | SUNAT nativo, CNEB, SIAGIE, soporte en español, datos en Perú |

---

## 8. Estrategia de Reserved Instances

Para clientes con contrato anual (recomendado):

1. Al confirmar contrato anual → comprar Reserved Instance 1 año (no upfront) para EC2 y RDS del cliente.
2. Ahorro promedio: **35–40%** vs bajo demanda.
3. Riesgo: si cliente cancela antes de 12 meses, SciBack asume el costo residual → incluir cláusula de penalidad equivalente en contrato.

---

## 9. Monitoreo de costos

- **AWS Cost Explorer** con tags `Client`, `Product`, `Tier` en todos los recursos.
- **Budget alert** por cliente: alerta al 80% y 100% del presupuesto asignado.
- **Trusted Advisor** activado en cada cuenta para detectar recursos subutilizados.
- Review mensual: rightsizing si CPU promedio < 20% por 30 días → downgrade de tier.

---

## 10. Notas de precios

- Precios en USD, región `us-east-2` (Ohio — producción), mayo 2026.
- Tipo de cambio referencial: S/3.75 por USD.
- Los precios AWS varían; validar con [AWS Pricing Calculator](https://calculator.aws/pricing/2/home) antes de cotizar a cliente.
- Data transfer entre AZs dentro de `us-east-2` (Ohio): $0.01/GB (relevante para Multi-AZ RDS).
- Egress a internet: primeros 100 GB/mes gratis desde EC2, luego $0.09/GB (Ohio, más barato que São Paulo $0.114/GB).
