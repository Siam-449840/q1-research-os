"""End-to-end: a toy study driven through every gate S0 -> S10, then fault injection.

Offline and stdlib-only. Results are genuinely computed by analysis scripts run via `rosctl run`;
references go through the real rosrefs.verify_bib path with an offline registry stand-in. Human
approvals are recorded with record_approval (the TTY prompt itself is covered in test_hardening).
The toy science is not a claim; the test proves the machinery accepts honest work and rejects faults.
"""

from __future__ import annotations

import json
import shutil
import sys
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hardening import fake_fetch  # noqa: E402
from test_rosctl import EXAMPLE, ProjectCase, quiet, rosctl  # noqa: E402

PROSE = ("This sentence documents a concrete decision with its reason, data source and expected effect "
         "so that an independent reader can audit the study without asking the authors. ")

ANALYSIS = r'''
import csv, json, random, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import rosstats

def fit(rows):
    n = len(rows); mx = sum(r[1] for r in rows) / n; my = sum(r[2] for r in rows) / n
    b = sum((r[1] - mx) * (r[2] - my) for r in rows) / sum((r[1] - mx) ** 2 for r in rows)
    return my - b * mx, b

def rmse(rows, a, b):
    return (sum((r[2] - a - b * r[1]) ** 2 for r in rows) / len(rows)) ** 0.5

rows = [(r["site"], float(r["x"]), float(r["y"])) for r in csv.DictReader(open("data/raw/d1/plots.csv"))]
sites = sorted({r[0] for r in rows})
random.seed(20261114)
shuffled = rows[:]; random.shuffle(shuffled)  # ros: allow-random shuffling for the random K-fold comparison arm
rand_folds = [shuffled[i::5] for i in range(5)]
split_rows, grp, rnd = [], [], []
for k, site in enumerate(sites, 1):
    test = [r for r in rows if r[0] == site]; train = [r for r in rows if r[0] != site]
    grp.append(rmse(test, *fit(train)))
    split_rows += [(k, "train", s) for s in sorted({r[0] for r in train})] + [(k, "test", site)]
for k in range(5):
    test = rand_folds[k]; train = [r for j, f in enumerate(rand_folds) if j != k for r in f]
    rnd.append(rmse(test, *fit(train)))
d = [g - r for g, r in zip(grp, rnd)]
mean = sum(d) / 5; sd = (sum((x - mean) ** 2 for x in d) / 4) ** 0.5; t = mean / (sd / 5 ** 0.5)
out = {"random_cv_rmse": sum(rnd) / 5, "group_cv_rmse": sum(grp) / 5, "t": t, "df": 4,
       "p": rosstats.p_value("t", t, 4, None), "fold_diff": d}
Path("results").mkdir(exist_ok=True); Path("results/splits").mkdir(exist_ok=True)
json.dump(out, open("results/metrics.json", "w"), indent=2)
with open("results/splits/leave_site_out.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["fold", "split", "group"]); w.writerows(split_rows)
'''

RECOMPUTE = r'''
import csv, json
rows = [(float(r["x"]), float(r["y"]), r["site"]) for r in csv.DictReader(open("data/raw/d1/plots.csv"))]
def solve(train):  # normal equations via 2x2 Cramer's rule: a different algorithm from the primary fit
    n = len(train); sx = sum(x for x, _, _ in train); sy = sum(y for _, y, _ in train)
    sxx = sum(x * x for x, _, _ in train); sxy = sum(x * y for x, y, _ in train)
    det = n * sxx - sx * sx
    return (sy * sxx - sx * sxy) / det, (n * sxy - sx * sy) / det
errs = []
for site in sorted({s for _, _, s in rows}):
    a, b = solve([r for r in rows if r[2] != site]); test = [r for r in rows if r[2] == site]
    errs.append((sum((y - a - b * x) ** 2 for x, y, _ in test) / len(test)) ** 0.5)
primary = json.load(open("results/metrics.json"))["group_cv_rmse"]
with open("ledgers/RECOMPUTATION_AUDIT.csv", "a", newline="") as fh:
    csv.writer(fh).writerow(["s1", "H1", "leave-site-out RMSE", primary, "closed-form OLS (analysis/model.py)",
                             sum(errs) / len(errs), "Cramer normal equations (analysis/recompute.py)", 1e-9, "", "match"])
'''

