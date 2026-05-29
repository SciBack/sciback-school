# Despliegue multi-tenant (POD)

> Un **POD** = 1 EC2 + 1 RDS que aloja **varios colegios**, una base de datos por colegio,
> aislados por subdominio. Es el modelo que hace rentables los colegios pequeños (<300) y
> nano (<100). Detalle de costos en `docs/03-costos-aws.md`.

## Cómo funciona

```
https://aguaviva.colegios.sciback.com ─┐
https://sanpablo.colegios.sciback.com ─┼─► nginx (wildcard) ─► Odoo ─► dbfilter=^%d$ ─► DB del colegio
https://otrocolegio.colegios.sciback.com┘        (1 instancia, N colegios)
```

- **nginx** captura `*.${BASE_DOMAIN}` y reenvía con `Host` intacto.
- **Odoo** (`dbfilter = ^%d$`, `list_db = False`) toma la primera etiqueta del host
  (`aguaviva.colegios... → aguaviva`) y sirve esa DB. Sin subdominio válido → sin acceso.
- **Aislamiento**: cada colegio tiene su DB y su filestore (Odoo los separa por DB).
  SUNAT/NubeFact y Culqi se configuran **dentro de cada DB** (`sciback.school.config`), no en el `.env`.

## Requisitos de DNS y TLS

1. **DNS wildcard**: registro `*.${BASE_DOMAIN}` → Elastic IP del pod (Route 53).
2. **Certificado wildcard** vía Let's Encrypt **DNS-01** (HTTP-01 no emite wildcards):

   ```bash
   # En el host del pod (requiere plugin route53 y credenciales AWS)
   certbot certonly --dns-route53 \
     -d "${BASE_DOMAIN}" -d "*.${BASE_DOMAIN}" \
     --non-interactive --agree-tos -m ops@sciback.com
   ```

   El cert queda en `/etc/letsencrypt/live/${BASE_DOMAIN}/` y nginx lo monta (ver
   `nginx/odoo.conf.template`). Un solo cert cubre **todos** los colegios del pod.

## Alta de un colegio nuevo (provisioning = $0 de infraestructura)

```bash
# En el host del pod
cd /opt/sciback-odoo/deploy
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml" \
BASE_DOMAIN=colegios.sciback.com \
  ./scripts/nuevo-colegio.sh aguaviva esencial "I.E.P. Agua Viva"
```

Crea la DB, instala los módulos del plan (`esencial` | `profesional`) y etiqueta la compañía.
Acceso inmediato en `https://aguaviva.colegios.sciback.com` (admin/admin → cambiar).

En dev local (puerto 80, sin SSL): `make nuevo-colegio SLUG=aguaviva PLAN=esencial` → `http://aguaviva.localhost`.

## Archivos

| Archivo | Rol |
|---|---|
| `odoo/odoo.conf` | `dbfilter=^%d$`, `list_db=False`, workers parametrizados |
| `nginx/odoo.conf` | nginx dev (HTTP, `*.localhost`) |
| `nginx/odoo.conf.template` | nginx prod (SSL wildcard); Ansible lo renderiza con `BASE_DOMAIN` → `nginx/odoo.conf` en el host |
| `scripts/nuevo-colegio.sh` | alta de colegio (DB + módulos del plan) |
| `.env.example` | variables del POD (no del cliente) |

## Pendiente (Fase 8 — IaC del pod)

- [ ] **Terraform**: parametrizar por `pod_id` (hoy `client_slug`); EC2 `t3.xlarge` + RDS `db.t3.medium` por pod.
- [ ] **Ansible**: renderizar `nginx/odoo.conf.template` con `BASE_DOMAIN`; emitir cert wildcard DNS-01; inyectar `ODOO_WORKERS`.
- [ ] **Backups por-DB**: `pg_dump` por colegio → S3 (no `pg_dumpall` del pod) para restaurar un colegio sin tocar a los demás.
- [ ] **Onboarding**: tras `nuevo-colegio.sh`, automatizar carga de `sciback.school.config` (RUC, token NubeFact, serie) desde el overlay del cliente.
- [ ] **Límite de densidad**: alertar cuando el pod supere ~85% CPU/RAM → abrir POD-2.
