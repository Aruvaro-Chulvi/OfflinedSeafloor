"""Descarga el nomenclátor GEBCO/SCUFN (puntos, líneas, polígonos) a GeoJSON."""
import json, os, sys, time, requests
from pathlib import Path

BASE = "https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/Undersea_Features/FeatureServer"
WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
OUT = WORK

for lid, name in ((0, "points"), (1, "lines"), (2, "polygons")):
    feats, off = [], 0
    while True:
        r = requests.get(f"{BASE}/{lid}/query", params={
            "where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
            "resultOffset": off, "resultRecordCount": 1000, "orderByFields": "OBJECTID"}, timeout=120)
        r.raise_for_status()
        d = r.json()
        fs = d.get("features", [])
        feats += fs
        print(name, off, len(fs), flush=True)
        if len(fs) < 1000:
            break
        off += 1000
        time.sleep(0.3)
    (OUT / f"{name}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    print(name, "total", len(feats))
