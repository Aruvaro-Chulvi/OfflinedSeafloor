"""Empareja cada relieve del nomenclátor GEBCO con Wikidata: etiqueta inglesa exacta «NAME TYPE»
(o alias) + coordenadas cercanas. Después baja etiquetas y artículos de Wikipedia en 10 idiomas.
Salida: wd.json  {FEATURE_ID: {"q": "Q510", "l": {lang: etiqueta}, "w": {lang: título}}}"""
import json, math, os, time
from pathlib import Path
import requests
from shapely.geometry import shape, Point

WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
HERE = WORK
LANGS = ["en", "es", "fr", "it", "de", "pt", "zh", "hi", "ar", "ru"]
EP = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "OfflinedBuild/1.0 (seafloor gazetteer; alvarocuadradochulvi@gmail.com)",
      "Accept": "application/sparql-results+json"}


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


def load():
    feats = {}
    for n in ("lines", "polygons", "points"):       # preferencia de geometría
        for f in json.load(open(HERE / f"{n}.geojson", encoding="utf-8"))["features"]:
            p = f["properties"]
            fid = p["FEATURE_ID"]
            if fid in feats or not f.get("geometry"):
                continue
            g = shape(f["geometry"])
            c = g.representative_point() if n != "lines" else g.interpolate(0.5, normalized=True)
            minx, miny, maxx, maxy = g.bounds
            feats[fid] = {"name": p["NAME"], "type": p["TYPE"], "lon": c.x, "lat": c.y,
                          "ext": max(maxx - minx, maxy - miny), "g": g}
    return feats


def dist(a_lon, a_lat, b_lon, b_lat):
    dl = abs(a_lon - b_lon); dl = min(dl, 360 - dl)
    return math.hypot(dl * math.cos(math.radians((a_lat + b_lat) / 2)), a_lat - b_lat)


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    feats = load()
    print(len(feats), "features")
    by_label = {}
    for fid, f in feats.items():
        for lab in {f"{f['name']} {f['type']}", f"{f['name']} {f['type']}".replace("Seachannel", "Sea Channel")}:
            by_label.setdefault(lab, []).append(fid)
    labels = list(by_label)
    cache = HERE / "wd_cand.json"
    cand = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for i in (range(0, len(labels), 150) if not cand else []):
        chunk = labels[i:i + 150]
        vals = " ".join(f'"{esc(l)}"@en' for l in chunk)
        q = f"""SELECT ?i ?l ?c WHERE {{ VALUES ?l {{ {vals} }}
          {{ ?i rdfs:label ?l }} UNION {{ ?i skos:altLabel ?l }}
          ?i wdt:P625 ?c . }}"""
        for b in sparql(q):
            m = b["c"]["value"]
            if not m.startswith("Point("):
                continue
            lon, lat = map(float, m[6:-1].split())
            cand.setdefault(b["l"]["value"], []).append((b["i"]["value"].rsplit("/", 1)[1], lon, lat))
        print("labels", i + len(chunk), "/", len(labels), "cand", len(cand), flush=True)
        time.sleep(1)
    if not cache.exists():
        cache.write_text(json.dumps(cand), encoding="utf-8")
    match = {}
    for lab, fids in by_label.items():
        for fid in fids:
            f = feats[fid]
            thr = 2.5 if f["ext"] > 1 else 1.5
            best = None
            for q, lon, lat in cand.get(lab, []):
                d = min(f["g"].distance(Point(lon, lat)), f["g"].distance(Point(lon - 360, lat)), f["g"].distance(Point(lon + 360, lat)))
                if d <= thr and (best is None or d < best[1]):
                    best = (q, d)
            if best:
                match[fid] = best[0]
    # Un mismo Q para dos relieves distintos: nos quedamos sin ninguno de los dos (ambiguo)
    from collections import Counter
    cnt = Counter(match.values())
    match = {k: v for k, v in match.items() if cnt[v] == 1}
    print("matched", len(match))
    qs = sorted(set(match.values()))
    info = {}
    for i in range(0, len(qs), 200):
        chunk = qs[i:i + 200]
        vals = " ".join(f"wd:{q}" for q in chunk)
        langs = ", ".join(f'"{l}"' for l in LANGS)
        q = f"""SELECT ?i ?lab ?art ?wl WHERE {{ VALUES ?i {{ {vals} }}
          {{ ?i rdfs:label ?lab FILTER(LANG(?lab) IN ({langs})) }}
          UNION
          {{ ?art schema:about ?i ; schema:isPartOf ?site ; schema:inLanguage ?wl .
             FILTER(STRENDS(STR(?site), ".wikipedia.org/")) FILTER(?wl IN ({langs})) }} }}"""
        for b in sparql(q):
            qid = b["i"]["value"].rsplit("/", 1)[1]
            d = info.setdefault(qid, {"l": {}, "w": {}})
            if "lab" in b:
                d["l"][b["lab"]["xml:lang"]] = b["lab"]["value"]
            if "art" in b:
                t = requests.utils.unquote(b["art"]["value"].rsplit("/wiki/", 1)[1]).replace("_", " ")
                d["w"][b["wl"]["value"]] = t
        print("info", i + len(chunk), "/", len(qs), flush=True)
        time.sleep(1)
    out = {str(fid): {"q": q, **info.get(q, {"l": {}, "w": {}})} for fid, q in match.items()}
    (HERE / "wd.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print("wiki in some lang:", sum(1 for v in out.values() if v["w"]), "es:", sum(1 for v in out.values() if "es" in v["w"]))


if __name__ == "__main__":
    main()