SPLIT_TEST = '''
import csv, unittest
class TestSplits(unittest.TestCase):
    def test_no_site_in_train_and_test_of_same_fold(self):
        seen = {}
        for r in csv.DictReader(open("results/splits/leave_site_out.csv")):
            seen.setdefault((r["fold"], r["split"]), set()).add(r["group"])
        for (fold, split), groups in seen.items():
            if split == "test":
                self.assertFalse(groups & seen.get((fold, "train"), set()))
'''

FIGURE = '''
import json
m = json.load(open("results/metrics.json"))
h1, h2 = 200 * m["random_cv_rmse"], 200 * m["group_cv_rmse"]
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="320"><rect x="60" y="{300-h1}" width="60" '
       f'height="{h1}" fill="#0072B2"/><rect x="180" y="{300-h2}" width="60" height="{h2}" fill="#E69F00"/></svg>')
open("manuscript/figures/fig1_cv_gap.svg", "w").write(svg)
'''


class TestEndToEnd(ProjectCase):
    def gate(self, stage):
        code, out = quiet(rosctl.main, ["gate", stage])
        return code, out

    def assert_gate(self, stage):
        code, out = self.gate(stage)
        self.assertEqual(code, 0, f"{stage} should pass:\n{out}")

    def approve(self, stage):
        code, out = self.gate(stage)
        self.assertEqual(code, 1)
        self.assertIn(f"rosctl approve {stage}", out)
        rosctl.record_approval(self.proj, rosctl.load_state(self.proj), stage, "e2e",
                               checklist=rosctl.human_controls(self.proj, stage))
        self.assert_gate(stage)

    def run_logged(self, *cmd):
        code, out = quiet(rosctl.main, ["run", "--", sys.executable, *cmd])
        self.assertEqual(code, 0, out)

    # ---------------------------------------------------------------- stages
    def s1_literature(self):
        self.write("literature/SEARCH_PROTOCOL.md", "# Search protocol\n\n" + PROSE * 6)
        purposes = ["main", "counter-evidence", "grey/regional"] + ["main"] * 9
        for i in range(12):
            self.write(f"literature/search_raw/q{i}.json", json.dumps({"total": 30 + i, "papers": []}))
        self.write("ledgers/SEARCH_LOG.csv", "date,source,query,filters,purpose,hits,screened,included,raw_output,notes\n" + "".join(
            f"2026-11-14,{src},q{i},2015-2026,{purposes[i]},{30 + i},{10 + i},2,literature/search_raw/q{i}.json,\n"
            for i, src in enumerate(["openalex", "crossref", "semantic"] * 4)))
        keys = [f"work{i:02d}" for i in range(10)]
        self.write("refs/refs.bib", "".join(f"@article{{{k},\n title={{Title of {k}}},\n doi={{10.5555/{k}}},\n year={{2020}}\n}}\n" for k in keys))
        self.write("literature/CLOSEST_WORK.csv",
                   "citekey,title,year,doi_or_url,what_they_did,data,method,key_result,limitation,overlap_with_us,evidence_location\n"
                   + "".join(f"{k},Title of {k},2020,10.5555/{k},x,d,m,r,l,{'partial' if i < 3 else 'none'},p. 2\n" for i, k in enumerate(keys)))
        registry = {f"doi.org/10.5555/{k}": (200, json.dumps({"title": f"Title of {k}", "issued": {"date-parts": [[2020]]}})) for k in keys}
        registry["openalex"] = (200, '{"is_retracted": false}')
        rows = rosctl.rosrefs.verify_bib(rosctl.parse_bib(self.proj / "refs/refs.bib"), fetch=fake_fetch(registry), pause_s=0)
        rosctl.rosrefs.write_ledger(self.proj, rows)
        self.write("literature/NOVELTY_VERDICT.md", "# Novelty verdict\n\nRecommendation: proceed.\n\n" + PROSE * 8
                   + "\n## Contrary evidence\n\n" + PROSE + "\n## Search limitations\n\n" + PROSE)

    def s2_protocol(self):
        sections = ["Research Questions", "Hypotheses", "Data", "Variables", "Primary Analysis", "Validation Strategy",
                    "Robustness and Sensitivity", "Multiple Comparisons and Uncertainty", "Stopping Rules", "Success Criteria"]
        body = "# Protocol\n\n" + "".join(f"## {i}. {s}\n\n{PROSE * 2}\n\n" for i, s in enumerate(sections, 1))
        body = body.replace("## 2. Hypotheses\n\n", "## 2. Hypotheses\n\nH1: leave-site-out RMSE exceeds random-CV RMSE. "
                                                    "Decision rule: supported if the paired t-test on fold differences gives p below alpha. "
                                                    "Normality of the fold differences is checked first. Pre-registered analyses: A1 leave-site-out OLS RMSE; "
                                                    "A2 random five-fold comparison arm.\n\n")
        self.write("protocol/PROTOCOL.md", body + "## 11. Deviations\n\nNone yet.\n")

    def s3_data(self):
        import random
        random.seed(7)
        lines = ["site,x,y"] + [f"S{s},{x:.3f},{2 * x + 1.5 * s + random.gauss(0, 1):.3f}"
                                for s in range(1, 6) for x in [random.uniform(0, 10) for _ in range(20)]]
        f = self.write("data/raw/d1/plots.csv", "\n".join(lines) + "\n")
        self.write("ledgers/DATA_PROVENANCE.csv", "dataset_id,name,source_url,version_or_access_date,license,path,sha256,size_bytes,notes\n"
                   f"D1,plots,https://example.org/plots,2026-11-14,CC-BY-4.0,data/raw/d1/plots.csv,{rosctl.sha256_file(f)},{f.stat().st_size},\n")
        self.write("data/DATA_CARD.md", "# Data card\n\n" + PROSE * 9)
        self.write("data/SCHEMA.csv", "file,column,type,unit,min,max,date_format,coded_numeric,notes\n"
                   "data/raw/d1/plots.csv,site,categorical,,,,,no,\n"
                   "data/raw/d1/plots.csv,x,continuous,dS/m,0,10,,,\n"
                   "data/raw/d1/plots.csv,y,continuous,t/ha,-20,60,,,\n")
        self.write("requirements.txt", "# standard library only; no third-party packages\n")

    def s4_analysis(self):
        self.write("analysis/model.py", ANALYSIS)
        self.write("analysis/tests/test_splits.py", SPLIT_TEST)
        self.run_logged("analysis/model.py", str(rosctl.FRAMEWORK_ROOT / "bin"))
        self.run_logged("-m", "unittest", "discover", "-s", "analysis/tests")

    def s5_recompute(self):
        self.write("analysis/recompute.py", RECOMPUTE)
        self.run_logged("analysis/recompute.py")

    def s6_figures(self):
        self.write("analysis/fig1.py", FIGURE)
        self.run_logged("analysis/fig1.py")
        self.write("ledgers/FIGURE_MANIFEST.csv", "figure_file,script,data_inputs,message,colorblind_safe,dpi,error_bars\n"
                   "manuscript/figures/fig1_cv_gap.svg,analysis/fig1.py,results/metrics.json,validation gap,yes,,none\n")

    def s7_manuscript(self):
        m = json.loads((self.proj / "results/metrics.json").read_text())
        vals = {"random_cv_rmse": f"{m['random_cv_rmse']:.3f}", "group_cv_rmse": f"{m['group_cv_rmse']:.3f}",
                "t": f"{m['t']:.2f}", "p": f"{m['p']:.3f}"}
        text = textwrap.dedent(f"""\
            # Leave-site-out validation of a toy yield model
            ## Abstract
            Random cross-validation gave RMSE {vals['random_cv_rmse']} whereas leave-site-out gave {vals['group_cv_rmse']} [Source: results/metrics.json].
            ## 1. Introduction
            Spatial structure biases random validation [@work00].
            ## 2. Methods
            Ordinary least squares with leave-site-out and random five-fold validation, seed `20261114`.
            ## 3. Results
            Leave-site-out RMSE was {vals['group_cv_rmse']} versus {vals['random_cv_rmse']}, t(4) = {vals['t']}, p = {vals['p']}.
            We evaluated H1 with the pre-registered paired test.
            ## 4. Discussion
            The gap is consistent with prior reports [@work01].
            ### 4.1 Limitations
            {PROSE * 5}
            ## 5. Conclusion
            Validation design matters.
            ## Data Availability
            Synthetic data are generated by the test.
            ## Code Availability
            All scripts are in analysis/.
            ## Declaration of Generative AI Use
            Claude Code drafted this text; the authors verified it.
            ## References
            """)
        self.write("manuscript/manuscript.md", text)
        self.write("ledgers/PROTOCOL_EXECUTION.csv", "analysis_id,description,status,results_file,locator,notes\n"
                   "A1,leave-site-out OLS RMSE,done,results/metrics.json,$.group_cv_rmse,\n"
                   "A2,random five-fold arm,done,results/metrics.json,$.random_cv_rmse,\n")
        self.write("ledgers/NUMBER_PROVENANCE.csv", "number_id,value,manuscript_location,results_file,locator,script,notes\n"
                   + "".join(f"{k},{v},Results,results/metrics.json,$.{k},analysis/model.py,\n" for k, v in vals.items()))
        self.write("ledgers/CLAIM_SUPPORT.csv", "claim_id,manuscript_location,claim_text,citekey,evidence_location,evidence_quote,support_level,checked_by\n"
                   'c1,Intro,bias,work00,p. 2,"random splits were optimistic",supports,agent\n'
                   'c2,Discussion,gap,work01,p. 5,"spatial gap observed",supports,agent\n')
        self.write("literature/text/work00.txt", "ACCESS: full-text\nWe found that random splits were optimistic for clustered plots.")
        self.write("literature/text/work01.txt", "ACCESS: abstract-only\nA spatial gap observed across regions.")
        self.write("ledgers/AI_USAGE_LOG.csv", "timestamp_utc,tool,model,model_version,purpose,prompt_ref,output_ref,notes\n"
                   "2026-11-14T00:00:00Z,Claude Code,claude-opus-5-5,2026-11,drafting manuscript,prompts/p1.md,manuscript/manuscript.md,\n")
        return vals

    def s8_review(self):
        for role in rosctl.REVIEW_ROLES:
            who = "human: owner" if role == "editor" else "gemini-3-pro"
            self.write(f"review/REVIEW_{role}_v1.md", f"# {role} review\nReviewer: {who}\n\n" + PROSE * 8)
        self.write("review/Q1_SCORECARD.csv", "dimension,score,evidence,reviewer\n" +
                   "".join(f"{d},4,see REVIEW files,reviewer-{d[:3]}\n" for d in rosctl.RUBRIC_DIMENSIONS))
        self.write("review/ISSUES.csv", "issue_id,reviewer,severity,location,issue,action,status,resolution_note\n"
                   "I1,methods,major,Sec 3,no uncertainty,added t-test,resolved,done\n")

    def s9_submission(self):
        self.write("submission/COVER_LETTER.md", "Dear Editor,\n\n" + PROSE * 8)
        self.write("submission/SUBMISSION_CHECKLIST.md", "# Checklist\n\n- [x] scope fit confirmed with three recent articles\n"
                   "- [x] owner verified quartile on SCImago and recorded the source\n- [x] all statements present\n")
        self.write("submission/JOURNAL_CHECK.csv", "journal,publisher,issn,quartile,quartile_source,checked_date,scope_fit,apc_or_route,ai_policy_url,owner_verified\n"
                   "Journal X,Pub,0000-0000,Q1,SJR 2025,2026-11-14,yes,subscription,https://example.org,yes\n")
        self.write("submission/GUIDE_FOR_AUTHORS.txt", "Guide for authors downloaded by the owner. " * 40)

    # ---------------------------------------------------------------- the test
    def test_full_pipeline_s0_to_s10_then_fault_injection(self):
        self.write("PROPOSAL.md", EXAMPLE.read_text())
        self.assert_gate("S0")
        self.s1_literature(); self.approve("S1")
        self.s2_protocol(); self.approve("S2")
        self.s3_data(); self.assert_gate("S3")
        self.s4_analysis(); self.assert_gate("S4")
        self.s5_recompute(); self.assert_gate("S5")
        self.s6_figures(); self.assert_gate("S6")
        vals = self.s7_manuscript(); self.assert_gate("S7")
        self.assertEqual(rosctl.check_stats(self.proj).warnings, [])  # the t-test was found and recomputed
        self.assertFalse(any("unverifiable" in w and "work00" in w for w in rosctl.check_citations(self.proj).warnings))
        self.s8_review(); self.approve("S8")
        self.s9_submission(); self.approve("S9")
        self.write("review/RESPONSE_TO_REVIEWERS.md", "**Comment R1.1:** add uncertainty\n**Response:** Added; see Results.\n"
                   "**Change:** Results now state \"Leave-site-out RMSE was\" with the paired test.\n\n" + PROSE * 3)
        self.assert_gate("S10")
        code, out = quiet(rosctl.main, ["status"])
        self.assertIn("Current stage: DONE", out)

        ms = self.proj / "manuscript/manuscript.md"
        good = ms.read_text()
        ms.write_text(good.replace(f"was {vals['group_cv_rmse']}", "was 0.111"))  # fabricated number
        code, out = self.gate("S7")
        self.assertEqual(code, 1); self.assertIn("0.111", out)
        ms.write_text(good)

        raw = self.proj / "data/raw/d1/plots.csv"
        original = raw.read_text()
        raw.write_text(original.replace("S1,", "S9,", 1))  # tampered raw data
        code, out = self.gate("S7")
        self.assertEqual(code, 1); self.assertIn("sha256 mismatch", out)
        raw.write_text(original)

        proto = self.proj / "protocol/PROTOCOL.md"
        frozen = proto.read_text()
        proto.write_text(frozen.replace("p below alpha", "p below 0.10"))  # moved goalposts after freeze
        code, out = self.gate("S7")
        self.assertEqual(code, 1); self.assertIn("changed after freeze", out)
        self.assertNotIn("S8", rosctl.load_state(self.proj)["passed"])  # later passes invalidated
        proto.write_text(frozen)
        self.assert_gate("S7")

        metrics = self.proj / "results/metrics.json"
        honest = metrics.read_text()
        metrics.write_text(honest.replace('"df": 4', '"df": 40'))  # hand-edited result file
        code, out = self.gate("S7")
        self.assertEqual(code, 1); self.assertIn("not produced by a logged", out)
        metrics.write_text(honest)

        ms.write_text(good.replace("Validation design matters.", "These results prove that validation design matters."))
        code, out = self.gate("S7")  # misreporting language must fail the gate itself, not only the linter
        self.assertEqual(code, 1); self.assertIn("[E41]", out)
        ms.write_text(good)

        locked = self.proj / "analysis/tests/test_splits.py"
        original_test = locked.read_text()
        locked.write_text("import unittest\n")  # test gutted after the lock
        code, out = self.gate("S7")
        self.assertEqual(code, 1); self.assertIn("after the S4 test lock", out)
        locked.write_text(original_test)
        self.assert_gate("S7")


if __name__ == "__main__":
    unittest.main()
