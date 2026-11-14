# Research Proposal: When can satellite-and-weather rice yield models be trusted outside the region they were trained in? A leave-zone-out study in Bangladesh

> Worked example for Q1 Research OS. It passes `rosctl lint-proposal`. It contains **no citations or
> statistics on purpose**: in the real pipeline these are found and verified in S1, never written from memory.

## 0. Metadata

- **Working title:** Random cross-validation overstates the transferability of satellite-and-weather rice yield models: evidence from agro-ecological zones in Bangladesh
- **Discipline / subfield:** Agriculture / Remote sensing and crop yield estimation (A3, with A1 and A2)
- **Domain pack:** agriculture
- **Research type:** computational, secondary data (satellite, reanalysis, official statistics)
- **Target journals (ranked):**
  1. Field Crops Research: publishes yield-estimation and transferability studies with agronomic interpretation
  2. Computers and Electronics in Agriculture: strong fit for ML validation methodology in agriculture
  3. European Journal of Agronomy: accepts modelling studies with clear agronomic relevance
- **Article type and limits:** Research article, about 8,000 words, abstract up to 250 words (to confirm in S9)
- **Owner(s):** first author (agriculture background), supervisor as senior author
- **Communication language (agent → owner):** বাংলা for explanations, English for the manuscript
- **Deadline / time budget:** 12 weeks, about 15 hours per week

## 1. Contribution Statement

We quantify how much random cross-validation overstates the accuracy of satellite-and-weather rice
yield models in Bangladesh, and test whether transfer error across agro-ecological zones can be
predicted from environmental dissimilarity, giving model users a practical rule for when such models
can be trusted.

## 2. Problem and Significance

District-level rice yield estimates guide food-security monitoring, import decisions and crop
insurance design in Bangladesh, where Boro (dry-season, irrigated) rice is the largest harvest. Many
published yield models combine satellite vegetation indices with weather data and report high accuracy,
but most evaluate with random splits of district-years. Neighbouring districts and the same district in
other years share climate, soils and management, so random splits let the model see near-copies of the
test data. If these models are then used in zones or years unlike their training data, users may trust
estimates that are much worse than reported. Agencies and insurers need to know (a) how large this
optimism is and (b) whether they can detect, before deployment, where a model will fail. S1 will
quantify how common random-split evaluation is in the published literature and the policy uses of
district yield estimates, with verified citations.

## 3. State of Knowledge and Gap

Established: satellite vegetation indices and seasonal weather explain a substantial part of
inter-annual yield variation in irrigated rice systems; machine-learning models (random forest,
gradient boosting) often outperform linear regression on such data. Contested: how well such models
generalise across space and time; studies in other regions report sharp accuracy drops under spatial
or temporal hold-out, but evidence for South Asian smallholder rice systems is limited. Missing: a
systematic comparison of random, leave-year-out and leave-zone-out validation for the same models and
data in Bangladesh, and a test of whether environmental dissimilarity (for example an area-of-
applicability style dissimilarity index) predicts where transfer fails. Gap types: evidence gap and
transferability gap. Checkable gap statement for S1: "No study has compared random, leave-year-out
and leave-zone-out validation of satellite-and-weather rice yield models across Bangladesh's
agro-ecological zones and tested dissimilarity as a predictor of transfer error."

## 4. Research Questions and Hypotheses

**RQ1:** How much does random cross-validation overstate yield-model accuracy compared with
leave-one-zone-out and leave-one-year-out validation?

- **H1:** Leave-one-zone-out RMSE is substantially higher than random-split RMSE for the same models.
  - **Rival explanation:** the difference is caused by smaller training sets in leave-zone-out folds, not by distribution shift.
  - **Discriminating prediction:** the gap remains when random-split training sets are subsampled to the same size as leave-zone-out training sets.
  - **Measurement:** RMSE of detrended district Boro yield (t/ha) per fold, for each learner, under three split designs.
  - **Decision rule:** H1 is supported if the 95% zone-block bootstrap CI of the size-matched relative RMSE gap excludes 0 and its median is at least 15%.
  - **Smallest effect size of interest:** a 10% relative increase in RMSE, which would change how much decision makers should trust the model.

**RQ2:** Can transfer error be predicted from how different a test zone is from the training data?

- **H2:** Zone-level transfer error increases with environmental dissimilarity between the test zone and the training zones.
  - **Rival explanation:** larger errors reflect noisier official statistics in some zones rather than dissimilarity.
  - **Discriminating prediction:** the association holds after controlling for each zone's residual variance under a trend-only model (a proxy for reporting noise).
  - **Measurement:** Spearman correlation and partial rank correlation between the dissimilarity index and zone RMSE.
  - **Decision rule:** H2 is supported if the partial Spearman correlation is at least 0.4 and its 95% bootstrap CI excludes 0.
  - **Smallest effect size of interest:** a correlation of 0.3, below which dissimilarity would not be useful for screening.

## 5. Data Sources

