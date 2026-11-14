# Domain pack: Agriculture (computational & secondary-data research)

Agriculture is not one field. It spans biology, earth science, engineering, economics and policy, and
Q1 reviewers come from each of these traditions. This pack tells the agent how each subfield frames
contributions, which data and methods are standard, what reviewers attack, and which reporting
standards apply. Files:

| File | Use it in |
|---|---|
| `DOMAIN.md` (this) | S0–S1: framing, subfield map, search vocabulary |
| `DATASETS.md` | S0, S3: open data sources by subfield |
| `METHODS.md` | S2, S4: standard methods and expected baselines |
| `PITFALLS.md` | S2, S4, S8: leakage and validity traps reviewers look for |
| `REPORTING.md` | S2, S7, S8: reporting guidelines and checklists |
| `JOURNALS.md` | S0, S9: venue map (quartiles must be re-verified) |

## Subfield map

| # | Subfield | Typical computational questions | Where Q1 contributions usually come from |
|---|---|---|---|
| A1 | Agronomy & crop modelling | yield gaps, management × environment, model inter-comparison, calibration | process understanding, transferable models, uncertainty decomposition |
| A2 | Agro-climatology & climate impacts | heat/drought effects, attribution, projections, adaptation | causal identification of weather effects, robust ensembles, extremes |
| A3 | Remote sensing & digital agriculture | crop mapping, yield/phenology estimation, irrigation detection | generalisation across space/time/sensors, label-scarce learning, uncertainty maps |
| A4 | Soil science & land | soil property mapping, carbon stocks, degradation, erosion | digital soil mapping with honest validation, change detection, MRV-grade uncertainty |
| A5 | Water & irrigation | ET estimation, water productivity, groundwater, scheduling | water accounting at scale, evaluation against independent measurements |
| A6 | Plant breeding, genetics & genomics | GWAS, genomic prediction, G×E, phenomics | prediction across environments/populations, multi-omics integration, biological validation via public data |
| A7 | Plant protection | disease/pest risk models, image-based diagnosis, spread | field-realistic generalisation, early warning skill, explainability tied to biology |
| A8 | Livestock & animal science | productivity, emissions, disease surveillance, welfare from sensors | robust prediction across farms, emission inventories with uncertainty |
| A9 | Fisheries & aquaculture | stock assessment, catch reconstruction, aquaculture expansion | data-limited methods, remote sensing of ponds/cages, climate impacts |
| A10 | Agricultural economics & policy | adoption, prices, markets, subsidies, insurance, food security | credible causal identification, heterogeneity, welfare/distributional effects |
| A11 | Food systems & nutrition | supply chains, loss & waste, diets, trade, footprints | system-level accounting with uncertainty, scenario analysis |
| A12 | Agri-environment & sustainability | emissions, biodiversity, LCA, land-use change | spatially explicit accounting, trade-offs/synergies, robust attribution |
| A13 | Agricultural AI & software | ML benchmarks, decision-support tools, crop-model software quality | rigorous benchmarks, reproducible tools, failure analysis, software testing of scientific models |

## What makes an agriculture paper Q1 (beyond the general rubric)

1. **Transfer, not just fit.** Results validated on held-out regions/years/seasons, or the paper
   explains exactly where they do not transfer.
2. **Mechanism or decision relevance.** Either explains *why* (biophysical/economic mechanism, tested)
   or changes *what someone should do* (with quantified benefit and uncertainty).
3. **Scale with honesty.** Large spatial/temporal coverage is valued only with uncertainty and bias
   assessment (e.g. map accuracy assessment, reporting-unit bias).
4. **Independent ground truth.** Model outputs compared with measurements not used in training (field
   trials, flux towers, census statistics, independent surveys).
5. **Benchmark against the field's standards.** Process models, published products (e.g. MODIS/
   Sentinel-based products, global yield datasets) and strong ML baselines, not only naive baselines.
6. **Global South relevance done right.** Studies in data-scarce regions are welcomed when they address
   data quality explicitly and contribute transferable knowledge, not just "first study in region X".

## Search vocabulary (concept blocks; combine with AND, synonyms with OR)

- **Crops / systems:** rice OR paddy OR "Oryza sativa"; wheat OR "Triticum aestivum"; maize OR corn OR
  "Zea mays"; "cropping system*"; "smallholder*"; "agro-ecological zone*"; "farming system*"
- **Outcomes:** yield OR productivity OR "crop production"; "yield gap*"; "water productivity";
  "soil organic carbon" OR SOC; emissions OR "greenhouse gas*" OR GHG; adoption; "food security"
- **Stressors / drivers:** drought OR "water stress"; heat OR "high temperature" OR "extreme heat";
  salinity; flood* OR submergence; "climate change" OR "climate variability"; pest* OR disease*
- **Methods:** "crop model*" OR APSIM OR DSSAT OR AquaCrop OR WOFOST OR "STICS"; "remote sensing" OR
  Sentinel-2 OR Landsat OR MODIS OR SAR; "machine learning" OR "deep learning" OR "random forest" OR
  XGBoost OR transformer; "genomic prediction" OR GWAS OR "genomic selection"; "difference-in-
  differences" OR "instrumental variable" OR "panel data" OR "synthetic control"
- **Validation words:** transferability OR generalization OR "out-of-sample" OR "spatial cross-
  validation" OR "leave-one-year-out" OR "domain shift"

## Framing templates that reviewers in this field respect

- "Where and why do <models> fail to transfer across <space/time>?" (A1, A3, A6)
- "How much of <outcome> variability is explained by <driver> after removing <confounder>?" (A2, A10)
- "Can <cheap/open data> replace <expensive measurement> for <decision>, and with what error?" (A3, A4, A5)
- "Do independent implementations of <model> agree, and what explains disagreement?" (A1, A13)
- "Which design choices explain divergent published estimates of <effect>?" (meta-analysis; any)
