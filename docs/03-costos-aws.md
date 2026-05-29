# Capítulo 03 — Costos e Inversión AWS

> Área de conocimiento PMBOK: Gestión de los Costos del Proyecto
> Región AWS producción (clientes): `us-east-2` (Ohio)
> Región AWS labs / infra interna SciBack: `us-east-1` (Virginia)
> Última revisión: **2026-05-29** — reescrito al modelo **multi-tenant** (ver memoria `sciback-odoo-multitenant`)

---

## 0. Cambio de modelo (2026-05-29)

> **La versión anterior de este documento asumía una instancia dedicada (EC2+RDS) por
> cliente.** Eso hacía inviable atender colegios pequeños: el AWS dedicado (~$45-60/mes)
> deja margen ~0% frente a una tarifa de S/199. El modelo correcto, alineado con
> `CLAUDE.md` y la memoria `sciback-school-pricing`, es **multi-tenant**.

Validado en el lab el 2026-05-29: varios colegios en **una sola instancia Odoo**, una DB
por colegio, aislados por subdominio (`dbfilter` + nginx). Detalle técnico en la memoria
`sciback-odoo-multitenant`.

---

## 1. Dos arquitecturas de hosting

| Arquitectura | Para quién | Recursos AWS |
|---|---|---|
| **A — Pod compartido (multi-tenant)** | Colegios Nano / Pequeño / Mediano | 1 EC2 + 1 RDS alojan **N colegios** (1 DB c/u) |
| **B — Dedicada** | Enterprise (grandes, multi-sede, requisito contractual de aislamiento físico) | 1 EC2 + 1 RDS Multi-AZ por colegio |

```
┌──────────────────────────────────────────────────────────────┐
│  Cuenta AWS SciBack (us-east-1 Virginia — labs/infra)         │
│  ├── Route 53 (DNS + wildcard *.colegios.sciback.com)         │
│  ├── ECR (imágenes Docker canónicas)                          │
│  └── S3 tfstate + backups cross-region                        │
│                                                               │
│  Cuenta AWS producción (us-east-2 Ohio)                       │
│  ├── POD-1 (multi-tenant)  ← 1 EC2 + 1 RDS                    │
│  │     ├── DB aguaviva     (colegio A)                        │
│  │     ├── DB sanpablo     (colegio B)                        │
│  │     └── … hasta ~10-15 colegios pequeños                   │
│  ├── POD-2 (multi-tenant)  ← se crea al llenarse el POD-1     │
│  └── EC2 dedicada cliente-Enterprise (aislada)               │
└──────────────────────────────────────────────────────────────┘
```

Aislamiento entre colegios del mismo pod: cada uno tiene **su propia base de datos** y su
**filestore separado** (Odoo lo gestiona por-DB). Backups por-DB (`pg_dump` por colegio),
no por instancia.

---

## 2. Escalones de tamaño

> Se añade el escalón **Nano (<100 alumnos)** — refleja la realidad del mercado peruano:
> muchas IIEE privadas tienen menos de 100 estudiantes.

| Criterio | **Nano** | **Pequeño** | **Mediano** | **Grande (Enterprise)** |
|----------|----------|-------------|-------------|--------------------------|
| Estudiantes | **< 100** | 100 – 300 | 301 – 800 | > 800 |
| Docentes/admin | < 8 | 8 – 20 | 21 – 50 | > 50 |
| Usuarios concurrentes pico | < 8 | < 15 | 15 – 40 | > 40 |
| Transacciones SUNAT/mes | < 120 | 120 – 400 | 400 – 1 500 | > 1 500 |
| Hosting | Pod compartido | Pod compartido | Pod compartido | Dedicado |
| Colegios por pod | ~15 | ~10 | ~4 | 1 |
| RAM efectiva / colegio | ~0.8 GB | ~1.5 GB | ~4 GB | 16 GB |
| Almacenamiento / colegio | 10 GB | 20 GB | 50 GB | 200 GB |

---

## 3. Costo de un POD compartido (multi-tenant)

Un pod es un servidor que aloja varios colegios. El costo se **reparte** entre los colegios
que aloja → el costo por colegio baja con la densidad.

