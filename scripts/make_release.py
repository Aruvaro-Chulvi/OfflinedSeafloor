"""Prepara los archivos de una Release de GitHub y el manifest.json que lee Offlined.

GitHub no admite assets de 2 GiB o más: los paquetes grandes se parten en trozos
(`<archivo>.part1`, `.part2`…) que Offlined descarga y vuelve a unir. El manifest
lleva el tamaño y el MD5 de cada trozo y del archivo entero.

Uso: make_release.py <tag> <paquete.pmtiles>:<id> [<paquete.pmtiles>:<id> …]
     p. ej. make_release.py gebco-2026 work/seafloor-gebco2026-z6.pmtiles:std work/seafloor-gebco2026-z7.pmtiles:hd
Deja en work/release/ los trozos y manifest.json, y copia el manifest a la raíz del repo.
"""
import hashlib, json, os, shutil, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("SEAFLOOR_WORK") or (Path(__file__).parent / "work"))
OUT = WORK / "release"
PART = int(os.environ.get("SEAFLOOR_PART") or 1_900_000_000)   # < 2 GiB, con margen
REPO = "Aruvaro-Chulvi/OfflinedSeafloor"


def maxzoom(path: Path) -> int:
    with open(path, "rb") as f:
        h = f.read(127)
    assert h[:7] == b"PMTiles" and h[7] == 3, f"{path} no es PMTiles v3"
    return h[101]


def main():
    tag, specs = sys.argv[1], sys.argv[2:]
    OUT.mkdir(parents=True, exist_ok=True)
    packs = []
    for spec in specs:
        src, pid = spec.rsplit(":", 1)
        src = Path(src)
        size = src.stat().st_size
        whole = hashlib.md5()
        parts = []
        with open(src, "rb") as f:
            n = 0
            while True:
                n += 1
                name = src.name if size < PART else f"{src.name}.part{n}"
                ph, done = hashlib.md5(), 0
                with open(OUT / name, "wb") as o:
                    while done < (size if size < PART else PART):
                        b = f.read(min(8 << 20, PART - done))
                        if not b:
                            break
                        o.write(b); ph.update(b); whole.update(b); done += len(b)
                if done == 0:
                    (OUT / name).unlink()
                    break
                parts.append({"name": name, "size": done, "md5": ph.hexdigest()})
                if size < PART or f.tell() >= size:
                    break
        packs.append({"id": pid, "maxzoom": maxzoom(src), "file": src.name, "size": size,
                      "md5": whole.hexdigest(), "parts": parts})
        print(pid, src.name, size, len(parts), "trozo(s)")
    manifest = {
        "name": "Offlined Seafloor", "version": tag,
        "base_url": f"https://github.com/{REPO}/releases/download/{tag}/",
        "attribution": "GEBCO Compilation Group (2026) GEBCO 2026 Grid",
        "packs": packs,
    }
    txt = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (OUT / "manifest.json").write_text(txt, encoding="utf-8")
    (ROOT / "manifest.json").write_text(txt, encoding="utf-8")
    print("->", OUT)


if __name__ == "__main__":
    main()