| ID | Dataset | URL | Version / date | License | Coverage (space, time) | Unit | Known issues | Access status |
|---|---|---|---|---|---|---|---|---|
| D1 | BBS district Boro rice area, production and yield | https://bbs.gov.bd/ | Yearbooks of Agricultural Statistics, years to be fixed in S3 | Government publication; terms to be recorded in S3 | 64 districts, about 2001 onward | district-year | district boundary changes, possible revisions, some values may be modelled | published PDFs; tables must be digitised and double-entered |
| D2 | MODIS MOD13Q1 NDVI/EVI | https://lpdaac.usgs.gov/ | Collection 6.1, accessed in S3 | NASA open data policy, recorded in S3 | Bangladesh, 2001 onward, 250 m, 16-day | pixel to district aggregate | cloud contamination in monsoon, mixed pixels | API / Google Earth Engine |
| D3 | CHIRPS daily rainfall | https://www.chc.ucsb.edu/data/chirps | v2.0, accessed in S3 | as stated by provider, recorded in S3 | 0.05 degree, 1981 onward | grid to district | gauge density varies | direct download |
| D4 | NASA POWER daily temperature and radiation | https://power.larc.nasa.gov/ | API version in S3 | NASA open data, recorded in S3 | 0.5 degree, 1981 onward | grid to district | coarse resolution | REST API, tested |
| D5 | SoilGrids soil properties | https://soilgrids.org/ | 2.0 | stated by ISRIC, recorded in S3 | 250 m global | grid to district | prediction uncertainty in floodplains | WCS download |
| D6 | Agro-ecological zone boundaries of Bangladesh | source to be confirmed in S1/S3 | to be confirmed | to be confirmed | 30 zones | polygon | must find an openly licensed digital version | not yet accessed (risk) |

## 6. Methods and Validation

- **Primary analysis:** gradient boosting (LightGBM) and random forest predicting detrended district Boro yield from seasonal composites of NDVI/EVI (D2), cumulative rainfall (D3), growing degree days, extreme-heat degree days and radiation (D4), and static soil covariates (D5). Yields are detrended per district with a linear trend fitted only on training years within each fold.
- **Baselines:** (1) trend-only model (district trend extrapolation); (2) linear mixed model with weather covariates and district random intercepts; (3) the common published practice: random forest evaluated with random K-fold, reproduced exactly as reported in the closest work found in S1.
- **Validation strategy:** for every learner, compare random 10-fold cross-validation, leave-one-year-out, and leave-one-zone-out cross-validation (zones from D6, or physiographic divisions if D6 is unavailable, recorded as a deviation). Hyperparameters are tuned with nested cross-validation inside each outer training fold using the same split type.
- **Uncertainty:** zone-block bootstrap (2,000 resamples) for RMSE gaps and correlations; repeat each model with 5 seeds.
- **Robustness and sensitivity:** alternative detrending (none, quadratic); alternative zone definitions; feature ablations (weather only, satellite only); a different dissimilarity metric; excluding districts with boundary changes.
- **Multiplicity:** two confirmatory hypotheses; Holm correction across them; all other analyses labelled exploratory.
- **Software and compute:** Python 3.12 with uv-locked environment; laptop with 16 GB RAM; Earth Engine for satellite aggregation (free research tier).

## 7. Expected Results and Planned Figures

- **Fig. 1:** map of districts and agro-ecological zones with data coverage, showing where training and test data come from.
- **Fig. 2:** RMSE under random, leave-year-out and leave-zone-out validation for each learner with bootstrap CIs; the optimism gap is the main message.
- **Fig. 3:** zone transfer error against environmental dissimilarity, with partial correlation after controlling for reporting noise.
- **Fig. 4:** stability of feature importance across zones, showing which relationships do and do not transfer.
- **Fig. 5:** map of the area of applicability: where the model can and cannot be trusted.
- **If hypotheses fail:** if the gap is small, the paper reports that these models transfer well across Bangladesh's zones, which is useful evidence for agencies; if dissimilarity does not predict error, the paper documents that screening by dissimilarity is unreliable and analyses what does explain failure.

## 8. Threats to Validity

- Construct: official yields may contain modelled or revised values; mitigation: triangulate with FAOSTAT national totals and run sensitivity excluding suspicious district-years.
- Internal: district boundary changes create artificial breaks; mitigation: harmonise to a fixed boundary set and test exclusion.
- External: results for Boro rice in Bangladesh may not hold for rain-fed rice or other countries; mitigation: state scope and test on Aman season as exploratory transfer.
- Conclusion: few zones limit statistical power for H2; mitigation: report CIs, smallest effect of interest and power by simulation.

## 9. Ethics, Licensing and Data Sharing

No human subjects or personal data. All datasets are public; each license is recorded in S3 and
determines what can be redistributed. Code will be released under the MIT license; processed
district-level features will be shared if licenses allow, otherwise download scripts will be shared.
The archive will receive a Zenodo DOI. Generative AI use will be declared as required by the journal.

## 10. Definition of Done

All rosctl gates S0 to S9 pass; both hypotheses evaluated exactly as pre-registered; every figure
regenerated by one command from raw data; manuscript within the journal limit; reproducibility archive
ready for the owner to upload.

## 11. Constraints and Resources

Zero budget: no paid APIs or software. Laptop with 16 GB RAM and about 40 GB free disk; ask before any
download larger than 5 GB. Earth Engine free research access. No proprietary yield data. University
library access for paywalled papers (owner fetches them).

## 12. Decisions Reserved for the Owner

- Changing the primary outcome, the split designs or the hypotheses.
- Replacing the agro-ecological zone map with another zoning.
- Any download larger than 5 GB, and any paid service.
- The final target journal and the author list.
