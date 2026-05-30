#!/bin/bash
# Espera a que termine enrich_identicole.py (lo reanuda si se corta) y al
# detectar "FIN." sube el enriquecimiento a HubSpot (upsert por codigo_local).
cd "$(dirname "$0")"
LOG=out/identicole.log
ULOG=out/upsert_identicole.log
echo "$(date '+%F %T') watcher iniciado" >> "$ULOG"
while ! grep -q "^FIN\." "$LOG" 2>/dev/null; do
  if ! pgrep -f enrich_identicole.py >/dev/null 2>&1; then
    echo "$(date '+%F %T') scraping no activo y sin FIN -> resume" >> "$ULOG"
    nohup .venv/bin/python enrich_identicole.py >> "$LOG" 2>&1 &
  fi
  sleep 120
done
echo "$(date '+%F %T') scraping FIN detectado -> subiendo enriquecimiento" >> "$ULOG"
.venv/bin/python hubspot_import.py file out/identicole_enrich.csv "Enriquecimiento Identicole" >> "$ULOG" 2>&1
echo "$(date '+%F %T') upsert lanzado (ver importId arriba)" >> "$ULOG"
