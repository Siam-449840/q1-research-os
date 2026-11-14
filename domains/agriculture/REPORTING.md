# Reporting standards (choose in S2, complete in S7)

| Study type | Guideline | Where to get it |
|---|---|---|
| Prediction / ML models (yield, disease, risk) | **TRIPOD+AI** (2024) and/or **REFORMS** (ML-based science) | https://www.tripod-statement.org/ ; https://reforms.cs.princeton.edu/ |
| Observational studies (surveys, panels, census data) | **STROBE** (+ **RECORD** for routinely collected data) | https://www.strobe-statement.org/ ; https://www.record-statement.org/ |
| Systematic reviews / meta-analyses | **PRISMA 2020** (+ PRISMA-S for searches) | https://www.prisma-statement.org/ |
| Plant phenotyping data | **MIAPPE** | https://www.miappe.org/ |
| Agent-based / individual-based models | **ODD protocol** | Grimm et al. (ODD protocol updates); verify the current version |
| Economic evaluations | **CHEERS 2022** | https://www.equator-network.org/ |
| Life-cycle assessment | **ISO 14040/14044** reporting elements | ISO |
| Geospatial data / maps | ISO 19115 metadata; area-adjusted accuracy assessment good practice | ISO; remote sensing literature |
| Any study | **FAIR** data principles; journal data & code policies | https://www.go-fair.org/fair-principles/ |

The EQUATOR Network (https://www.equator-network.org/) indexes most health-adjacent guidelines; use it
to find the current version of each checklist.

## Minimum reporting items for any computational agriculture paper

- Data: sources, versions, access dates, licenses, spatial/temporal coverage, units, preprocessing.
- Study area map with coordinates/projection.
- Unit of analysis and sample size at each stage (flow diagram if records are excluded).
- Model specification, hyperparameter search space and budget, seeds, software versions, hardware.
- Validation design with justification for the split strategy.
- Metrics with uncertainty; baseline results under identical conditions.
- Robustness, sensitivity and ablation results (supplement is fine).
- Deviations from the protocol.
- Code and data availability with archive DOI.
