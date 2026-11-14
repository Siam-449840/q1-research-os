# Pitfalls (empirical SE)

1. **Time-travel leakage:** using future commits/releases to predict past events → time-aware splits.
2. **Toy or cherry-picked subjects** → justified, reproducible sampling; diverse projects; report the frame.
3. **Forks, bots and mirrors** inflating counts → filter and report the filters.
4. **Ignoring project clustering:** commits within projects are not independent → mixed models, per-project analysis.
5. **Construct validity:** e.g. "bug-fix commit" identified by keywords → validate the heuristic on a labelled sample, report precision/recall.
6. **Single-run randomised algorithms** (fuzzers, search, LLMs) → repeated runs + statistics.
7. **LLM benchmark contamination and moving model versions** → pin versions, date, contamination analysis.
8. **Tool comparison unfairness:** default settings for competitors vs tuned own tool.
9. **Unit tests ≠ scientific validity:** for research software, passing tests does not show the science is right; use differential/metamorphic testing against references.
10. **Ethics:** personal data of developers; mass contacting maintainers; responsible disclosure for vulnerabilities (the owner decides and sends).
