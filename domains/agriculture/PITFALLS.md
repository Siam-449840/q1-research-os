# Pitfalls Q1 reviewers in agriculture look for

Each item: the trap → how a reviewer detects it → the control to put in the protocol.

## Leakage and optimistic validation
1. **Spatial autocorrelation leakage:** random K-fold on gridded/field data puts neighbours in train and
   test → reviewer asks for spatial CV → use spatial block CV, buffered leave-location-out, or
   leave-region-out; report the gap between random and spatial CV.
2. **Temporal leakage:** using the same season's later data, or random splits across years → use
   leave-one-year-out or forward-chaining; features only from information available at prediction time.
3. **Group leakage:** same farm/plot/animal/genotype family in train and test → group K-fold.
4. **Preprocessing leakage:** scaling, imputation, feature selection or PCA fitted on all data → fit
   inside each training fold (pipelines).
5. **Target leakage in features:** e.g. using end-of-season NDVI to "forecast" yield mid-season; using
   variables derived from the target (yield-based zones).
6. **Hyperparameter tuning on the test set:** nested CV or a separate validation split.
7. **Lab-to-field gap:** models trained on lab images (uniform background, single leaf) collapse in
   the field → test on independent field images; report the drop.

## Design and inference
8. **Technology trend confounding:** yields rise over time for non-climate reasons → detrend (linear,
   piecewise, or LOESS) or include trend terms before attributing to weather.
9. **Ecological fallacy:** district statistics used for farm-level claims → match claim to unit.
10. **MAUP:** results change with aggregation level → test sensitivity to spatial units.
11. **Pseudo-replication:** treating repeated measures or pixels as independent samples → mixed models,
    cluster-robust SEs, effective sample size.
12. **Selection bias in surveys/trials:** adopters differ from non-adopters → causal design or bounds;
    discuss direction of bias.
13. **Endogenous management:** farmers adapt to expected weather → IV or panel designs, discuss.
14. **Causal language from correlations or SHAP values:** "X drives yield" → "X is associated with".
15. **Multiplicity:** many crops × regions × indices tested → correction and pre-registration.
16. **Reporting-unit and statistics quality:** official yields may be modelled, revised or politically
    affected → triangulate with independent sources; sensitivity analysis.

## Remote sensing specifics
17. Cloud contamination and gap-filling artefacts; mixed pixels in smallholder landscapes (field size
    < pixel size); crop masks with their own errors propagated; sensor changes across time
    (Landsat 5/7/8/9, MODIS collection changes); map accuracy reported without area-adjusted estimation.

## Crop-model specifics
18. Calibrating and evaluating on the same data; equifinality (many parameter sets fit equally);
    unreported default parameters; comparing models with non-equivalent inputs.

## Genomics specifics
19. Population structure inflating GWAS hits; CV that ignores family structure; reporting accuracy
    without the CV scheme (CV1/CV2/CV0/CV00).

## Climate-projection specifics
20. Single GCM; no bias correction; ignoring CO₂ fertilisation or adaptation assumptions; presenting
    ensemble mean without spread.

## Machine-learning hygiene
21. One random seed; no variance across runs; untuned baselines; benchmark contamination; class
    imbalance hidden by accuracy (use balanced metrics, per-class results, calibration).
