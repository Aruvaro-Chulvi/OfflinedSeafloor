"""Paso A: GEBCO (EPSG:4326) → ráster Web Mercator z7 (65536×65536 int16) en un memmap.
Uso: build_z7.py [bloque_inicial bloque_final]   (bloques de 512 filas, 0..127)"""
import math, os, sys, time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window

WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
SRC = WORK / "gebco_2026_webmerc.tif"   # GEBCO en EPSG:4326, ±85° (source.coop giswqs/gebco-bathymetry)
OUT = WORK / "z7.i16"
Z, TS = 7, 512
N = TS << Z


def main():
    b0, b1 = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, N // TS)
    ds = rasterio.open(SRC)
    W, H = ds.width, ds.height
    res, top = 360.0 / W, 85.0
    mm = np.memmap(OUT, dtype=np.int16, mode="r+" if OUT.exists() else "w+", shape=(N, N))
    lon = (np.arange(N, dtype=np.float64) + 0.5) / N * 360.0 - 180.0
    fc = np.clip((lon + 180.0) / res - 0.5, 0, W - 1)
    c0 = np.floor(fc).astype(np.int64); c1 = np.minimum(c0 + 1, W - 1)
    wc = (fc - c0).astype(np.float32)
    for b in range(b0, b1):
        t0 = time.time()
        rows = np.arange(b * TS, (b + 1) * TS, dtype=np.float64)
        lat = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * (rows + 0.5) / N))))
        fr = np.clip((top - lat) / res - 0.5, 0, H - 1)
        r0 = int(math.floor(fr.min())); r1 = min(H, int(math.floor(fr.max())) + 2)
        a = ds.read(1, window=Window(0, r0, W, r1 - r0)).astype(np.float32)
        a[a <= -32000] = 0
        ah = a[:, c0] * (1 - wc) + a[:, c1] * wc
        rr = fr - r0
        q0 = np.floor(rr).astype(np.int64); q1 = np.minimum(q0 + 1, ah.shape[0] - 1)
        wr = (rr - q0).astype(np.float32)[:, None]
        out = ah[q0] * (1 - wr) + ah[q1] * wr
        mm[b * TS:(b + 1) * TS] = np.clip(np.round(out), -11000, 9000).astype(np.int16)
        print(b, r0, r1, round(time.time() - t0, 2), flush=True)
    mm.flush()


if __name__ == "__main__":
    main()
