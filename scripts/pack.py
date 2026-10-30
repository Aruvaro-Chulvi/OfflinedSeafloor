"""Paso C: tiles/z/x/y.webp → seafloor.pmtiles. Uso: pack.py salida.pmtiles maxzoom"""
import json, os, sys
from pathlib import Path
from pmtiles.tile import zxy_to_tileid, TileType, Compression
from pmtiles.writer import Writer

WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
TILES = WORK / "tiles"


def main():
    out, maxz = Path(sys.argv[1]), int(sys.argv[2])
    ids = []
    for z in range(maxz + 1):
        for x in range(1 << z):
            for y in range(1 << z):
                ids.append((zxy_to_tileid(z, x, y), z, x, y))
    ids.sort()
    with open(out, "wb") as f:
        w = Writer(f)
        for tid, z, x, y in ids:
            w.write_tile(tid, (TILES / str(z) / str(x) / f"{y}.webp").read_bytes())
        w.finalize(
            {
                "tile_type": TileType.WEBP, "tile_compression": Compression.NONE,
                "min_zoom": 0, "max_zoom": maxz,
                "min_lon_e7": -1800000000, "min_lat_e7": -850511287, "max_lon_e7": 1800000000, "max_lat_e7": 850511287,
                "center_zoom": 2, "center_lon_e7": 0, "center_lat_e7": 0,
            },
            {
                "name": "Offlined Seafloor",
                "type": "baselayer", "format": "webp", "encoding": "terrarium", "tileSize": 512,
                "offlined": "seafloor", "version": "gebco-2026",
                "attribution": "GEBCO Compilation Group (2026) GEBCO 2026 Grid",
                "description": "GEBCO 2026 Grid reprojected to Web Mercator, Terrarium-encoded elevation in metres (1 m). Not for navigation.",
            },
        )
    print(out, out.stat().st_size // (1 << 20), "MB")


if __name__ == "__main__":
    main()
