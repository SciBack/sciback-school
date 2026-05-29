#!/usr/bin/env python3
"""
Transforma out/colegios_master.csv -> out/hubspot_companies.csv
con los headers nombrados igual que las propiedades de HubSpot (mapeo 1:1).
"""
import csv, os
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "out", "colegios_master.csv")
DST = os.path.join(BASE, "out", "hubspot_companies.csv")

def industry(tipo):
    if tipo == "COLEGIO": return "PRIMARY_SECONDARY_EDUCATION"
    if tipo in ("INSTITUTO", "ESCUELA_SUPERIOR", "UNIVERSIDAD"): return "HIGHER_EDUCATION"
    return "EDUCATION_MANAGEMENT"

OUT_COLS = ["codigo_local","name","tipo_institucion","etapa","niveles_educativos",
    "gestion","es_privado","ruc","razon_social","promotor","director_ie","phone",
    "email_ie","website","address","city","state","ubigeo","region_minedu","dre_ugel",
    "industry","codigos_modulares","sciback_linea","fuente_datos","fecha_padron","country"]

n = 0
with open(SRC, encoding="utf-8") as f, open(DST, "w", newline="", encoding="utf-8") as g:
    r = csv.DictReader(f)
    w = csv.DictWriter(g, fieldnames=OUT_COLS); w.writeheader()
    for row in r:
        nombre = (row["nombre"] or "").strip()
        # nombres numéricos (jardines/colegios por número) -> legibles
        if not nombre:
            nombre = f"I.E. {row['codigo_local']}"
        elif nombre.replace(" ", "").isdigit():
            nombre = f"I.E. N° {nombre}" + (f" - {row['distrito']}" if row["distrito"] else "")
        w.writerow({
            "codigo_local": row["codigo_local"],
            "name": nombre,
            "tipo_institucion": row["tipo_institucion"],
            "etapa": row["etapa"],
            "niveles_educativos": row["niveles"],
            "gestion": row["gestion"],
            "es_privado": row["es_privado"],
            "ruc": row["ruc"], "razon_social": row["razon_social"],
            "promotor": row["promotor"], "director_ie": row["director"],
            "phone": row["telefono"], "email_ie": row["email"],
            "website": row["pagweb"], "address": row["direccion"],
            "city": row["distrito"], "state": row["departamento"],
            "ubigeo": row["ubigeo"], "region_minedu": row["region"],
            "dre_ugel": row["dre_ugel"], "industry": industry(row["tipo_institucion"]),
            "codigos_modulares": row["codigos_modulares"], "sciback_linea": "Edu",
            "fuente_datos": row["fuente"], "fecha_padron": row["fecha_padron"],
            "country": "Perú",
        })
        n += 1
print(f"OK -> {DST}  ({n:,} filas)")
