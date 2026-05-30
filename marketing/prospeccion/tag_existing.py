#!/usr/bin/env python3
"""
Etiqueta las companies preexistentes (sin sciback_linea) para que sean filtrables
junto al resto: universidades del negocio repositorios + otros.
Idempotente: solo toca companies que aún no tienen sciback_linea.
"""
import os, json, requests

def load_token():
    vals = {}
    for line in open(os.path.expanduser("~/.secrets/hubspot.env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1); vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals.get("HUBSPOT_TOKEN") or vals.get("HUBSPOT_API_KEY")

TOK = load_token()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

def fetch_untagged():
    out, after = [], None
    while True:
        body = {"filterGroups": [{"filters": [{"propertyName": "sciback_linea",
                "operator": "NOT_HAS_PROPERTY"}]}], "limit": 100,
                "properties": ["name", "domain", "industry", "description"]}
        if after: body["after"] = after
        r = requests.post("https://api.hubapi.com/crm/v3/objects/companies/search", headers=H, json=body).json()
        out += r.get("results", [])
        after = r.get("paging", {}).get("next", {}).get("after")
        if not after: break
    return out

def clasifica(p):
    name = (p.get("name") or "").lower()
    ind = p.get("industry") or ""
    es_uni = "universidad" in name or "escuela de posgrado" in name or ind == "HIGHER_EDUCATION"
    if es_uni:
        # nacional/estatal -> pública; resto -> privada
        publica = any(w in name for w in ["nacional", "estatal", " de la amazon", "autónoma"]) and "particular" not in name
        return {"tipo_institucion": "UNIVERSIDAD", "etapa": "SUPERIOR",
                "sciback_linea": "Repositorios",
                "gestion": "Pública de gestión directa" if publica else "Privada",
                "es_privado": "No" if publica else "Sí"}
    # no es institución educativa (apps, herramientas, etc.)
    return {"tipo_institucion": "OTRO", "sciback_linea": "Otro"}

def main():
    comps = fetch_untagged()
    print(f"companies sin etiquetar: {len(comps)}")
    inputs = []
    uni = otro = 0
    for c in comps:
        props = clasifica(c.get("properties", {}))
        if props["tipo_institucion"] == "UNIVERSIDAD": uni += 1
        else: otro += 1
        inputs.append({"id": c["id"], "properties": props})
    print(f"  -> universidades: {uni} | otros: {otro}")
    for i in range(0, len(inputs), 100):
        batch = inputs[i:i+100]
        r = requests.post("https://api.hubapi.com/crm/v3/objects/companies/batch/update",
                          headers=H, json={"inputs": batch})
        print(f"  batch {i//100+1}: HTTP {r.status_code}" + ("" if r.status_code < 300 else f" {r.text[:200]}"))

if __name__ == "__main__":
    main()
