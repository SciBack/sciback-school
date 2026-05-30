# Prospección — Base de datos de instituciones educativas (MINEDU → HubSpot)

Pipeline de marketing/prospección para SciBack Edu: construir y mantener la base
de **todas las instituciones educativas del Perú** como prospectos en HubSpot,
etiquetadas por tipo (colegio / instituto / escuela superior / CETPRO / universidad),
gestión (privada / pública) y enriquecidas con pensiones declaradas.

> Activo de marketing **canónico** de SciBack. NO contiene datos de clientes.

## Hallazgo de interoperabilidad (mayo 2026)

No existe API/protocolo de interoperabilidad formal en las fuentes MINEDU. El flujo es
**descarga de archivo → ETL → carga**. Detalle:

| Fuente | Acceso | Aporta |
|---|---|---|
| **ESCALE** padrón | Descarga ZIP/DBF (sin API) | Base maestra: 180k servicios, gestión, contacto, RUC, promotor, geo |
| **datosabiertos.gob.pe** | API DKAN (`/api/action/datastore/search.json?resource_id=`) | SUNEDU (universidades), IEST |
| **Identicole** | Scraping por código modular (sin API) | Pensión + cuota + nº alumnos (segmentación por plan) |
| **infocole.ugel05** | Solo web | Marginal (solo UGEL 05) |
| `datos.minedu.gob.pe` | Caído | — |

## Fuente maestra: padrón ESCALE

URL estable (cambia la fecha del nombre, ~semanal):
```
https://escale.minedu.gob.pe/documents/10156/958881/Padron_web_<AAAAMMDD>.zip
```
Contiene `Padron_web.dbf` (encoding **cp850**, 47 campos). Diccionario oficial dentro del ZIP.

## Pipeline

```
1. Descargar padrón     → data/Padron_web_<fecha>.zip  (curl)
2. ETL                  → out/colegios_master.csv      (etl_padron.py)
3. Enriquecer Identicole→ pensión/cuota/alumnos         (enrich_identicole.py) [fase C]
4. Cargar a HubSpot     → propiedades custom + import por lotes (API REST) [fase D]
```

### Reglas de modelado
- **1 LOCAL educativo (`CODLOCAL`) = 1 Company.** Los servicios del mismo local
  (Inicial+Primaria+Secundaria = 3 `COD_MOD`) se consolidan en una company.
- Dedupe key en HubSpot: `codigo_local`.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install dbfread
.venv/bin/python etl_padron.py            # solo activos
.venv/bin/python etl_padron.py --incluir-inactivos
```

## Cifras (padrón 2026-05-20, solo activos)

- 87,764 instituciones (locales) — 15,539 privadas / 71,484 públicas
- COLEGIO 84,802 · CETPRO 1,668 · INSTITUTO 1,180 · ESCUELA_SUPERIOR 114
- Universidades: NO están en ESCALE → fuente SUNEDU (datos abiertos)
