#!/usr/bin/env python3
"""
ETL del Padrón de Servicios Educativos (ESCALE/MINEDU) -> CSV maestro para HubSpot.

Fuente: https://escale.minedu.gob.pe/documents/10156/958881/Padron_web_<AAAAMMDD>.zip
        (contiene Padron_web.dbf, encoding cp850)

Regla de modelado: 1 LOCAL educativo (CODLOCAL) = 1 Company en HubSpot.
Un colegio que imparte Inicial+Primaria+Secundaria son 3 servicios (3 COD_MOD)
en el mismo local -> se consolidan en una sola company con sus niveles unidos.

Salida: out/colegios_master.csv  (todas las instituciones activas, etiquetadas)
Uso:    .venv/bin/python etl_padron.py [--incluir-inactivos]
"""
import csv, os, sys
from collections import defaultdict
from dbfread import DBF

BASE = os.path.dirname(os.path.abspath(__file__))
DBF_PATH = os.path.join(BASE, "data", "Padron_web.dbf")
OUT_DIR = os.path.join(BASE, "out")
os.makedirs(OUT_DIR, exist_ok=True)
INCLUIR_INACTIVOS = "--incluir-inactivos" in sys.argv

# --- Taxonomía: código NIV_MOD -> (etapa, tipo_macro, nivel_legible) ---
NIVELES = {
    'A1': ('EBR', 'COLEGIO', 'Inicial - Cuna'),
    'A2': ('EBR', 'COLEGIO', 'Inicial - Jardín'),
    'A3': ('EBR', 'COLEGIO', 'Inicial - Cuna-jardín'),
    'A5': ('EBR', 'COLEGIO', 'Inicial - PRONOEI'),
    'B0': ('EBR', 'COLEGIO', 'Primaria'),
    'F0': ('EBR', 'COLEGIO', 'Secundaria'),
    'C0': ('EBA', 'COLEGIO', 'Primaria de Adultos'),
    'G0': ('EBA', 'COLEGIO', 'Secundaria de Adultos'),
    'D0': ('EBA', 'COLEGIO', 'Básica Alternativa'),
    'D1': ('EBA', 'COLEGIO', 'Básica Alternativa - Inicial/Intermedio'),
    'D2': ('EBA', 'COLEGIO', 'Básica Alternativa - Avanzado'),
    'E0': ('EBE', 'COLEGIO', 'Básica Especial'),
    'E1': ('EBE', 'COLEGIO', 'Básica Especial - Inicial'),
    'E2': ('EBE', 'COLEGIO', 'Básica Especial - Primaria'),
    'T0': ('SUPERIOR', 'INSTITUTO', 'Instituto Superior Tecnológico'),
    'K0': ('SUPERIOR', 'INSTITUTO', 'Instituto Superior Pedagógico'),
    'S0': ('SUPERIOR', 'ESCUELA_SUPERIOR', 'Escuela Superior Tecnológica'),
    'P0': ('SUPERIOR', 'ESCUELA_SUPERIOR', 'Escuela Superior Pedagógica'),
    'M0': ('SUPERIOR', 'ESCUELA_SUPERIOR', 'Escuela de Formación Artística'),
}
def clasifica(niv):
    if not niv: return ('OTRO', 'OTRO', 'Desconocido')
    if niv.startswith('L'): return ('TECNICO_PRODUCTIVA', 'CETPRO', 'Técnico-Productiva / Ocupacional')
    return NIVELES.get(niv, ('OTRO', 'OTRO', niv))

# orden de "representatividad" del nombre (gana el nivel más alto)
RANK = {'F0':9,'B0':8,'A2':7,'A3':6,'A5':5,'A1':4,'T0':9,'K0':9,'S0':9,'P0':9,'M0':8}

def first(*vals):
    for v in vals:
        v = (v or '').strip()
        if v: return v
    return ''

