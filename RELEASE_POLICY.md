# Zero-Tolerance Release Policy

A version of Q1 Research OS may be tagged and announced only when **every** item below holds, with the
evidence linked in the release notes. If any item is unknown, the release is blocked (fail-closed).

## Must pass (automated)

1. `python3 -m unittest discover -s tests` passes on the oldest and newest supported Python (CI job green).
2. `tests/test_controls.py::TestErrorMatrixIntegrity` passes: all 136 errors mapped; every control's
   function and named tests exist.
3. Mutation testing: neutralising any gate function makes the suite fail (no surviving mutants).
4. Original adversarial probes (fabricated DOI, rounded-away number, leaky split, inconsistent p-value,
   self-review, misquote, agent self-approval) are all caught.
5. Clean clone from GitHub installs with `./install.sh` and passes the suite.
6. No personal paths, e-mails or secrets in the repository.

## Must be stated (human)

7. Runtime evidence per agent surface (Claude Code, Antigravity, ...) with date and version, or an explicit
   "untested" label. Folder structure or metadata alone never counts as compatibility.
8. Residual-risk table from `docs/ERROR_CONTROL_MATRIX.md`; no claim of complete safety.
9. Any capability not demonstrated end to end (for example "90-95 % automation") is labelled
   **unverified** until a real study has measured it.

## Never

- Weakening a test, threshold or check to make a release pass.
- Calling a release "certified", "world-class" or "production-ready" while a critical issue, an untested
  claim or an unproven capability remains.
