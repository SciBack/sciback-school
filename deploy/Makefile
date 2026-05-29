# ============================================================
# SciBack School — Makefile
# ============================================================

CLIENT   ?= agua-viva
TIER     ?= pilot
ENV_FILE  = .env

.PHONY: help dev stop logs shell db-shell update backup provision

help:
	@echo ""
	@echo "  SciBack School — Comandos disponibles"
	@echo ""
	@echo "  Desarrollo local:"
	@echo "    make dev          Levantar entorno local (Docker Compose)"
	@echo "    make stop         Detener contenedores"
	@echo "    make logs         Ver logs Odoo en tiempo real"
	@echo "    make shell        Shell dentro del contenedor Odoo"
	@echo "    make db-shell     Psql dentro del contenedor PostgreSQL"
	@echo ""
	@echo "  Módulos Odoo:"
	@echo "    make update MOD=sciback_siagie_connector   Actualizar un módulo"
	@echo "    make install MOD=sciback_school_portal      Instalar módulo nuevo"
	@echo ""
	@echo "  Producción (requiere CLIENT y configuración AWS):"
	@echo "    make provision CLIENT=agua-viva TIER=pilot  Provisionar instancia nueva"
	@echo "    make deploy CLIENT=agua-viva                Desplegar actualización"
	@echo "    make backup CLIENT=agua-viva                Backup manual a S3"
	@echo ""

# ── Desarrollo local ─────────────────────────────────────────

dev:
	@test -f $(ENV_FILE) || (cp .env.example $(ENV_FILE) && echo "⚠  Creado .env desde .env.example — completa las variables antes de continuar" && exit 1)
	docker compose up -d
	@echo "✓ Odoo disponible en http://localhost:80"

stop:
	docker compose down

logs:
	docker compose logs -f odoo

shell:
	docker compose exec odoo bash

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-odoo} $${POSTGRES_DB:-sciback_school}

# ── Módulos Odoo ─────────────────────────────────────────────

update:
	@test -n "$(MOD)" || (echo "Uso: make update MOD=nombre_modulo" && exit 1)
	docker compose exec odoo odoo -d $${POSTGRES_DB:-sciback_school} -u $(MOD) --stop-after-init

install:
	@test -n "$(MOD)" || (echo "Uso: make install MOD=nombre_modulo" && exit 1)
	docker compose exec odoo odoo -d $${POSTGRES_DB:-sciback_school} -i $(MOD) --stop-after-init

# ── Producción ───────────────────────────────────────────────

provision:
	@echo "→ Provisionando cliente $(CLIENT) en tier $(TIER)..."
	cd terraform && terraform init -backend-config="key=$(CLIENT)/terraform.tfstate"
	cd terraform && terraform apply -var="client_slug=$(CLIENT)" -var="tier=$(TIER)" -auto-approve
	ansible-playbook ansible/playbook.yml -i ansible/inventory.yml \
	  -e "client_slug=$(CLIENT) tier=$(TIER)"
	@echo "✓ Instancia $(CLIENT) lista"

deploy:
	@echo "→ Desplegando actualización en $(CLIENT)..."
	ansible-playbook ansible/playbook.yml -i ansible/inventory.yml \
	  -e "client_slug=$(CLIENT) action=update"

backup:
	@echo "→ Backup manual de $(CLIENT)..."
	ansible-playbook ansible/playbook.yml -i ansible/inventory.yml \
	  -e "client_slug=$(CLIENT) action=backup"
