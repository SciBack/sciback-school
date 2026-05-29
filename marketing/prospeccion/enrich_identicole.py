#!/usr/bin/env python3
"""
Enriquecimiento desde Identicole (scraping) para colegios PRIVADOS.
Por cada local privado prueba sus COD_MOD+ANEXO hasta encontrar ficha con datos
y extrae: Cuota de Ingreso, Matrícula, Pensión (más reciente), nº alumnos/docentes.

Identicole no tiene API; los datos están en el HTML SSR. Código = COD_MOD+ANEXO (8 díg).
Resume: salta los codigo_local ya presentes en el CSV de salida.

Salida: out/identicole_enrich.csv  (headers = propiedades HubSpot, listo para upsert)
Uso:    .venv/bin/python enrich_identicole.py
"""
import csv, os, re, time, sys
import urllib.request
from collections import defaultdict
from dbfread import DBF

BASE = os.path.dirname(os.path.abspath(__file__))
DBF_PATH = os.path.join(BASE, "data", "Padron_web.dbf")
OUT = os.path.join(BASE, "out", "identicole_enrich.csv")
DELAY = 1.5  # segundos entre requests (respetuoso con el servidor)
UA = {"User-Agent": "Mozilla/5.0 (compatible; SciBack-prospeccion/1.0)"}

def campo(html, label):
    """Valor que sigue a <strong class="strlabel">LABEL</strong> ... <strong>VALOR</strong>.
    Captura el primer número (con o sin 'S/')."""
    m = re.search(r'strlabel"?>\s*' + re.escape(label) +
                  r'\s*</strong>.*?<strong[^>]*>\s*(?:S/[.\s]*)?([\d.,]+)',
                  html, re.S | re.I)
    if not m: return ""
    return m.group(1).replace(",", "").rstrip(".")

def plan_por_alumnos(n):
    if not n: return "Sin clasificar"
    n = int(n)
    if n <= 300: return "Esencial"
    if n <= 800: return "Profesional"
    return "Enterprise"

def fetch(cod):
    try:
        req = urllib.request.Request(f"https://identicole.minedu.gob.pe/colegio/{cod}", headers=UA)
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception:
        return ""

def privados_por_local():
    db = DBF(DBF_PATH, encoding="cp850", load=False)
    loc = defaultdict(list)
    for r in db:
        if r.get("ESTADO") == "1" and r.get("GESTION") == "3":
            cl = (r.get("CODLOCAL") or "").strip()
            cm = (r.get("COD_MOD") or "").strip(); an = (r.get("ANEXO") or "0").strip()
            if cl and cm and not cm.startswith("0"):
                loc[cl].append(cm + an)
    return loc

COLS = ["codigo_local","pension_mensual","cuota_matricula","num_alumnos","num_docentes","plan_sugerido"]

def main():
    done = set()
    if os.path.exists(OUT):
        done = {r["codigo_local"] for r in csv.DictReader(open(OUT, encoding="utf-8"))}
    loc = privados_por_local()
    pend = [cl for cl in loc if cl not in done]
    print(f"Privados con código limpio: {len(loc):,} | ya hechos: {len(done):,} | pendientes: {len(pend):,}", flush=True)
    new = not os.path.exists(OUT)
    f = open(OUT, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=COLS)
    if new: w.writeheader()
    hits = 0
    for i, cl in enumerate(pend, 1):
        pension = matri = alum = doc = ""
        for cod in loc[cl][:3]:                      # probar hasta 3 servicios del local
            html = fetch(cod); time.sleep(DELAY)
            if len(html) < 60000: continue            # home/redirect = sin ficha
            pension = (campo(html, "Pensión 2026") or campo(html, "Pensión 2025")
                       or campo(html, "Pensión 2024") or pension)
            matri = matri or campo(html, "Matrícula") or campo(html, "Cuota de Ingreso")
            alum = alum or campo(html, "Total de estudiantes")
            doc = doc or campo(html, "Total de docentes") or campo(html, "Número de docentes")
            if pension: break
        if pension or matri or alum:
            hits += 1
            w.writerow({"codigo_local": cl, "pension_mensual": pension,
                        "cuota_matricula": matri, "num_alumnos": alum,
                        "num_docentes": doc, "plan_sugerido": plan_por_alumnos(alum)})
            f.flush()
        if i % 50 == 0:
            print(f"  {i}/{len(pend)} procesados | {hits} con datos", flush=True)
    f.close()
    print(f"FIN. {hits} locales enriquecidos -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
