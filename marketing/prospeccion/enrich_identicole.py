#!/usr/bin/env python3
"""
Enriquecimiento desde Identicole (scraping) para TODOS los colegios (EBR/EBA/EBE,
públicos y privados). Identicole tiene ficha por código modular con teléfono,
correo, director, nº alumnos/docentes y (en privados) pensión y matrícula.

Identicole no tiene API; datos en HTML SSR. Código = COD_MOD + ANEXO (8 díg,
SE INCLUYEN los que empiezan en 0). Resume: salta codigo_local ya en el CSV.

Salida: out/identicole_enrich.csv (headers = propiedades HubSpot, listo para upsert)
Uso:    .venv/bin/python enrich_identicole.py
"""
import csv, os, re, time, sys
import urllib.request
from collections import defaultdict
from dbfread import DBF

BASE = os.path.dirname(os.path.abspath(__file__))
DBF_PATH = os.path.join(BASE, "data", "Padron_web.dbf")
OUT = os.path.join(BASE, "out", "identicole_enrich.csv")
DELAY = 1.2
UA = {"User-Agent": "Mozilla/5.0 (compatible; SciBack-prospeccion/1.0)"}
# niveles escolares (colegios): Inicial/Primaria/Secundaria/EBA/EBE. Excluye L,T,K,S,P,M.
ESCOLAR = ("A", "B", "C", "D", "E", "F", "G")

def campo(html, label):
    """Texto que sigue a <strong class="strlabel">LABEL</strong> ... hasta cierre."""
    m = re.search(r'strlabel"?>\s*' + re.escape(label) + r'\s*</strong>(.*?)</div>\s*</div>',
                  html, re.S | re.I)
    if not m:
        return ""
    txt = re.sub(r'<[^>]+>', ' ', m.group(1))
    return re.sub(r'\s+', ' ', txt).strip()

def num(txt):
    m = re.search(r'[\d.,]+', txt or "")
    return m.group(0).replace(",", "").rstrip(".") if m else ""

def plan_por_alumnos(n):
    if not n: return "Sin clasificar"
    try: n = int(n)
    except ValueError: return "Sin clasificar"
    if n <= 300: return "Esencial"
    if n <= 800: return "Profesional"
    return "Enterprise"

def fetch(cod):
    try:
        req = urllib.request.Request(f"https://identicole.minedu.gob.pe/colegio/{cod}", headers=UA)
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception:
        return ""

def colegios_por_local():
    db = DBF(DBF_PATH, encoding="cp850", load=False)
    loc = defaultdict(list)
    for r in db:
        if r.get("ESTADO") != "1":
            continue
        niv = (r.get("NIV_MOD") or "")[:1]
        if niv not in ESCOLAR:        # solo colegios (no institutos/CETPRO/superior)
            continue
        cl = (r.get("CODLOCAL") or "").strip()
        cm = (r.get("COD_MOD") or "").strip()
        an = (r.get("ANEXO") or "0").strip()
        if cl and cm:
            loc[cl].append(cm + an)   # cod_mod+anexo (incluye cero inicial)
    return loc

COLS = ["codigo_local", "phone", "email_ie", "director_ie",
        "num_alumnos", "num_docentes", "pension_mensual", "cuota_matricula", "plan_sugerido"]

def main():
    done = set()
    if os.path.exists(OUT):
        done = {r["codigo_local"] for r in csv.DictReader(open(OUT, encoding="utf-8"))}
    loc = colegios_por_local()
    pend = [cl for cl in loc if cl not in done]
    print(f"Colegios (locales): {len(loc):,} | hechos: {len(done):,} | pendientes: {len(pend):,}", flush=True)
    new = not os.path.exists(OUT)
    f = open(OUT, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=COLS)
    if new: w.writeheader()
    hits = 0
    for i, cl in enumerate(pend, 1):
        rec = {c: "" for c in COLS}
        rec["codigo_local"] = cl
        for cod in loc[cl][:3]:
            html = fetch(cod); time.sleep(DELAY)
            if len(html) < 60000:        # home/redirect = sin ficha
                continue
            tel = campo(html, "Teléfono")
            email = campo(html, "Correo electrónico")
            director = campo(html, "Nombre del director")
            alum = num(campo(html, "Total de estudiantes"))
            doc = num(campo(html, "Total de docentes"))
            pen = num(campo(html, "Pensión 2026") or campo(html, "Pensión 2025") or campo(html, "Pensión 2024"))
            mat = num(campo(html, "Matrícula") or campo(html, "Cuota de Ingreso"))
            rec["phone"] = rec["phone"] or tel
            rec["email_ie"] = rec["email_ie"] or (email if "@" in email else "")
            rec["director_ie"] = rec["director_ie"] or director
            rec["num_alumnos"] = rec["num_alumnos"] or alum
            rec["num_docentes"] = rec["num_docentes"] or doc
            rec["pension_mensual"] = rec["pension_mensual"] or pen
            rec["cuota_matricula"] = rec["cuota_matricula"] or mat
            if tel or alum:              # ficha válida encontrada
                break
        rec["plan_sugerido"] = plan_por_alumnos(rec["num_alumnos"])
        if any(rec[c] for c in COLS[1:-1]):
            hits += 1
            w.writerow(rec); f.flush()
        if i % 50 == 0:
            print(f"  {i}/{len(pend)} | {hits} con datos", flush=True)
    f.close()
    print(f"FIN. {hits} colegios enriquecidos -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
