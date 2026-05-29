# ============================================================
# SciBack Odoo — Makefile (modelo POD multi-tenant)
# Un POD aloja varios colegios (1 DB c/u). Ver README-multitenant.md
# ============================================================

POD      ?= pod-1
PLAN     ?= esencial
ENV_FILE  = .env

.PHONY: help dev stop logs shell db-shell nuevo-colegio colegios update update-all install backup provision deploy

help:
	@echo ""
	@echo "  SciBack Odoo — Comandos disponibles"
	@echo ""
	@echo "  Desarrollo local:"
	@echo "    make dev          Levantar entorno local (Docker Compose)"
	@echo "    make stop         Detener contenedores"
	@echo "    make logs         Ver logs Odoo en tiempo real"
	@echo "    make shell        Shell dentro del contenedor Odoo"
	@echo "    make db-shell DB=aguaviva   Psql dentro de la DB de un colegio"
	@echo ""
	@echo "  Multi-tenant (alta de colegios en el pod):"
	@echo "    make nuevo-colegio SLUG=aguaviva PLAN=esencial NOMBRE=\"I.E.P. Agua Viva\""
	@echo "    make colegios               Listar colegios (DBs) del pod"
	@echo ""
	@echo "  Módulos Odoo:"
	@echo "    make update DB=aguaviva MOD=sciback_sunat_nubefact   Actualizar módulo en 1 colegio"
	@echo "    make update-all MOD=sciback_sunat_nubefact            Actualizar módulo en TODOS"
	@echo "    make install DB=aguaviva MOD=sciback_school_portal    Instalar módulo en 1 colegio"
	@echo ""
	@echo "  Producción del POD (requiere configuración AWS):"
	@echo "    make provision POD=pod-1    Provisionar EC2+RDS del pod"
	@echo "    make deploy POD=pod-1        Desplegar actualización"
	@echo "    make backup POD=pod-1        Backup por-DB a S3"
	@echo ""

# ── Desarrollo local ─────────────────────────────────────────

dev:
	@test -f $(ENV_FILE) || (cp .env.example $(ENV_FILE) && echo "⚠  Creado .env desde .env.example — completa las variables antes de continuar" && exit 1)
	docker compose up -d
	@echo "✓ Pod arriba. Da de alta un colegio: make nuevo-colegio SLUG=aguaviva PLAN=esencial"
	@echo "  Acceso dev: http://<slug>.localhost"

stop:
	docker compose down

logs:
	docker compose logs -f odoo

shell:
	docker compose exec odoo bash

db-shell:
	@test -n "$(DB)" || (echo "Uso: make db-shell DB=aguaviva" && exit 1)
	docker compose exec db psql -U $${POSTGRES_USER:-odoo} $(DB)

# ── Multi-tenant ─────────────────────────────────────────────

nuevo-colegio:
	@test -n "$(SLUG)" || (echo "Uso: make nuevo-colegio SLUG=aguaviva PLAN=esencial NOMBRE=\"...\"" && exit 1)
	./scripts/nuevo-colegio.sh "$(SLUG)" "$(PLAN)" "$(NOMBRE)"

colegios:
	@docker compose exec -T db psql -U $${POSTGRES_USER:-odoo} -d postgres -tAc \
	  "SELECT datname FROM pg_database WHERE datistemplate=false AND datname<>'postgres' ORDER BY datname;"

# ── Módulos Odoo ─────────────────────────────────────────────

update:
	@test -n "$(DB)" || (echo "Uso: make update DB=aguaviva MOD=nombre_modulo" && exit 1)
	@test -n "$(MOD)" || (echo "Uso: make update DB=aguaviva MOD=nombre_modulo" && exit 1)
	docker compose exec odoo odoo -d $(DB) -u $(MOD) --stop-after-init

update-all:
	@test -n "$(MOD)" || (echo "Uso: make update-all MOD=nombre_modulo" && exit 1)
	@for db in $$(docker compose exec -T db psql -U $${POSTGRES_USER:-odoo} -d postgres -tAc \
	   "SELECT datname FROM pg_database WHERE datistemplate=false AND datname<>'postgres'"); do \
	  echo "→ actualizando $(MOD) en $$db"; \
	  docker compose exec -T odoo odoo -d $$db -u $(MOD) --stop-after-init; \
	done

install:
	@test -n "$(DB)" || (echo "Uso: make install DB=aguaviva MOD=nombre_modulo" && exit 1)
	@test -n "$(MOD)" || (echo "Uso: make install DB=aguaviva MOD=nombre_modulo" && exit 1)
	docker compose exec odoo odoo -d $(DB) -i $(MOD) --stop-after-init

# ── Producción del POD ───────────────────────────────────────

provision:
	@echo "→ Provisionando POD $(POD)..."
	cd terraform && terraform init -backend-config="key=$(POD)/terraform.tfstate"
	cd terraform && terraform apply -var="pod_id=$(POD)" -auto-approve
	ansible-playbook ansible/playbook.yml -i ansible/inventory.yml -e "pod_id=$(POD)"
	@echo "✓ POD $(POD) listo"

deploy:
	@echo "→ Desplegando actualización en POD $(POD)..."
	ansible-playbook ansible/playbook.yml -i ansible/inventory.yml -e "pod_id=$(POD) action=update"

backup:
	@echo "→ Backup por-DB del POD $(POD)..."
	ansible-playbook ansible/playbook.yml -i ansible/inventory.yml -e "pod_id=$(POD) action=backup"
