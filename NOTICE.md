# Notice

**Offlined Seafloor** — © 2026 **Álvaro C. Chulvi**, a project of **[Offlined](https://www.offlined.org)**.

## What is licensed under what

| Part | Files | License |
|---|---|---|
| Seafloor packages (tiling, encoding, packaging) | `seafloor-*.pmtiles` in Releases | [CC BY-NC-SA 4.0](LICENSE) |
| Undersea features dataset (selection, depths, Wikidata matching) | `data/seafloor_features.json` | [CC BY-NC-SA 4.0](LICENSE) |
| Seas and oceans dataset (simplified areas, Wikidata matching) | `data/sea_areas.json` | [CC BY-NC-SA 4.0](LICENSE) |
| Build scripts | `scripts/` | [PolyForm Noncommercial 1.0.0](LICENSE-CODE.md) |

You may use, copy, modify and share Offlined Seafloor **for non-commercial purposes**, crediting the
author and the sources below. Commercial use is reserved to the author: if you want to use it
commercially, get in touch through [offlined.org](https://www.offlined.org).

**Offlined** (the application by Álvaro C. Chulvi and Eric Uguet, https://www.offlined.org) is authorized by
the author to use, include and distribute Offlined Seafloor, also for commercial purposes.

The underlying GEBCO Grid is in the **public domain** and the Marine Regions datasets are **CC BY 4.0**:
this license covers this project's own work, not their data, which you can always get directly from
[gebco.net](https://www.gebco.net) and [marineregions.org](https://www.marineregions.org) under their own terms.

## How to credit

> Offlined Seafloor by Álvaro C. Chulvi, a project of Offlined (https://www.offlined.org) — CC BY-NC-SA 4.0.
> Bathymetry: GEBCO Compilation Group (2026) GEBCO 2026 Grid. Names: IHO-IOC GEBCO Gazetteer of Undersea
> Feature Names, www.gebco.net. Seas and oceans: Flanders Marine Institute, Marine Regions
> (www.marineregions.org), CC BY 4.0.

## Third-party sources

- **GEBCO 2026 Grid** — GEBCO Compilation Group (2026). Public domain, free to copy, adapt and use
  commercially with attribution, without suggesting official status. **Not to be used for navigation or
  for any purpose involving safety at sea.** Terms: https://www.gebco.net/data-products/gridded-bathymetry/terms-of-use
  — downloaded from the Cloud Optimized GeoTIFF copy on Source Cooperative (`giswqs/gebco-bathymetry`).
- **IHO-IOC GEBCO Gazetteer of Undersea Feature Names** — maintained by the GEBCO Sub-Committee on
  Undersea Feature Names (SCUFN), served by the IHO Data Centre for Digital Bathymetry (NOAA NCEI).
  Citation requested: *IHO-IOC GEBCO Gazetteer of Undersea Feature Names, www.gebco.net*.
- **IHO Sea Areas, version 3** and **Global Oceans and Seas, version 1** — Flanders Marine Institute
  (2018 and 2021), Marine Regions, www.marineregions.org, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  https://doi.org/10.14284/323 · https://doi.org/10.14284/542 — polygons simplified to ~4 km by
  `scripts/build_seas.py` (used in `data/sea_areas.json`).
- **Marine Regions «eez_land»** (union of world country boundaries and Exclusive Economic Zones) —
  Flanders Marine Institute (2024), www.marineregions.org, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Only read by `scripts/build_chart_zones.py` to make the country zones that Offlined uses to split its
  sea charts; no data from it is published in this repository.
- **Wikidata** (CC0): translated names and Wikipedia article titles of the matched features, seas and
  oceans (the seas through property P3006, Marine Regions Geographic ID).
- Wikipedia® is a registered trademark of the Wikimedia Foundation. This project is not affiliated with
  or endorsed by the Wikimedia Foundation, GEBCO, the IHO, the IOC or the Flanders Marine Institute.
