#!/usr/bin/env python3
"""
Crea el grupo y las propiedades custom en HubSpot (objeto Company) para la
base de prospección MINEDU. Idempotente: si una propiedad ya existe, la omite.

Requiere ~/.secrets/hubspot.env con HUBSPOT_TOKEN (o HUBSPOT_API_KEY).
Scope necesario: crm.schemas.companies.write
"""
import os, sys, json, requests

def load_token():
    env = os.path.expanduser("~/.secrets/hubspot.env")
    vals = {}
    for line in open(env):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals.get("HUBSPOT_TOKEN") or vals.get("HUBSPOT_API_KEY")

TOKEN = load_token()
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = "https://api.hubapi.com/crm/v3/properties/companies"
GROUP = "minedu_sciback_edu"

def opts(*labels):
    return [{"label": l, "value": l, "displayOrder": i} for i, l in enumerate(labels)]

PROPS = [
    {"name": "codigo_local", "label": "Código de local (MINEDU)", "type": "string",
     "fieldType": "text", "hasUniqueValue": True},
    {"name": "tipo_institucion", "label": "Tipo de institución", "type": "enumeration",
     "fieldType": "select", "options": opts("COLEGIO","INSTITUTO","ESCUELA_SUPERIOR","CETPRO","UNIVERSIDAD","OTRO")},
    {"name": "etapa", "label": "Etapa educativa", "type": "enumeration", "fieldType": "select",
     "options": opts("EBR","EBA","EBE","SUPERIOR","TECNICO_PRODUCTIVA","OTRO")},
    {"name": "niveles_educativos", "label": "Niveles educativos", "type": "string", "fieldType": "text"},
    {"name": "gestion", "label": "Gestión", "type": "enumeration", "fieldType": "select",
     "options": opts("Privada","Pública de gestión directa","Pública de gestión privada")},
    {"name": "es_privado", "label": "¿Es privado?", "type": "enumeration", "fieldType": "booleancheckbox",
     "options": opts("Sí","No")},
    {"name": "dependencia", "label": "Dependencia / fuente de financiamiento", "type": "enumeration",
     "fieldType": "select", "options": opts(
        "Sector Educación","Particular","Convenio con Sector Educación",
        "Comunidad o asociación religiosa","Municipalidad","Otro sector público (FF.AA.)",
        "Asociación civil / Inst.Benéfica","Comunidad","Cooperativo","Empresa (Fiscalizado)","Otro")},
    {"name": "financiamiento_estatal", "label": "¿Recibe financiamiento estatal?", "type": "enumeration",
     "fieldType": "booleancheckbox", "options": opts("Sí","No")},
    {"name": "codigos_modulares", "label": "Códigos modulares", "type": "string", "fieldType": "text"},
    {"name": "ruc", "label": "RUC", "type": "string", "fieldType": "text"},
    {"name": "razon_social", "label": "Razón social", "type": "string", "fieldType": "text"},
    {"name": "promotor", "label": "Promotor / Titular", "type": "string", "fieldType": "text"},
    {"name": "director_ie", "label": "Director(a)", "type": "string", "fieldType": "text"},
    {"name": "email_ie", "label": "Email institucional", "type": "string", "fieldType": "text"},
    {"name": "dre_ugel", "label": "DRE / UGEL", "type": "string", "fieldType": "text"},
    {"name": "ubigeo", "label": "UBIGEO", "type": "string", "fieldType": "text"},
    {"name": "region_minedu", "label": "Región (DRE/GRE)", "type": "string", "fieldType": "text"},
    {"name": "pension_mensual", "label": "Pensión mensual (S/)", "type": "number", "fieldType": "number"},
    {"name": "cuota_matricula", "label": "Cuota de matrícula (S/)", "type": "number", "fieldType": "number"},
    {"name": "num_alumnos", "label": "Nº de alumnos", "type": "number", "fieldType": "number"},
    {"name": "num_docentes", "label": "Nº de docentes", "type": "number", "fieldType": "number"},
    {"name": "plan_sugerido", "label": "Plan SciBack sugerido", "type": "enumeration", "fieldType": "select",
     "options": opts("Esencial","Profesional","Enterprise","Sin clasificar")},
    {"name": "sciback_linea", "label": "Línea SciBack", "type": "enumeration", "fieldType": "select",
     "options": opts("Edu","Repositorios","Smart WiFi","Otro")},
    {"name": "fuente_datos", "label": "Fuente de datos", "type": "string", "fieldType": "text"},
    {"name": "fecha_padron", "label": "Fecha del padrón", "type": "date", "fieldType": "date"},
]

def ensure_group():
    r = requests.get(f"{BASE}/groups/{GROUP}", headers=H)
    if r.status_code == 200:
        print(f"  grupo '{GROUP}' ya existe"); return
    r = requests.post(f"{BASE}/groups", headers=H,
                      json={"name": GROUP, "label": "MINEDU / SciBack Edu", "displayOrder": 10})
    print(f"  grupo creado: {r.status_code}")
    if r.status_code >= 400: print("   ", r.text[:300])

def ensure_prop(p):
    r = requests.get(f"{BASE}/{p['name']}", headers=H)
    if r.status_code == 200:
        print(f"  = {p['name']} (existe)"); return
    body = dict(p); body["groupName"] = GROUP
    r = requests.post(BASE, headers=H, json=body)
    if r.status_code < 300:
        print(f"  + {p['name']} creada")
    else:
        print(f"  ! {p['name']} ERROR {r.status_code}: {r.text[:200]}")

if __name__ == "__main__":
    if not TOKEN:
        sys.exit("No token en ~/.secrets/hubspot.env")
    print("Creando grupo...")
    ensure_group()
    print("Creando propiedades...")
    for p in PROPS:
        ensure_prop(p)
    print("Listo.")
