"""Nomenclátor GEBCO + Wikidata + profundidades (z7.i16) → frontend/geo/seafloor_features.json

Formato compacto:
  {"v": 1, "types": [tipo inglés, …],
   "f": [[id, NAME, ti, lon, lat, prof_m, rango, geom|null, q|null], …],
   "wd": {id: {"l": {lang: nombre}, "w": {lang: artículo}}}}
  geom: [[lon, lat], …] (línea) o {"p": [[[lon, lat], …]]} (polígono, solo anillo exterior)
"""
import json, math, os, sys
from pathlib import Path
import numpy as np
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon, MultiLineString
from shapely import contains_xy

WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
HERE = WORK
Z7 = WORK / "z7.i16"
OUT = Path(__file__).resolve().parents[1] / "data" / "seafloor_features.json"   # copiar a Offlined: frontend/geo/
N = 512 << 7

UP = {"Seamount", "Seamounts", "Guyot", "Guyots", "Tablemount", "Knoll", "Knolls", "Hill", "Hills", "Bank", "Banks",
      "Shoal", "Shoals", "Reef", "Reefs", "Peak", "Mound", "Mounds", "Pingos", "Cone", "Mud Volcano", "Ridge", "Ridges",
      "Rise", "Spur", "Plateau", "Seamount Chain", "Seamount Group", "Seamount Province", "Cap", "Promontory", "Bars",
      "Hill Province", "Sand Ridge Province", "Salt Dome Province", "Finger", "Lobe", "Borderland", "Terrace", "Shelf"}

mm = np.memmap(Z7, dtype=np.int16, mode="r", shape=(N, N))


def px(lon, lat):
    lat = np.clip(lat, -85.05, 85.05)
    x = ((np.asarray(lon) + 180.0) / 360.0 * N).astype(np.int64) % N
    s = np.sin(np.radians(lat))
    y = ((0.5 - np.log((1 + s) / (1 - s)) / (4 * math.pi)) * N).astype(np.int64)
    return x, np.clip(y, 0, N - 1)


def sample(lons, lats):
    x, y = px(np.asarray(lons, float), np.asarray(lats, float))
    order = np.argsort(y)                      # leer el memmap por filas
    v = np.empty(len(x), np.int32)
    v[order] = mm[y[order], x[order]]
    return v


def geom_samples(g):
    if isinstance(g, Point):
        return np.array([g.x]), np.array([g.y])
    if isinstance(g, (LineString, MultiLineString)):
        L = g.length
        k = max(2, min(4000, int(L / 0.01)))
        pts = [g.interpolate(i / (k - 1), normalized=True) for i in range(k)]
        return np.array([p.x for p in pts]), np.array([p.y for p in pts])
    minx, miny, maxx, maxy = g.bounds
    step = max(0.004, math.sqrt(max((maxx - minx) * (maxy - miny), 1e-8) / 60000))
    xs, ys = np.meshgrid(np.arange(minx, maxx + step, step), np.arange(miny, maxy + step, step))
    xs, ys = xs.ravel(), ys.ravel()
    m = contains_xy(g, xs, ys)
    if not m.any():
        c = g.representative_point()
        return np.array([c.x]), np.array([c.y])
    return xs[m], ys[m]


def rnd(c):
    return [round(c[0], 3), round(c[1], 3)]


def pack_geom(g):
    if isinstance(g, (LineString, MultiLineString)):
        g = g.simplify(0.01)
        parts = list(g.geoms) if isinstance(g, MultiLineString) else [g]
        part = max(parts, key=lambda p: p.length)
        return [rnd(c) for c in part.coords]
    if isinstance(g, (Polygon, MultiPolygon)):
        g = g.simplify(0.005)
        polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
        return {"p": [[rnd(c) for c in p.exterior.coords] for p in polys if not p.is_empty]}
    return None


def main():
    wd = json.loads((HERE / "wd.json").read_text(encoding="utf-8"))
    feats = {}
    for n in ("lines", "polygons", "points"):
        for f in json.load(open(HERE / f"{n}.geojson", encoding="utf-8"))["features"]:
            p = f["properties"]
            fid = p["FEATURE_ID"]
            if fid in feats or not f.get("geometry") or not (p.get("NAME") or "").strip():
                continue
            g = shape(f["geometry"])
            if g.geom_type == "MultiPoint":
                g = g.geoms[0]
            feats[fid] = (p["NAME"].strip(), (p["TYPE"] or "UNKNOWN").strip(), g)
    types, rows, wdout = [], [], {}
    for fid, (name, typ, g) in sorted(feats.items(), key=lambda kv: kv[1][0]):
        if typ not in types:
            types.append(typ)
        lab = g if isinstance(g, Point) else (g.interpolate(0.5, normalized=True) if isinstance(g, (LineString, MultiLineString)) else g.representative_point())
        # Depresiones lineales (fosas, cañones…): la línea es su eje aproximado, se mira una franja
        sg = g.buffer(0.12) if (typ not in UP and isinstance(g, (LineString, MultiLineString))) else g
        xs, ys = geom_samples(sg)
        v = sample(xs, ys)
        depth = int(v.max() if typ in UP else v.min())
        minx, miny, maxx, maxy = g.bounds
        ext = max(maxx - minx, maxy - miny)
        w = wd.get(str(fid))
        has_wiki = bool(w and w.get("w"))
        rank = 0 if (ext > 8 or (has_wiki and ext > 3)) else 1 if (ext > 3 or has_wiki) else 2 if ext > 0.5 else 3
        geom = None if isinstance(g, Point) else pack_geom(g)
        rows.append([fid, name, types.index(typ), round(lab.x, 4), round(lab.y, 4), depth, rank, geom, w["q"] if w else None])
        if w and (w.get("l") or w.get("w")):
            l = {k: (v[:1].upper() + v[1:]) for k, v in (w.get("l") or {}).items() if v}
            wdout[str(fid)] = {"l": l, "w": w.get("w") or {}}
    out = {"v": 1, "src": "IHO-IOC GEBCO Gazetteer of Undersea Feature Names, www.gebco.net; depths: GEBCO 2026 Grid; names/articles: Wikidata (CC0)",
           "types": types, "f": rows, "wd": wdout}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(rows), "features", len(types), "types", OUT.stat().st_size // 1024, "KB")
    print(types)


if __name__ == "__main__":
    main()
