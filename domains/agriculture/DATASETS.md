# Open data for computational agriculture research

> Curated November 2026. URLs were checked to respond at curation time, but **datasets move, versions
> change and licenses differ by product**. In S3 the agent must open each source page, record the exact
> version/access date and the license in `ledgers/DATA_PROVENANCE.csv`, and never assume a license
> from this list.

## Weather & climate

| Dataset | What | Access | URL |
|---|---|---|---|
| NASA POWER | Daily agro-meteorology (radiation, Tmin/Tmax, precipitation, humidity, wind), global, 1981– | REST API, no key | https://power.larc.nasa.gov/ |
| ERA5 / ERA5-Land | ECMWF reanalysis, hourly, global | Copernicus CDS API (free account) | https://cds.climate.copernicus.eu/ |
| AgERA5 | ERA5 derived daily agro-meteorological indicators | CDS | https://cds.climate.copernicus.eu/ |
| CHIRPS | Quasi-global gridded rainfall, 0.05°, 1981– | Download / GEE | https://www.chc.ucsb.edu/data/chirps |
| WorldClim | Climate normals and CMIP6 downscaled projections | Download | https://www.worldclim.org/ |
| CMIP6 (ESGF) | Global climate model projections | ESGF nodes | https://esgf.llnl.gov/ |
| GHCN-Daily | Station observations | NOAA NCEI | https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily |

## Satellite & geospatial

| Dataset | What | Access | URL |
|---|---|---|---|
| Sentinel-2 / Sentinel-1 | 10 m optical / C-band SAR | Copernicus Data Space (free) | https://dataspace.copernicus.eu/ |
| Landsat Collection 2 | 30 m optical/thermal, 1984– | USGS EarthExplorer / GEE | https://www.usgs.gov/landsat-missions |
| MODIS (e.g. MOD13Q1 NDVI/EVI) | 250 m–1 km vegetation, LST, ET, 2000– | NASA LP DAAC / GEE | https://lpdaac.usgs.gov/ |
| Google Earth Engine catalog | Petabyte catalog + compute (free for research/non-commercial) | GEE | https://developers.google.com/earth-engine/datasets |
| Microsoft Planetary Computer | STAC catalog of analysis-ready data | STAC API | https://planetarycomputer.microsoft.com/ |
| FAO WaPOR | Water productivity, ET, biomass (Africa & Near East) | Portal / API | https://data.apps.fao.org/wapor/ |
| OpenET | Field-scale ET (USA) | Portal / API | https://openetdata.org/ |
| SMAP | Soil moisture | NASA NSIDC | https://smap.jpl.nasa.gov/ |
| ESA WorldCover / WorldCereal | Land cover / crop type maps | Download / GEE | https://esa-worldcover.org/ and https://esa-worldcereal.org/ |

## Crops, yields & agricultural statistics

| Dataset | What | Access | URL |
|---|---|---|---|
| FAOSTAT | Country-level production, area, yield, trade, inputs, emissions, prices | Bulk download / API | https://www.fao.org/faostat/ |
| USDA NASS Quick Stats | US county/state crop statistics | API (free key) | https://quickstats.nass.usda.gov/ |
| Eurostat agriculture | EU regional crop and farm statistics | API | https://ec.europa.eu/eurostat/ |
| MapSPAM | Gridded crop area/production/yield (by crop, by system) | Download | https://www.mapspam.info/ |
| FAO GAEZ v4 | Agro-ecological zones, suitability, attainable yield | Portal | https://gaez.fao.org/ |
| Global Yield Gap Atlas | Yield potential and gaps by climate zone | Portal | https://www.yieldgap.org/ |
| National statistics offices | Sub-national yields (e.g. Bangladesh Bureau of Statistics) | Reports / portals | https://bbs.gov.bd/ (example) |

## Soil & land

| Dataset | What | Access | URL |
|---|---|---|---|
| SoilGrids | Global 250 m soil property predictions with uncertainty | WCS / download | https://soilgrids.org/ |
| ISRIC WoSIS | Harmonised soil profile observations | WFS / download | https://www.isric.org/explore/wosis |
| LUCAS Soil (EU) | Topsoil survey points | ESDAC | https://esdac.jrc.ec.europa.eu/ |

## Genomics & breeding

| Dataset | What | Access | URL |
|---|---|---|---|
| NCBI SRA / GEO | Raw sequencing reads / expression | E-utilities, SRA toolkit | https://www.ncbi.nlm.nih.gov/sra |
| Ensembl Plants | Plant genomes, variation, annotation | REST / FTP | https://plants.ensembl.org/ |
| Gramene | Comparative plant genomics | Portal | https://www.gramene.org/ |
| Rice SNP-Seek (3K RGP) | Rice genotypes/phenotypes | Portal | https://snp-seek.irri.org/ |
| CGIAR / Harvard Dataverse | Trials, surveys, phenotypes from CGIAR centers | Dataverse API | https://dataverse.harvard.edu/ |
| Genesys | Germplasm accessions | API | https://www.genesys-pgr.org/ |

## Plant protection & biodiversity

| Dataset | What | Access | URL |
|---|---|---|---|
| GBIF | Species occurrences (pests, pathogens, pollinators, crop wild relatives) | API | https://www.gbif.org/ |
| PlantVillage (and successors) | Leaf images (lab conditions; see PITFALLS) | GitHub / Kaggle mirrors | https://github.com/spMohanty/PlantVillage-Dataset |

## Livestock, fisheries & food

| Dataset | What | Access | URL |
|---|---|---|---|
| FAO FishStat | Capture and aquaculture production | FishStatJ / download | https://www.fao.org/fishery/en/statistics |
| Sea Around Us | Reconstructed catches by EEZ | Portal / API | https://www.seaaroundus.org/ |
| USDA FoodData Central | Food composition | API | https://fdc.nal.usda.gov/ |
| EM-DAT | Disaster events and impacts (registration) | Portal | https://www.emdat.be/ |

## Socio-economic & policy

| Dataset | What | Access | URL |
|---|---|---|---|
| World Bank LSMS-ISA | Household panel surveys with agriculture modules | Microdata library | https://www.worldbank.org/en/programs/lsms |
| DHS Program | Demographic & health surveys (nutrition, geocoded clusters) | Registration | https://dhsprogram.com/ |
| World Bank WDI | Country indicators | API | https://data.worldbank.org/ |
| FEWS NET | Food security outlooks, prices | Portal / API | https://fews.net/ |
| IFPRI datasets | Policy, public spending, surveys | Dataverse | https://www.ifpri.org/ |
| USDA ERS | US farm economics, trade, food prices | Download | https://www.ers.usda.gov/ |

## Model ensembles & benchmarks

| Resource | What | URL |
|---|---|---|
| AgMIP | Crop/economic model inter-comparison protocols and data | http://agmip.org/ (site served over http at curation time) |
| ISIMIP | Impact-model outputs incl. agriculture under climate scenarios | https://www.isimip.org/ |

## How to choose data for a Q1 paper

1. **Independent validation data exists** (field measurements, census, surveys) that you do not train on.
2. **Coverage matches the claim**: if you claim generality, you need multiple regions/years.
3. **Resolution matches the process**: field-level questions need field-level data; district statistics
   support district-level claims only (ecological fallacy).
4. **Known artefacts are documented** (sensor changes, reporting changes, gap-filling).
5. **License allows publication** of derived results and, ideally, sharing processed data.
