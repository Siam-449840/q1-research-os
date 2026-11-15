"""Adversarial (red-team) tests: an honest project passes S7, then one cheat at a time must be blocked by the check
meant for it. Each attack is a shortcut a lazy or hallucinating agent could take; the message proves which check fired.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_e2e import EXAMPLE, TestEndToEnd, quiet, rosctl  # noqa: E402

ROW = "Leave-site-out RMSE was"


class TestRedTeam(TestEndToEnd):
    def setUp(self):
        super().setUp()
        self.write("PROPOSAL.md", EXAMPLE.read_text())
        self.s1_literature(); self.approve("S1")
        self.s2_protocol(); self.approve("S2")
        self.s3_data(); self.s4_analysis(); self.s5_recompute(); self.s6_figures()
        self.vals = self.s7_manuscript()
        self.assert_gate("S7")
        self.ms = self.proj / "manuscript/manuscript.md"
        self.good = self.ms.read_text()

    def test_full_pipeline_s0_to_s10_then_fault_injection(self):
        """Inherited e2e test; already covered by test_e2e, skipped here to avoid running it twice."""

    def assert_blocked(self, expected, stage="S7"):
        code, out = quiet(rosctl.main, ["gate", stage])
        self.assertEqual(code, 1, f"cheat passed the {stage} gate")
        self.assertIn(expected, out)

    def say(self, sentence):
        self.ms.write_text(self.good.replace("Validation design matters.", sentence))

    def test_result_hidden_in_code_span_is_blocked(self):
        self.ms.write_text(self.good.replace(f"{ROW} {self.vals['group_cv_rmse']}", f"{ROW} `0.999`"))
        self.assert_blocked("bare number `0.999` in a code span")

    def test_apa_leading_dot_statistics_need_provenance(self):
        self.say("Accuracy correlated with yield (r = .85, p < .001).")
        self.assert_blocked("number .85 has no row")

    def test_sample_size_in_year_range_needs_provenance(self):
        self.say("We used n = 2045 plots.")
        self.assert_blocked("number 2045 has no row")

    def test_citations_outside_citekey_syntax_are_blocked(self):
        for sentence, shown in [("Validation matters (Smith et al., 2021).", "(Smith et al., 2021)"),
                                ("Validation matters (Smith, 2020; Lee, 2019).", "(Smith, 2020;"),
                                (r"Validation matters \citep{smith2021}.", r"\\citep{"),
                                ("Validation matters [3].", "numeric citation [3]")]:
            with self.subTest(sentence):
                self.say(sentence)
                self.assert_blocked(shown)

    def test_hand_written_source_text_cannot_carry_a_quote(self):
        (self.proj / "literature/text/work01.txt").write_text("ACCESS: full-text\nA spatial gap observed across regions.")
        self.assert_blocked("literature/text/work01.txt was not produced by `rosctl fetch-text`")

    def test_logged_script_that_types_a_result_is_blocked(self):
        self.write("analysis/fake.py", "import json\njson.dump({'gain': 0.777}, open('results/fake.json', 'w'))\n")
        quiet(rosctl.main, ["run", "--", sys.executable, "analysis/fake.py"])
        self.assert_blocked("analysis/fake.py writes to results/ but reads no data")

    def test_typed_recomputation_audit_is_blocked(self):
        m = json.loads((self.proj / "results/metrics.json").read_text())
        (self.proj / "ledgers/RECOMPUTATION_AUDIT.csv").write_text(
            "stat_id,hypothesis_id,description,primary_value,primary_method,independent_value,independent_method,"
            f"abs_tolerance,rel_tolerance,status\ns1,H1,gap,{m['group_cv_rmse']},ols,{m['group_cv_rmse']},by hand,1e-6,1e-3,match\n")
        self.assert_blocked("RECOMPUTATION_AUDIT.csv was not produced by a logged re-computation script")

    def test_unchecked_manuscript_sources_are_blocked(self):
        (self.proj / "manuscript/main.tex").write_text("The gain was 0.931 \\cite{x}.\n")
        self.assert_blocked("manuscript/main.tex: numbers and citations in .tex files are not checked")

    def test_underscore_draft_cannot_reach_submission(self):
        (self.proj / "manuscript/_appendix.md").write_text("# Appendix\nThe gain was 0.931.\n")
        code, out = quiet(rosctl.main, ["gate", "S7"])
        self.assertIn("_appendix.md is not checked", out)  # warned while drafting
        self.s8_review()
        rosctl.record_approval(self.proj, rosctl.load_state(self.proj), "S8", "t",
                               checklist=rosctl.human_controls(self.proj, "S8"))
        self.s9_submission()
        self.assert_blocked("manuscript/_appendix.md was never checked", stage="S9")

    @unittest.expectedFailure
    def test_known_limit_forged_approval_in_state_file(self):
        """Local trust boundary: anything running as the owner's user can write .ros/state.json. The approval guard,
        Claude deny rules and git history make forgery visible, not impossible. Kept as an expected failure so the
        limit stays documented and a future fix shows up as an unexpected success."""
        self.s8_review()
        st = self.proj / ".ros/state.json"
        s = json.loads(st.read_text())
        s["approvals"]["S8"] = {"at": "x", "by": "x", "checklist": rosctl.human_controls(self.proj, "S8"),
                                "spot_checks": ["a", "b", "c"]}
        st.write_text(json.dumps(s))
        self.assert_blocked("approval", stage="S8")


class TestNumberSemantics(unittest.TestCase):
    def test_inequality_must_hold_for_the_cell(self):
        self.assertTrue(rosctl.value_matches_cell("<.001", "1.2e-42"))
        self.assertFalse(rosctl.value_matches_cell("<.001", "6.29"))
        self.assertTrue(rosctl.number_matches("<.001", "<0.001"))
        self.assertFalse(rosctl.number_matches("<.001", ".001"))  # "p < .001" is not "p = .001"

    def test_versions_and_named_parameters_in_code_spans_are_allowed(self):
        text = "Software `numpy 2.1.3`, `scikit-learn 1.5.2`, seed `20261114`, licence `CC BY 4.0`.\n"
        self.assertEqual([], [m.group(0) for m in rosctl.CODE_SPAN_NUMBER_RE.finditer(text)])

    def test_reading_scripts_are_not_flagged(self):
        reads = ["import csv\nrows = list(csv.DictReader(open('data/raw/x.csv')))\nopen('results/r.csv', 'w').write('1')\n",
                 "d <- read.csv('data/raw/x.csv')\nwrite.csv(d, 'results/r.csv')\n",
                 "import json\nm = json.load(open('results/a.json'))\njson.dump(m, open('results/b.json', 'w'))\n"]
        self.assertTrue(all(rosctl.rosqa._reads_input(r) for r in reads))
        self.assertFalse(rosctl.rosqa._reads_input("import json\njson.dump({'a': 1}, open('results/a.json', 'w'))\n"))


if __name__ == "__main__":
    unittest.main()
