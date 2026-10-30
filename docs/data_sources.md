# Data sources and licences

Licences below were checked against the publishers' own pages on **2026-10-30**. Confirm the current terms
before redistributing any data. **No dataset is committed to this repository**; everything is downloaded by
the ingestion code.

| Source | What is used | Native grain | Licence | Access |
|---|---|---|---|---|
| FAOSTAT, *Crops and livestock products* | Production, area harvested, yield, livestock elements for Cambodia (1961-2024) | country x year x item | CC BY 4.0 (FAO database terms of use apply) | Bulk file `Production_Crops_Livestock_E_All_Data_(Normalized).zip` (about 34 MB). The REST API requires authentication, so it is not used |
| World Bank Indicators API v2 | 8 indicators for Cambodia (listed in `config.py`) | country x year x indicator | CC BY 4.0 (World Bank default for its datasets) | Public JSON API, no key |
| CHIRPS v3.0 monthly precipitation | Cambodia window, aggregated to provinces | 0.05 degree grid, monthly | Public domain / CC BY 4.0 per the Climate Hazards Center | `data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/tifs/` read with GDAL `/vsicurl/` |
| geoBoundaries gbOpen ADM1 (Cambodia) | 25 province polygons | province | ODbL 1.0 (attribution; share-alike for derived databases) | geoBoundaries API |

## Required attribution

- FAO. *FAOSTAT: Crops and livestock products.* Food and Agriculture Organization of the United Nations.
  https://www.fao.org/faostat/ . Accessed 2026-10-30. Licence: CC BY 4.0.
- World Bank. *World Development Indicators / Indicators API v2.* https://api.worldbank.org/v2/ .
  Last updated by source: 2026-10-08. Licence: CC BY 4.0.
- Climate Hazards Center. *CHIRPS3 Data Repository.* doi:10.15780/G2JQ0P (2025). Data accessed 2026-10-30.
  Paper: Funk et al. (2026), *Scientific Data* 13, 718, doi:10.1038/s41597-026-07096-4 (as given on the
  CHC CHIRPS3 page).
- geoBoundaries (William & Mary geoLab). https://www.geoboundaries.org/ . Boundary vintage represented: 2017.
  Licence: ODbL 1.0.

## Things to know about the data

- FAOSTAT rows flagged `E` are estimates and `I` are values imputed by FAO. Both are source-side flags and
  are kept in the fact tables (`production_flag`, `area_flag`, `yield_flag`).
- 221 of 12,621 Cambodia FAOSTAT rows (1.75%) have no value (flag `M`). They remain NULL.
- 95 of 528 World Bank observations (18.0%) are null for the requested indicators. They remain NULL with
  `is_missing = true`.
- Province names are exactly as spelled by geoBoundaries (for example "Bantey Meanchey",
  "Ratanakiri Province", "Tbong Khmum"). They are not normalised to any national gazetteer.
- Boundaries are from 2017, so they may not match current administrative boundaries.

## Not used

- No National Institute of Statistics (NIS) data, no company data and no private data of any kind.
