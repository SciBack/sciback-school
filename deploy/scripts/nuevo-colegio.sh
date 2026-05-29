#!/usr/bin/env bash
# ============================================================
# SciBack Odoo — Alta de un colegio en un POD multi-tenant
# Crea una DB nueva e instala los módulos del plan contratado.
# Provisioning de infraestructura = $0 (no crea EC2/RDS; solo una DB).
#
# Uso:
#   ./nuevo-colegio.sh <slug> <plan> ["Nombre del Colegio"]
#
#   <slug>  nombre-host del colegio = nombre de la DB = subdominio.
#           Solo [a-z0-9-], sin guion bajo (debe ser válido como hostname).
#           Acceso final: https://<slug>.<BASE_DOMAIN>
#   <plan>  esencial | profesional
#           (enterprise NO va en pod compartido — usa instancia dedicada)
#
# Ejemplos:
#   ./nuevo-colegio.sh aguaviva esencial "I.E.P. Agua Viva"
#   ./nuevo-colegio.sh sanpablo profesional "Colegio San Pablo"
# ============================================================
set -euo pipefail

SLUG="${1:-}"
PLAN="${2:-esencial}"
NOMBRE="${3:-}"

COMPOSE="${COMPOSE:-docker compose}"        # en prod: docker compose -f docker-compose.yml -f docker-compose.prod.yml
ODOO_SVC="${ODOO_SVC:-odoo}"
BASE_DOMAIN="${BASE_DOMAIN:-localhost}"

# ── Validaciones ─────────────────────────────────────────────
if [[ -z "$SLUG" ]]; then
  echo "Uso: $0 <slug> <plan> [\"Nombre del Colegio\"]" >&2
  exit 1
fi
if ! [[ "$SLUG" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "✗ slug inválido: '$SLUG'. Solo minúsculas, dígitos y guiones (no '_', no inicia/termina con '-')." >&2
  echo "  Motivo: el slug es a la vez nombre de DB y subdominio (hostname)." >&2
  exit 1
fi

# ── Módulos por plan ─────────────────────────────────────────
# Núcleo común (todos los planes). Orden importa: 'website' antes de OpenEduCat (dep oculta O17).
CORE="base,web,website,l10n_pe,queue_job"
OE_ESENCIAL="openeducat_core,openeducat_admission,openeducat_attendance,openeducat_exam,openeducat_fees,openeducat_timetable"
SCIBACK_ESENCIAL="sciback_school_base,sciback_sunat_nubefact"
# Pendientes (cuando estén implementados, añadir al Esencial):
#   sciback_cneb_evaluation,sciback_siagie_connector,sciback_school_portal,sciback_ley29733_compliance

OE_PROFESIONAL="openeducat_classroom,openeducat_library,openeducat_assignment,openeducat_activity"
SCIBACK_PROFESIONAL="sciback_payment_culqi,sciback_payment_yape,sciback_payment_pagoefectivo"

case "$PLAN" in
  esencial)
    MODULES="${CORE},${OE_ESENCIAL},${SCIBACK_ESENCIAL}"
    ;;
  profesional)
    MODULES="${CORE},${OE_ESENCIAL},${OE_PROFESIONAL},${SCIBACK_ESENCIAL},${SCIBACK_PROFESIONAL}"
    ;;
  enterprise)
    echo "✗ El plan 'enterprise' usa instancia DEDICADA, no un pod compartido." >&2
    exit 1
    ;;
  *)
    echo "✗ Plan desconocido: '$PLAN'. Use: esencial | profesional" >&2
    exit 1
    ;;
esac

echo "→ Alta de colegio"
echo "    slug/DB   : $SLUG"
echo "    plan      : $PLAN"
echo "    URL final : https://${SLUG}.${BASE_DOMAIN}"
echo "    módulos   : $MODULES"
echo ""

# ── ¿La DB ya existe? ────────────────────────────────────────
if $COMPOSE exec -T db psql -U "${POSTGRES_USER:-odoo}" -tAc \
     "SELECT 1 FROM pg_database WHERE datname='${SLUG}'" postgres | grep -q 1; then
  echo "✗ La base '$SLUG' ya existe. Aborto." >&2
  exit 1
fi

# ── Crear DB + instalar módulos (odoo lo crea, no el web manager) ──
echo "→ Creando DB e instalando módulos (puede tardar varios minutos)..."
$COMPOSE exec -T "$ODOO_SVC" odoo \
  -d "$SLUG" \
  -i "$MODULES" \
  --load=base,web \
  --without-demo=all \
  --stop-after-init

# ── Etiquetar el colegio (nombre de la compañía) ─────────────
if [[ -n "$NOMBRE" ]]; then
  echo "→ Asignando nombre de la compañía: $NOMBRE"
  $COMPOSE exec -T db psql -U "${POSTGRES_USER:-odoo}" -d "$SLUG" \
    -c "UPDATE res_company SET name=\$\$${NOMBRE}\$\$ WHERE id=1;" >/dev/null
fi

echo ""
echo "✓ Colegio '$SLUG' creado."
echo "  Acceso: https://${SLUG}.${BASE_DOMAIN}   (admin / admin — CAMBIAR de inmediato)"
echo "  Siguiente: configurar sciback.school.config (RUC, token NubeFact, serie SUNAT)."
