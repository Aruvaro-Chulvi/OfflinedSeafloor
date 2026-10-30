# 🌊 Offlined Seafloor

**The relief of the ocean floor, offline.**
By **Álvaro C. Chulvi** · a project of **[Offlined](https://www.offlined.org)**

[English](#english) · [Español](#español)

---

## English

Offlined Seafloor is the data behind **World → Seas & Oceans → Explore** in
[Offlined](https://www.offlined.org), the app that brings Wikipedia, maps and AI to your computer without
internet. It publishes two things:

- **`seafloor-gebco2026-z*.pmtiles`** (in [Releases](../../releases)): the elevation of the whole planet,
  land and sea, from the **GEBCO 2026 Grid**, reprojected to Web Mercator and stored as
  [PMTiles](https://github.com/protomaps/PMTiles) raster-dem tiles (Terrarium encoding, lossless WebP,
  512 px, whole metres). Any map library that reads Terrarium elevation (MapLibre GL, for example) can
  draw it as depth colours, hillshade or 3D terrain.
- **[`data/seafloor_features.json`](data/seafloor_features.json)**: the **5,311 named undersea features**
  of the IHO-IOC GEBCO Gazetteer (trenches, ridges, seamounts, canyons, basins…) with their geometry,
  their depth measured on the grid and, for 839 of them, their name and exact Wikipedia article in
  10 languages from Wikidata.

| Package | Zoom | Resolution at the equator | Size |
|---|---|---|---:|
| Standard | 0–6 | ~2.4 km per pixel | 668 MB |
| Detailed | 0–7 | ~1.2 km per pixel | 2.1 GB (2 parts) |

> ⚠️ **Not for navigation.** GEBCO data must not be used for navigation or for any purpose involving
> safety at sea.

### In Offlined

Offlined downloads the package from the latest release (it reads [`manifest.json`](manifest.json):
files, sizes and MD5). Packages larger than 2 GiB are published in parts and joined after download.
If you already have the file, choose it with *I already have it: choose file*.

### Rebuild it

The scripts in [`scripts/`](scripts) rebuild everything from the original sources (Python 3.11,
`pip install -r scripts/requirements.txt`, ~25 GB free):

```bash
cd scripts && mkdir work
curl -o work/gebco_2026_webmerc.tif https://data.source.coop/giswqs/gebco-bathymetry/gebco_2026/gebco_2026_webmerc.tif
python build_z7.py          # GEBCO (EPSG:4326) → Web Mercator raster at z7 (65536², 8.6 GB)
python build_tiles.py       # pyramid z6…z0 and Terrarium tiles in work/tiles
python pack.py work/seafloor-gebco2026-z6.pmtiles 6
python pack.py work/seafloor-gebco2026-z7.pmtiles 7
python fetch_gaz.py         # gazetteer from the IHO DCDB ArcGIS service
python wd_match.py          # Wikidata: exact English label + nearby coordinates
python build_features.py    # → data/seafloor_features.json
python make_release.py gebco-2026 work/seafloor-gebco2026-z6.pmtiles:std work/seafloor-gebco2026-z7.pmtiles:hd
```

`make_release.py` splits large packages, computes the MD5s and writes `manifest.json`; upload the files
of `work/release/` (manifest included) to a release named after the tag.

### Credits

See [NOTICE.md](NOTICE.md). Bathymetry: *GEBCO Compilation Group (2026) GEBCO 2026 Grid*.
Names: *IHO-IOC GEBCO Gazetteer of Undersea Feature Names, www.gebco.net*. Offlined Seafloor is not
endorsed by GEBCO, the IHO or the IOC.

---

## Español

Offlined Seafloor son los datos de **Mundo → Mares y Océanos → Explorar** en
[Offlined](https://www.offlined.org), la app que lleva Wikipedia, mapas e IA a tu ordenador sin internet.
Publica dos cosas:

- **`seafloor-gebco2026-z*.pmtiles`** (en [Releases](../../releases)): la altitud de todo el planeta,
  tierra y mar, de la cuadrícula **GEBCO 2026**, reproyectada a Web Mercator y guardada como teselas
  raster-dem [PMTiles](https://github.com/protomaps/PMTiles) (codificación Terrarium, WebP sin pérdida,
  512 px, metros enteros). Cualquier librería de mapas que lea altitud Terrarium (MapLibre GL, por
  ejemplo) puede pintarla como color por profundidad, sombreado o relieve 3D.
- **[`data/seafloor_features.json`](data/seafloor_features.json)**: los **5.311 relieves submarinos con
  nombre** del nomenclátor IHO-IOC GEBCO (fosas, dorsales, montes submarinos, cañones, cuencas…) con su
  geometría, su profundidad medida en la cuadrícula y, en 839 de ellos, su nombre y su artículo exacto
  de Wikipedia en 10 idiomas, desde Wikidata.

| Paquete | Zoom | Resolución en el ecuador | Tamaño |
|---|---|---|---:|
| Estándar | 0–6 | ~2,4 km por píxel | 668 MB |
| Detalle | 0–7 | ~1,2 km por píxel | 2,1 GB (2 trozos) |

> ⚠️ **No apto para navegar.** Los datos de GEBCO no deben usarse para la navegación ni para nada que
> tenga que ver con la seguridad en el mar.

### En Offlined

Offlined descarga el paquete de la última release (lee [`manifest.json`](manifest.json): archivos,
tamaños y MD5). Los paquetes de más de 2 GiB se publican en trozos y se unen al descargarlos. Si ya
tienes el archivo, elígelo con *Ya lo tengo: elegir archivo*.

### Regenerarlo

Los scripts de [`scripts/`](scripts) lo rehacen todo desde las fuentes originales (los pasos están
arriba, en inglés). `make_release.py` parte los paquetes grandes, calcula los MD5 y escribe
`manifest.json`; los archivos de `work/release/` (con el manifest) se suben a una release con ese tag.

### Créditos

Ver [NOTICE.md](NOTICE.md). Batimetría: *GEBCO Compilation Group (2026) GEBCO 2026 Grid*. Nombres:
*IHO-IOC GEBCO Gazetteer of Undersea Feature Names, www.gebco.net*. Offlined Seafloor no está avalado
por GEBCO, la OHI ni la COI.
