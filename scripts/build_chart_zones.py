"""Zona de cada país para descargar sus cartas náuticas → frontend/geo/chart_zones.json

Fuente (CC BY 4.0, Flanders Marine Institute, www.marineregions.org):
  Marine Regions «eez_land»: unión de cada país y su zona económica exclusiva
  (tierra + mar hasta 200 millas). Así entran los faros de la costa, los
  puertos, ríos y lagos navegables y las boyas de alta mar.
Descarga (WFS):
  https://geo.vliz.be/geoserver/MarineRegions/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=MarineRegions:eez_land&outputFormat=application/json&propertyName=the_geom,iso_ter1,iso_sov1,territory1,pol_type
  → eez_land.json en ZONES_WORK
Los países de frontend/learn/geo/data/countries.json (los mismos del selector de
Mapas) se cruzan por su ISO 3166-1 alfa-3. Si un país no está en «eez_land»,
se usa su silueta con 0,1° de margen (igual que Mapas).

Formato (polígonos para el filtro «poly:» de Overpass, sin huecos):
  {"v": 1, "src": "…", "zones": {"ES": {"bbox": [w, s, e, n], "sea": true|false,
                                         "p": [[lon, lat, lon, lat, …], …]}, …}}
"""
import json, os, sys
from pathlib import Path
from shapely.geometry import shape, Polygon, MultiPolygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid

WORK = Path(os.environ.get("ZONES_WORK") or (Path(__file__).parent / "work"))
OFFLINED = Path(os.environ.get("OFFLINED_ROOT") or r"C:\SurvivalAI-phi4")
COUNTRIES = OFFLINED / "frontend" / "learn" / "geo" / "data" / "countries.json"
OUT = OFFLINED / "frontend" / "geo" / "chart_zones.json"
TOL = 0.05          # ~5 km: el borde de la zona no necesita más (las señales están lejos de él)
MIN_AREA = 0.002    # se descartan islotes sueltos de la simplificación
MAX_PTS = 600       # puntos por polígono como mucho (la consulta a Overpass no debe crecer sin límite)


def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def pack(geom):
    out = []
    for p in parts(geom):
        g = p.simplify(TOL, preserve_topology=False)
        if not g.is_valid:
            g = make_valid(g)
        for q in parts(g):
            if q.area < MIN_AREA:
                continue
            ext = Polygon(q.exterior)
            t = TOL
            while len(ext.exterior.coords) > MAX_PTS:
                t *= 1.6
                ext = Polygon(ext.exterior).simplify(t, preserve_topology=True)
            ring = list(ext.exterior.coords)[:-1]
            out.append([round(v, 3) for xy in ring for v in xy])
    return out


def main():
    src = json.loads((WORK / "eez_land.json").read_text(encoding="utf-8"))
    by_a3 = {}
    for f in src["features"]:
        # Las partes del propio país (Canarias, Alaska, Hawái…) vienen sin territorio:
        # van con su país soberano. Los territorios con código propio, aparte.
        pr = f["properties"]
        a3 = (pr.get("iso_ter1") or pr.get("iso_sov1") or "").upper()
        if not a3 or not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        if not g.is_valid:
            g = make_valid(g)
        by_a3.setdefault(a3, []).append(g)
    data = json.loads(COUNTRIES.read_text(encoding="utf-8"))
    sil = {f.get("id"): f.get("geometry") for f in data["geo"]["features"]}
    world = box(-180, -85.0511, 180, 85.0511)
    zones, missing = {}, []
    for c in data["countries"]:
        iso2, a3 = c["id"], (c.get("a3") or "").upper()
        if a3 in by_a3:
            g = unary_union(by_a3[a3]).intersection(world)
            land = shape(sil[iso2]) if sil.get(iso2) else None
            # ¿Tiene mar? Si la zona es mucho mayor que la tierra, sí
            has_sea = land is None or g.area > land.area * 1.05
        elif sil.get(iso2):
            g = shape(sil[iso2]).buffer(0.1, resolution=2).intersection(world)
            has_sea = False
            missing.append(iso2)
        else:
            missing.append(iso2 + "?")
            continue
        p = pack(g)
        if not p:
            # Países diminutos (Mónaco, Vaticano): su rectángulo con un pequeño margen
            w, s_, e, n_ = g.buffer(0.02).bounds
            p = [[round(v, 3) for v in (w, s_, e, s_, e, n_, w, n_)]]
        zones[iso2] = {"bbox": [round(v, 3) for v in g.bounds], "sea": bool(has_sea), "p": p}
    out = {"v": 1,
           "src": "Flanders Marine Institute (2024): Marine Regions «eez_land», union of world country boundaries and EEZ (CC BY 4.0, marineregions.org)",
           "zones": zones}
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    pts = sum(len(r) // 2 for z in zones.values() for r in z["p"])
    print(f"{len(zones)} países, {pts} puntos, {OUT.stat().st_size / 1e6:.2f} MB; sin ZEE: {missing}")


if __name__ == "__main__":
    sys.exit(main())
