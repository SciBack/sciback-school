#!/usr/bin/env python3
"""
Carga out/hubspot_companies.csv a HubSpot vía CRM Import API (job asíncrono).
Dedupe/upsert por la propiedad única `codigo_local`.

Uso:
  .venv/bin/python hubspot_import.py                       # importa out/hubspot_companies.csv
  .venv/bin/python hubspot_import.py file out/X.csv "Nom"  # importa otro CSV (upsert por codigo_local)
  .venv/bin/python hubspot_import.py status ID             # consulta estado del job
"""
import os, sys, json, requests

def load_token():
    vals = {}
    for line in open(os.path.expanduser("~/.secrets/hubspot.env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1); vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals.get("HUBSPOT_TOKEN") or vals.get("HUBSPOT_API_KEY")

TOKEN = load_token()
BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(BASE, "out", "hubspot_companies.csv")

def mapping(col):
    m = {"columnObjectTypeId": "0-2", "columnName": col,
         "propertyName": col, "columnType": "STANDARD"}
    if col == "codigo_local":
        m["columnType"] = "HUBSPOT_ALTERNATE_ID"   # clave de dedupe/upsert
    return m

def launch(csv_path=DEFAULT_CSV, name="Padrón MINEDU - IIEE Perú (SciBack Edu)"):
    cols = open(csv_path, encoding="utf-8").readline().strip().split(",")
    fname = os.path.basename(csv_path)
    req = {
        "name": name,
        "importOperations": {"0-2": "UPSERT"},
        "dateFormat": "YEAR_MONTH_DAY",
        "files": [{
            "fileName": fname,
            "fileFormat": "CSV",
            "fileImportPage": {"hasHeader": True,
                "columnMappings": [mapping(c) for c in cols]},
        }],
    }
    r = requests.post("https://api.hubapi.com/crm/v3/imports",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files={"importRequest": (None, json.dumps(req)),
               "files": (fname, open(csv_path, "rb"), "text/csv")})
    print("HTTP", r.status_code)
    if r.status_code < 300:
        d = r.json(); print("importId:", d.get("id"), "| state:", d.get("state"))
    else:
        print(r.text[:600])

def status(imp_id):
    r = requests.get(f"https://api.hubapi.com/crm/v3/imports/{imp_id}",
        headers={"Authorization": f"Bearer {TOKEN}"})
    d = r.json()
    cnt = d.get("metadata", {}).get("counters", {}) if isinstance(d.get("metadata"), dict) else {}
    print(f"state: {d.get('state')}  counters: {json.dumps(d.get('metadata',{}).get('counters', cnt))}")
    print(json.dumps({k: d.get(k) for k in ('state','optOutImport')}, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "status":
        status(sys.argv[2])
    elif len(sys.argv) > 2 and sys.argv[1] == "file":
        launch(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Enriquecimiento Identicole")
    else:
        launch()