### 3.1 POD estándar — `t3.xlarge` (USD, Ohio, bajo demanda)

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| EC2 `t3.xlarge` | 4 vCPU / 16 GB RAM, 30 GB gp3 (Odoo + Nginx, workers compartidos) | 96.29 |
| EBS gp3 | 200 GB adjuntos (todos los colegios del pod) | 16.00 |
| RDS PostgreSQL `db.t3.medium` | 2 vCPU / 4 GB, 100 GB gp3, Single-AZ (N bases) | 60.00 |
| Elastic IP | | 3.60 |
| S3 Standard + Glacier IR | Adjuntos + backups por-DB | 6.00 |
| Secrets Manager | ~10 secretos | 4.00 |
| CloudWatch | Logs + métricas + alarmas del pod | 6.00 |
| Data Transfer OUT | ~40 GB/mes agregado | 3.60 |
| Route 53 | Zona + wildcard | 2.00 |
| **TOTAL pod (on-demand)** | | **~197** |
| **TOTAL pod (Reserved 1 año)** | EC2 ~$60 + RDS ~$40 | **~135** |

### 3.2 Costo por colegio según densidad y escalón

| Escalón | Colegios/pod | Costo AWS/colegio (on-demand) | Costo AWS/colegio (Reserved) |
|---------|--------------|-------------------------------|------------------------------|
| **Nano** (<100) | ~15 | **~$13** | **~$9** |
| **Pequeño** (100–300) | ~10 | **~$20** | **~$14** |
| **Mediano** (301–800) | ~4 | **~$49** | **~$34** |

> El primer colegio de un pod "carga" el costo fijo; el break-even del pod se alcanza al
> 4º–5º colegio. Mientras el pod no esté lleno, el costo/colegio es mayor (ver §6).

### 3.3 Enterprise — instancia dedicada (Reserved aprox.)

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| EC2 `t3.xlarge`/`m6i.xlarge` | dedicado | 60–120 |
| RDS `db.t3.medium` **Multi-AZ** | aislado, alta disponibilidad | 84 |
| ALB + ElastiCache (opcional) | failover / colas | 35–55 |
| S3 + Secrets + CloudWatch + DT | | ~30 |
| **TOTAL dedicado** | | **~210–290/mes** |

---

## 4. Inversión inicial (one-time) por cliente

| Ítem | Costo estimado (USD) |
|------|---------------------|
| Provisioning (alta de DB en pod, automatizado) | $0 |
| Certificado digital SUNAT (si no tiene) | $80–150 (con cliente) |
| Registro OSE NubeFact | $0 plan básico / $200 profesional |
| Dominio institucional (si no tiene) | $12–30/año |
| Config inicial + carga datos maestros | 6–12h ($300–600 a $50/h) |
| Capacitación | Incluida en contrato |
| **Total setup típico (Nano/Pequeño)** | **USD 300–800** |

> En multi-tenant el provisioning de un colegio nuevo es **$0 marginal de infraestructura**
> (no se crea EC2/RDS; solo una base de datos en un pod existente).

---

## 5. Costos SciBack (infraestructura interna)

| Servicio | Especificación | USD/mes |
|----------|---------------|---------|
| ECR (Docker registry) | 3 repos × ~2 GB | 0.90 |
| S3 sciback-ops backups cross-region | 50 GB | 1.15 |
| Route 53 sciback.com | Zona + queries | 2.00 |
| GitHub Actions | Plan Team | 4.00 |
| NubeFact cuenta maestra (testing) | Plan dev | 0.00 |
| **TOTAL infra SciBack** | | **~$8–10/mes** |

---

## 6. Pricing y márgenes (modelo multi-tenant)

### 6.1 Tarifa sugerida por escalón

| Escalón | Plan | Costo AWS/mes (Reserved, pod lleno) | **Precio cliente/mes** | Precio anual (2 meses gratis) | Setup | Margen bruto |
|---------|------|--------------------------------------|------------------------|-------------------------------|-------|--------------|
| **Nano** (<100) | Esencial Nano | ~$9 (S/45) | **S/149** | S/1 490 | S/249 | ~70% |
| **Pequeño** (100–300) | Esencial | ~$14 (S/53) | **S/199** | S/1 990 | S/499 | ~73% |
| **Mediano** (301–800) | Profesional | ~$34 (S/128) | **S/599** | S/5 990 | S/1 499 | ~79% |
| **Grande** (>800) | Enterprise | ~$250 (S/940) | **S/1 899** | S/18 990 | S/4 999 | ~50% |

> ✅ **Precio Nano confirmado 2026-05-29: S/149/mes** (setup S/249, anual con 2 meses gratis).
> El salto Nano→Esencial es pequeño (×1.33) porque solo cambia el límite de alumnos, no las
> funciones; los saltos Esencial→Profesional (×3) y Profesional→Enterprise (×3.2) sí pagan
> capacidades nuevas. El margen neto del Nano (~30%, restando soporte) se sostiene **solo con
> soporte self-service/email**; por eso no se bajó a S/129.