def main():
    db = DBF(DBF_PATH, encoding="cp850", load=False)
    locales = {}
    for r in db:
        estado_act = r.get('ESTADO') == '1'
        if not INCLUIR_INACTIVOS and not estado_act:
            continue
        cl = (r.get('CODLOCAL') or '').strip() or f"SL{(r.get('COD_MOD') or '').strip()}"
        etapa, macro, nivel = clasifica((r.get('NIV_MOD') or '').strip())
        d = locales.get(cl)
        if d is None:
            d = locales[cl] = {
                'codigo_local': cl, 'niveles': {}, 'etapas': set(), 'macros': {},
                'cod_mods': [], 'nombre': '', 'nombre_rank': -1,
                'director': '', 'telefono': '', 'email': '', 'pagweb': '',
                'direccion': '', 'localidad': '', 'centro_poblado': '',
                'departamento': '', 'provincia': '', 'distrito': '', 'ubigeo': '',
                'region': '', 'dre_ugel': '', 'lat': '', 'lon': '',
                'gestion': '', 'ruc': '', 'razon_social': '', 'promotor': '',
                'cod_inst': '', 'n_serv': 0, 'activo': False, 'dependencia': '',
            }
        d['n_serv'] += 1
        d['activo'] = d['activo'] or estado_act
        d['niveles'][nivel] = True
        d['etapas'].add(etapa)
        d['macros'][macro] = d['macros'].get(macro, 0) + 1
        cm = (r.get('COD_MOD') or '').strip()
        if cm: d['cod_mods'].append(cm)
        rank = RANK.get((r.get('NIV_MOD') or '').strip(), 0)
        nombre = first(r.get('CEN_EDU'))
        if nombre and rank > d['nombre_rank']:
            d['nombre'] = nombre; d['nombre_rank'] = rank
        # contacto / ubicación: primer valor no vacío
        d['director']  = first(d['director'], r.get('DIRECTOR'))
        d['telefono']  = first(d['telefono'], r.get('TELEFONO'))
        d['email']     = first(d['email'], r.get('EMAIL'))
        d['pagweb']    = first(d['pagweb'], r.get('PAGWEB'))
        d['direccion'] = first(d['direccion'], r.get('DIR_CEN'))
        d['localidad'] = first(d['localidad'], r.get('LOCALIDAD'))
        d['centro_poblado'] = first(d['centro_poblado'], r.get('CEN_POB'))
        d['departamento'] = first(d['departamento'], r.get('D_DPTO'))
        d['provincia'] = first(d['provincia'], r.get('D_PROV'))
        d['distrito']  = first(d['distrito'], r.get('D_DIST'))
        d['ubigeo']    = first(d['ubigeo'], r.get('CODGEO'))
        d['region']    = first(d['region'], r.get('D_REGION'))
        d['dre_ugel']  = first(d['dre_ugel'], r.get('D_DREUGEL'))
        d['lat']       = first(d['lat'], str(r.get('NLAT_IE') or ''))
        d['lon']       = first(d['lon'], str(r.get('NLONG_IE') or ''))
        d['gestion']   = first(d['gestion'], r.get('D_GESTION'))
        d['dependencia'] = first(d['dependencia'], r.get('D_GES_DEP'))
        d['ruc']       = first(d['ruc'], r.get('NRORUC'))
        d['razon_social'] = first(d['razon_social'], r.get('RZSOCIAL'))
        d['promotor']  = first(d['promotor'], r.get('PROMOTOR'))
        d['cod_inst']  = first(d['cod_inst'], r.get('CODINST'))

    # tipo_macro dominante por local
    def macro_dominante(macros):
        pref = ['INSTITUTO','ESCUELA_SUPERIOR','COLEGIO','CETPRO','OTRO']
        for p in pref:
            if p in macros: return p
        return max(macros, key=macros.get)

    def gestion_norm(g):
        g = (g or '').lower()
        if 'privada' in g and 'gesti' not in g.split('privada')[0]:
            return 'Privada' if g.strip()=='privada' else 'Privada'
        if g.startswith('privada'): return 'Privada'
        if 'gestión privada' in g or 'gestion privada' in g: return 'Pública de gestión privada'
        if 'directa' in g: return 'Pública de gestión directa'
        return g.title()

    ESTATAL = {'Sector Educación', 'Municipalidad', 'Otro sector público (FF.AA.)',
               'Convenio con Sector Educación'}

    cols = ['codigo_local','nombre','tipo_institucion','etapa','niveles','gestion',
            'es_privado','dependencia','financiamiento_estatal','ruc','razon_social',
            'promotor','director','telefono','email','pagweb','direccion','localidad',
            'centro_poblado','distrito','provincia','departamento','ubigeo','region',
            'dre_ugel','lat','lon','codigos_modulares','num_servicios','fuente','fecha_padron']
    path = os.path.join(OUT_DIR, "colegios_master.csv")
    n=0; n_priv=0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for d in locales.values():
            ges = gestion_norm(d['gestion'])
            es_priv = 'Sí' if ges == 'Privada' else 'No'
            if es_priv == 'Sí': n_priv += 1
            macro = macro_dominante(d['macros'])
            etapa = 'EBR' if 'EBR' in d['etapas'] else (
                    'SUPERIOR' if 'SUPERIOR' in d['etapas'] else
                    next(iter(d['etapas']), 'OTRO'))
            w.writerow({
                'codigo_local': d['codigo_local'], 'nombre': d['nombre'],
                'tipo_institucion': macro, 'etapa': etapa,
                'niveles': ';'.join(sorted(d['niveles'])), 'gestion': ges,
                'es_privado': es_priv, 'dependencia': d['dependencia'],
                'financiamiento_estatal': 'Sí' if d['dependencia'] in ESTATAL else 'No',
                'ruc': d['ruc'], 'razon_social': d['razon_social'],
                'promotor': d['promotor'], 'director': d['director'],
                'telefono': d['telefono'], 'email': d['email'], 'pagweb': d['pagweb'],
                'direccion': d['direccion'], 'localidad': d['localidad'],
                'centro_poblado': d['centro_poblado'], 'distrito': d['distrito'],
                'provincia': d['provincia'], 'departamento': d['departamento'],
                'ubigeo': d['ubigeo'], 'region': d['region'], 'dre_ugel': d['dre_ugel'],
                'lat': d['lat'], 'lon': d['lon'],
                'codigos_modulares': ';'.join(d['cod_mods']),
                'num_servicios': d['n_serv'], 'fuente': 'ESCALE/MINEDU Padron_web',
                'fecha_padron': '2026-05-20',
            })
            n+=1
    print(f"OK -> {path}")
    print(f"  companies (locales): {n:,}  | privados: {n_priv:,}")

if __name__ == "__main__":
    main()
