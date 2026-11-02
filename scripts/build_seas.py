"""Mares y océanos para la ficha de «Explorar» → frontend/geo/sea_areas.json

Fuentes (CC BY 4.0, Flanders Marine Institute, www.marineregions.org):
  IHO Sea Areas v3 (https://doi.org/10.14284/323)          — 101 mares, golfos, estrechos
  Global Oceans and Seas v1 (https://doi.org/10.14284/542) — 10 océanos / regiones
Descarga (WFS):
  https://geo.vliz.be/geoserver/MarineRegions/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=MarineRegions:iho&outputFormat=application/json
  (igual con typeName=MarineRegions:goas) → iho.json y goas.json en SEAS_WORK
Nombres y artículos: Wikidata (CC0) por la propiedad P3006 (Marine Regions Geographic ID)
del mrgid de cada zona IHO; los océanos de GOaS van a mano al artículo del océano entero.

Formato:
  {"v": 1, "seas": [[mrgid, nombre_en, q|null, [w, s, e, n], [polígono, …]], …],
   "oceans": [[nombre_en, q, [w, s, e, n], [polígono, …]], …],
   "wd": {q: {"l": {lang: nombre}, "w": {lang: artículo}}}}
  polígono = [anillo exterior, huecos…], anillo = [lon, lat, lon, lat, …] (plano, 2 decimales)
"""
import json, os, time
from pathlib import Path
import requests
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.validation import make_valid

WORK = Path(os.environ.get("SEAS_WORK") or (Path(__file__).parent / "work"))
OUT = Path(__file__).resolve().parents[1] / "data" / "sea_areas.json"   # copiar a Offlined: frontend/geo/
LANGS = ["en", "es", "fr", "it", "de", "pt", "zh", "hi", "ar", "ru"]
EP = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "OfflinedBuild/1.0 (sea areas; alvarocuadradochulvi@gmail.com)",
      "Accept": "application/sparql-results+json"}
TOL = 0.04          # ~4 km: sirve para saber en qué mar se pincha (el borde lo tapa la tierra del mapa)

# GOaS → el océano (o mar) entero en Wikidata
OCEAN_Q = {
    "North Atlantic Ocean": "Q97", "South Atlantic Ocean": "Q97",
    "North Pacific Ocean": "Q98", "South Pacific Ocean": "Q98",
    "South China and Easter Archipelagic Seas": "Q98",
    "Indian Ocean": "Q1239", "Arctic Ocean": "Q788", "Southern Ocean": "Q7354",
    "Mediterranean Region": "Q4918", "Baltic Sea": "Q545",
}


def sparql(q):
    for i in range(5):
        try:
            r = requests.post(EP, data={"query": q}, headers=UA, timeout=180)
            if r.status_code == 429:
                time.sleep(30); continue
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:
            print("retry", i, e); time.sleep(10)
    raise RuntimeError("sparql")


def pack(geom):
    # Primero simplificar (rápido) y después arreglar: al revés, con costas de millones de vértices, tarda horas
    g = geom.simplify(TOL, preserve_topology=False)
    if not g.is_valid:
        g = make_valid(g)
    polys = [p for p in (g.geoms if hasattr(g, "geoms") else [g]) if isinstance(p, Polygon) and p.area > 0.002]
    out = []
    for p in polys:
        rings = [p.exterior] + [r for r in p.interiors if Polygon(r).area > 0.01]
        out.append([[v for xy in r.coords for v in (round(xy[0], 2), round(xy[1], 2))] for r in rings])
    w, s, e, n = MultiPolygon(polys).bounds
    return [round(w, 2), round(s, 2), round(e, 2), round(n, 2)], out


def main():
    iho = json.load(open(WORK / "iho.json", encoding="utf-8"))["features"]
    goas = json.load(open(WORK / "goas.json", encoding="utf-8"))["features"]
    mr = [str(f["properties"]["mrgid"]) for f in iho]
    vals = " ".join(f'"{m}"' for m in mr)
    by_mr = {}
    for b in sparql(f"SELECT ?i ?m WHERE {{ VALUES ?m {{ {vals} }} ?i wdt:P3006 ?m . }}"):
        by_mr.setdefault(b["m"]["value"], set()).add(b["i"]["value"].rsplit("/", 1)[1])
    # Un mrgid con varios ítems: no se sabe cuál es → sin artículo
    q_of = {m: next(iter(qs)) for m, qs in by_mr.items() if len(qs) == 1}
    qs = sorted(set(q_of.values()) | set(OCEAN_Q.values()))
    langs = ", ".join(f'"{l}"' for l in LANGS)
    wd = {q: {"l": {}, "w": {}} for q in qs}
    res = sparql(f"""SELECT ?i ?lab ?art ?wl WHERE {{ VALUES ?i {{ {" ".join("wd:" + q for q in qs)} }}
      {{ ?i rdfs:label ?lab FILTER(LANG(?lab) IN ({langs})) }}
      UNION
      {{ ?art schema:about ?i ; schema:isPartOf ?site ; schema:inLanguage ?wl .
         FILTER(STRENDS(STR(?site), ".wikipedia.org/")) FILTER(?wl IN ({langs})) }} }}""")
    for b in res:
        d = wd[b["i"]["value"].rsplit("/", 1)[1]]
        if "lab" in b:
            d["l"][b["lab"]["xml:lang"]] = b["lab"]["value"]
        if "art" in b:
            d["w"][b["wl"]["value"]] = requests.utils.unquote(b["art"]["value"].rsplit("/wiki/", 1)[1]).replace("_", " ")
    seas = []
    for f in iho:
        p = f["properties"]
        bbox, polys = pack(shape(f["geometry"]))
        seas.append([p["mrgid"], p["name"], q_of.get(str(p["mrgid"])), bbox, polys])
    oceans = []
    for f in goas:
        p = f["properties"]
        bbox, polys = pack(shape(f["geometry"]))
        oceans.append([p["name"], OCEAN_Q[p["name"]], bbox, polys])
    # Etiquetas con mayúscula inicial (Wikidata las tiene a veces en minúscula)
    for d in wd.values():
        d["l"] = {k: v[:1].upper() + v[1:] for k, v in d["l"].items() if v}
    out = {"v": 1, "src": "Flanders Marine Institute: IHO Sea Areas v3, Global Oceans and Seas v1 (CC BY 4.0, marineregions.org); names/articles: Wikidata (CC0)",
           "seas": seas, "oceans": oceans, "wd": wd}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(OUT.stat().st_size // 1024, "KB;", sum(1 for s in seas if s[2]), "of", len(seas), "seas with Wikidata")
    for s in seas:
        if not s[2]:
            print("  no Q:", s[1])
    from collections import Counter
    print(Counter(l for s in seas if s[2] for l in wd[s[2]]["w"]))


if __name__ == "__main__":
    main()
