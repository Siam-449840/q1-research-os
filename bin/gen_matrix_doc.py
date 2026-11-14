#!/usr/bin/env python3
"""Render core/ERROR_CONTROLS.csv + core/CONTROLS.csv into docs/ERROR_CONTROL_MATRIX.md (stdlib only).

Run after editing either CSV: python3 bin/gen_matrix_doc.py
"""

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    controls = {r["control_id"]: r for r in csv.DictReader((ROOT / "core/CONTROLS.csv").open(encoding="utf-8"))}
    errors = list(csv.DictReader((ROOT / "core/ERROR_CONTROLS.csv").open(encoding="utf-8")))
    enf = Counter(e["enforcement"] for e in errors)
    risk = Counter(e["residual_risk"] for e in errors)
    lines = [
        "# 136-Error Control Matrix",
        "",
        "Generated from `core/ERROR_CONTROLS.csv` and `core/CONTROLS.csv` by `bin/gen_matrix_doc.py`. "
        "`tests/test_controls.py` fails if any error lacks a control, or a control names a function or test that does not exist.",
        "",
        "- **C** controls are code: fail-closed `rosctl` gates (blockers stop the pipeline).",
        "- **H** controls are mandatory human checks: `rosctl approve` will not record an approval until the owner confirms each item for that stage.",
        "- **Residual risk** is what remains *after* the controls, judged honestly. No control makes a risk zero.",
        "",
        f"Enforcement: {', '.join(f'{k}: {v}' for k, v in sorted(enf.items()))}. "
        f"Residual risk: {', '.join(f'{k}: {v}' for k, v in sorted(risk.items()))}.",
        "",
        "| # | Category | Error | Controls | Enforcement | Residual |",
        "|---|---|---|---|---|---|",
    ]
    for e in errors:
        lines.append(f"| {e['error_id']} | {e['category']} | {e['error']} | {e['controls'].replace(';', ', ')} | "
                     f"{e['enforcement']} | {e['residual_risk']} |")
    lines += ["", "## Control registry", "", "| ID | Kind | Stage | Implementation | What it enforces |", "|---|---|---|---|---|"]
    for cid, c in controls.items():
        lines.append(f"| {cid} | {c['kind']} | {c['stage']} | `{c['implementation']}` | {c['description']} |")
    (ROOT / "docs/ERROR_CONTROL_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote docs/ERROR_CONTROL_MATRIX.md ({len(errors)} errors, {len(controls)} controls)")


if __name__ == "__main__":
    main()
