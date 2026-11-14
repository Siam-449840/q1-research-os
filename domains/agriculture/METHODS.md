# Standard methods and expected baselines (agriculture)

Use this to (a) choose the primary analysis, (b) name baselines a reviewer will expect, and (c) pick
the right validation. "Expected baseline" means a reviewer will likely ask "why didn't you compare to X?".

## A1 Agronomy & crop modelling
- **Process models:** APSIM, DSSAT, AquaCrop (FAO; official Fortran and AquaCrop-OSPy), WOFOST/PCSE,
  STICS, ORYZA (rice). Calibrate on one subset, evaluate on another; report RMSE, nRMSE, bias, Willmott d,
  Nash–Sutcliffe; parameter uncertainty (GLUE, Bayesian calibration), multi-model ensembles.
- **Statistical:** linear mixed models for multi-environment trials (site/year random effects),
  yield-gap analysis (boundary-line, stochastic frontier, quantile regression).
- **Expected baselines:** climatology/mean yield, linear trend, published model ensemble outputs.

## A2 Climate impacts
- **Panel regressions** with location fixed effects and year/technology trends (piecewise-linear degree
  days, extreme-degree-days, precipitation splines); clustered SEs (spatial/HAC, Conley).
- **Crop-model ensembles** forced by bias-corrected CMIP6 (SSP scenarios; multiple GCMs).
- **Attribution:** counterfactual climate, event attribution; detrending before attribution.
- **Expected baselines:** simple temperature/precipitation regression; published sensitivity estimates.

## A3 Remote sensing & digital agriculture
- **Features:** vegetation indices (NDVI, EVI, NDRE), SAR backscatter/coherence, phenology metrics,
  time-series composites; cloud masking documented.
- **Models:** random forest / gradient boosting, temporal CNN/LSTM/transformers, light-use-efficiency
  models, data assimilation into crop models, foundation models (fine-tuned) with honest comparison.
- **Validation:** spatial block CV / leave-region-out, leave-year-out; map accuracy assessment with
  area-adjusted estimates (Olofsson et al. good practice) for classification maps.
- **Expected baselines:** RF/XGBoost on standard indices; existing products (e.g. national crop masks,
  WorldCereal); simple statistical yield models.

## A4 Soil
- **Digital soil mapping:** RF/quantile regression forests, regression kriging, Gaussian processes;
  covariates (terrain, climate, spectral). Uncertainty via QRF/bootstrapping; validation with
  probability sampling or spatial CV; report MEC/R², RMSE, PICP.
- **Expected baselines:** SoilGrids, ordinary kriging.

## A5 Water & irrigation
- **ET:** FAO-56 Penman–Monteith reference ET, crop coefficients, SEBAL/METRIC/SSEBop, products
  (WaPOR, OpenET, MODIS ET); evaluate against eddy covariance / lysimeters.
- **Expected baselines:** FAO-56 single crop coefficient; existing ET products.

## A6 Breeding & genomics
- **GWAS:** mixed models with kinship + PCs (GEMMA, GAPIT/FarmCPU, MLMM); multiple-testing control.
- **Genomic prediction:** GBLUP, rrBLUP, Bayesian alphabet (BayesB/C), RKHS, ML/DL; G×E models
  (reaction norms, factor-analytic). CV schemes CV1/CV2/CV0/CV00 (new lines × new environments).
- **Expected baselines:** GBLUP; pedigree BLUP where available.

## A7 Plant protection
- **Risk models:** degree-day and infection models, species distribution models (MaxEnt, ensemble SDMs)
  with spatial-block CV; epidemic models (SIR-type, spatial spread).
- **Image diagnosis:** CNN/ViT with field-condition test sets; report per-class metrics and calibration.
- **Expected baselines:** published infection/degree-day models; ImageNet-pretrained CNN.

## A8–A9 Livestock, fisheries
- **Livestock:** mixed models on farm/sensor data; IPCC Tier 2 emission calculations; ML on accelerometer
  data with animal-level and farm-level splits.
- **Fisheries:** surplus-production and data-limited methods (catch-only, length-based), state-space models.

## A10 Economics & policy
- **Causal designs:** difference-in-differences (modern staggered estimators, e.g. Callaway–Sant'Anna,
  Sun–Abraham), synthetic control, instrumental variables, regression discontinuity, panel FE,
  matching + doubly robust estimators, causal forests for heterogeneity.
- **Structural / equilibrium:** partial/general equilibrium models, demand systems.
- **Expected:** event-study plots, placebo tests, pre-trend tests, robustness to specification.

## A11–A12 Food systems & sustainability
- **Accounting:** MFA, LCA (ISO 14040/44), input–output (MRIO), IPCC guidelines.
- **Scenario:** integrated assessment, land-use models; uncertainty via Monte Carlo / global
  sensitivity (Sobol, Morris).

## A13 Agricultural AI & software
- **Benchmarks:** fixed splits respecting dependence; multiple seeds; report variance; ablations.
- **Software quality of scientific models:** differential testing between implementations, metamorphic
  testing, regression tests, code review studies.

## Cross-cutting statistics
- Effect sizes + 95% CIs; bootstrap (cluster/block bootstrap when data are dependent).
- Multiple comparisons: Holm or Benjamini–Hochberg; pre-registered primary outcome.
- Model comparison on the same folds: paired tests (e.g. Diebold–Mariano for forecasts; Wilcoxon on
  per-fold metrics) with caution about fold dependence.
- Explainability: SHAP/permutation importance with correlated-feature caveats; never as causal evidence.
