# Contributing

Thank you for helping make AI-assisted research more rigorous.

## Most valuable contributions

1. **Domain packs** (`domains/<field>/`, copied from `_template`): real, checkable dataset URLs;
   standard methods and expected baselines; reviewer-known pitfalls with controls; reporting
   guidelines; venue map **without** quartile claims.
2. **New or sharper gate checks** in `bin/rosctl.py`, each with a behavioural test in
   `tests/test_rosctl.py` named `test_<behaviour>_<why it matters>`.
3. **Worked examples** in `examples/<name>/PROPOSAL.md` that pass `rosctl lint-proposal` and contain no
   unverified citations or statistics.
4. **Stage playbook improvements** in `skills/q1-pipeline/stages/` based on real reviewer feedback.

## Rules

- `rosctl` stays **stdlib-only** and supports Python ≥ 3.9.
- Run `python3 -m unittest discover -s tests` before opening a pull request.
- Never weaken a check to make a project pass; open an issue explaining the false positive instead.
- No fabricated facts in docs: every dataset URL, guideline and tool name must be real; if unsure, leave it out.
- Conventional commits (`feat:`, `fix:`, `docs:`, `test:` …).

## Reporting problems

Open an issue with the `rosctl` version (`rosctl --version`), the command, and the full output.
