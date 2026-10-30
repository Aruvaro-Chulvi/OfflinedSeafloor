"""Paso B: pirámide z7→z0 (media 2×2) y teselas Terrarium WebP sin pérdida en tiles/z/x/y.webp.
Paso C (pack.py) las junta en un PMTiles."""
import io, os, sys, time
from pathlib import Path
from multiprocessing import Pool
import numpy as np
from PIL import Image

WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
TS, ZMAX = 512, 7
TILES = WORK / "tiles"


def level_path(z):
    return WORK / f"z{z}.i16"


def level(z, mode="r"):
    n = TS << z
    return np.memmap(level_path(z), dtype=np.int16, mode=mode, shape=(n, n))


def build_pyramid():
    for z in range(ZMAX - 1, -1, -1):
        if level_path(z).exists():
            continue
        src, n = level(z + 1), TS << z
        dst = level(z, "w+")
        step = 1024
        for r in range(0, n, step):
            a = np.asarray(src[2 * r:2 * (r + step)], dtype=np.int32)
            m = (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2] + 2) // 4
            dst[r:r + step] = m.astype(np.int16)
        dst.flush()
        print("level", z, "ok", flush=True)


def encode_tile(args):
    z, x, y = args
    out = TILES / str(z) / str(x) / f"{y}.webp"
    if out.exists():
        return 0
    lv = level(z)
    h = np.asarray(lv[y * TS:(y + 1) * TS, x * TS:(x + 1) * TS], dtype=np.int32) + 32768
    rgb = np.zeros((TS, TS, 3), np.uint8)
    rgb[..., 0] = h >> 8
    rgb[..., 1] = h & 255
    b = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(b, "WEBP", lossless=True, quality=100, method=int(os.environ.get("WEBP_METHOD", "4")))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(b.getvalue())
    tmp.replace(out)
    return len(b.getvalue())


def main():
    build_pyramid()
    zs = [int(a) for a in sys.argv[1:]] or list(range(ZMAX + 1))
    with Pool(max(1, (os.cpu_count() or 4) - 2)) as pool:
        for z in zs:
            t0 = time.time()
            jobs = [(z, x, y) for x in range(1 << z) for y in range(1 << z)]
            tot = sum(pool.imap_unordered(encode_tile, jobs, chunksize=8))
            print("z", z, len(jobs), "tiles", tot // (1 << 20), "MB new", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