### 6.2 Por qué multi-tenant cambia todo para colegios pequeños

| | Modelo viejo (dedicado) | Modelo nuevo (multi-tenant) |
|---|---|---|
| AWS por colegio Nano | ~$50/mes | **~$9–13/mes** |
| Margen a S/199 | ❌ ~0% | ✅ ~75–90% |
| Provisioning de cliente nuevo | nueva EC2+RDS | **solo una DB** ($0 infra) |
| Viabilidad de atender <100 alumnos | No rentable | **Rentable** |

### 6.3 Curva de llenado de un pod (escalón Pequeño, Reserved)

El costo fijo del pod (~$135/mes) se diluye conforme entran colegios:

| Colegios en el pod | Costo AWS/colegio | Margen a S/199 (~$53) |
|--------------------|-------------------|------------------------|
| 1 | $135 | ❌ negativo |
| 3 | $45 | ~15% |
| 5 | $27 | ~49% |
| 8 | $17 | ~68% |
| 10 (lleno) | $14 | ~73% |

> **Regla operativa:** un pod nuevo es deficitario hasta el ~3er colegio. Estrategia: no
> abrir POD-2 hasta que POD-1 tenga ≥8 colegios. Mezclar Nano+Pequeño en el mismo pod
> acelera el llenado.

---

## 7. Break-even y proyección

| Clientes activos | Ingresos brutos/mes (mix S/129–199) | Costos AWS/mes | Margen bruto/mes |
|-----------------|--------------------------------------|----------------|--------------------|
| 1 (Agua Viva) | S/199 | ~$135 (1 pod) | ~S/(305) déficit |
| 5 | ~S/800 | ~$135 (1 pod) | ~S/290 |
| 10 (pod lleno) | ~S/1 700 | ~$135 | ~S/1 195 |
| 20 (2 pods) | ~S/3 400 | ~$270 | ~S/2 390 |
| 40 (3–4 pods) | ~S/6 800 | ~$540 | ~S/4 775 |

> Break-even de desarrollo (~200h × $50/h = $10 000): con 10 colegios en un pod a S/199 ≈
> **~16 meses**. Cada colegio adicional dentro de un pod existente = **$0 marginal**.

---

## 8. Comparativa vs alternativas

| Alternativa | Costo mensual típico | Ventaja SciBack Edu |
|-------------|---------------------|----------------------|
| SIANET (Perú) | $150–400/mes | — |
| Gedux | $200–500/mes | — |
| Odoo Enterprise self | $310/mes (10 users) + localizaciones | Lock-in de licencia |
| Google Workspace Edu + hojas | $0–4/usuario | Sin SUNAT, sin notas integradas |
| **SciBack Edu Nano** | **S/129–199/mes** | SUNAT nativo, CNEB, SIAGIE, soporte español, datos en Perú, **viable para <100 alumnos** |

---

## 9. Estrategia de Reserved Instances

1. Comprar Reserved Instance 1 año (no upfront) para **cada pod** (no por cliente) una vez
   tenga ≥3 colegios estables → ahorro **35–40%**.
2. El pod es el activo reservado; los colegios entran/salen sin afectar la reserva.
3. Para Enterprise dedicado: Reserved al confirmar contrato anual + cláusula de penalidad
   por cancelación temprana (SciBack asume el residual).

---

## 10. Monitoreo de costos

- **AWS Cost Explorer** con tags `Pod`, `Product`, `Tier`. (El tag `Client` ya no aplica a
  recursos compartidos; se contabiliza a nivel de pod.)
- **Costeo por colegio**: derivado (costo del pod ÷ nº de colegios activos), no por recurso AWS.
- **Budget alert por pod**: alerta al 80% / 100%.
- Review mensual: si un pod supera ~85% de CPU/RAM sostenido → mover colegios a POD nuevo o
  promover el más grande a Enterprise dedicado.

---

## 11. Notas de precios

- Precios USD, región `us-east-2` (Ohio), mayo 2026. Tipo de cambio referencial: **S/3.75/USD**.
- Validar con [AWS Pricing Calculator](https://calculator.aws/pricing/2/home) antes de cotizar.
- Densidades de colegios/pod son estimaciones a confirmar con load test (Fase 7 del cronograma).
- Egress a internet: primeros 100 GB/mes gratis desde EC2, luego $0.09/GB (Ohio).
