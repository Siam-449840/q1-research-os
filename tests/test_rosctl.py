"""Behavioural tests for rosctl. Run: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("rosctl", ROOT / "bin" / "rosctl.py")
rosctl = importlib.util.module_from_spec(spec)
sys.modules["rosctl"] = rosctl
spec.loader.exec_module(rosctl)

EXAMPLE = ROOT / "examples/agriculture-rice-yield-transfer/PROPOSAL.md"
LEDGER_HEADER = "citekey,doi,url,status,title_similarity,registered_title,registered_year,bib_year,is_retracted,source,checked_at\n"  # v1.1 subset; extra v1.2 columns are optional for gates


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        code = fn(*args)
    return code, buf.getvalue()


class ProjectCase(unittest.TestCase):
    """Creates a fresh project in a temp dir and chdirs into it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        self.proj = Path(self.tmp.name) / "paper"
        code, out = quiet(rosctl.main, ["init", str(self.proj), "--domain", "agriculture"])
        self.assertEqual(code, 0, out)
        os.chdir(self.proj)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def write(self, rel, text):
        p = self.proj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def state(self):
        return json.loads((self.proj / ".ros/state.json").read_text())


class TestProposalLint(unittest.TestCase):
    def test_worked_example_passes_so_users_have_a_valid_reference(self):
        rep = rosctl.lint_proposal(EXAMPLE)
        self.assertEqual(rep.blockers, [])

    def test_blank_template_is_blocked_to_prevent_agents_starting_on_placeholders(self):
        rep = rosctl.lint_proposal(ROOT / "templates/project/PROPOSAL.md")
        self.assertFalse(rep.ok)
        self.assertTrue(any("placeholder" in b for b in rep.blockers))

    def test_hypothesis_without_decision_rule_is_blocked_because_it_cannot_be_falsified(self):
        text = EXAMPLE.read_text().replace("**Decision rule:**", "**Rule:**")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "P.md"
            p.write_text(text)
            rep = rosctl.lint_proposal(p)
        self.assertTrue(any("decision rule" in b for b in rep.blockers))

    def test_metadata_section_is_not_confused_with_data_section(self):
        secs = rosctl.split_sections("## 0. Metadata\nmeta words\n## 5. Data Sources\nhttps://x.org License\n")
        self.assertIn("https://x.org", rosctl.find_section(secs, "data"))


class TestInit(unittest.TestCase):
    def test_init_refuses_to_overwrite_existing_work(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "existing"
            target.mkdir()
            (target / "CLAUDE.md").write_text("my precious rules")
            code, out = quiet(rosctl.main, ["init", str(target), "--domain", "agriculture"])
            self.assertEqual(code, 2)
            self.assertIn("CLAUDE.md", out)
            self.assertEqual((target / "CLAUDE.md").read_text(), "my precious rules")

    def test_extra_skills_are_added_but_never_replace_framework_skills(self):
        with tempfile.TemporaryDirectory() as d:
            extra = Path(d) / "extra"
            (extra / "stats-helper").mkdir(parents=True)
            (extra / "stats-helper/SKILL.md").write_text("---\nname: stats-helper\n---\n")
            (extra / "q1-pipeline").mkdir()
            (extra / "q1-pipeline/SKILL.md").write_text("impostor")
            target = Path(d) / "p"
            code, out = quiet(rosctl.main, ["init", str(target), "--extra-skills", str(extra)])
            self.assertEqual(code, 0, out)
            self.assertTrue((target / ".agents/skills/stats-helper/SKILL.md").is_file())
            self.assertNotEqual((target / ".claude/skills/q1-pipeline/SKILL.md").read_text(), "impostor")

    def test_init_rejects_unknown_domain(self):
        with tempfile.TemporaryDirectory() as d:
            code, out = quiet(rosctl.main, ["init", str(Path(d) / "p"), "--domain", "astrology"])
        self.assertEqual(code, 2)
        self.assertIn("agriculture", out)


class TestInitLayout(ProjectCase):
    def test_init_installs_constitution_skills_and_domain_for_every_agent(self):
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
            self.assertIn("Absolute rules", (self.proj / name).read_text())
        for d in (".claude/skills", ".agents/skills", ".agent/skills"):
            self.assertTrue((self.proj / d / "q1-pipeline/stages/S7_manuscript.md").is_file())
        self.assertTrue((self.proj / ".ros/domain/PITFALLS.md").is_file())
        self.assertEqual(self.state()["domain"], "agriculture")


class TestNumbers(ProjectCase):
    def setUp(self):
        super().setUp()
        self.write("results/metrics.csv", "model,rmse,gap\nrf,0.8213,0.234\n")
        self.write("ledgers/NUMBER_PROVENANCE.csv",
                   "number_id,value,manuscript_location,results_file,locator,script,notes\n"
                   "n1,0.82,Results,results/metrics.csv,rmse,analysis/05.py,\n"
                   "n2,23.4%,Results,results/metrics.csv,gap,analysis/05.py,\n")

    def test_provenanced_numbers_pass_and_noise_is_ignored(self):
        self.write("manuscript/manuscript.md",
                   "## Results\nRMSE was 0.82 and the gap 23.4% (Fig. 3, Table 12) in 2019-2023 using "
                   "`pandas 2.2.3` and seed `20261113` across 3 sites [@a2020].\n")
        rep = rosctl.check_numbers(self.proj)
        self.assertEqual(rep.blockers, [])

    def test_unprovenanced_number_is_blocked_to_prevent_fabricated_results(self):
        self.write("manuscript/manuscript.md", "## Results\nAccuracy reached 0.97.\n")
        rep = rosctl.check_numbers(self.proj)
        self.assertTrue(any("0.97" in b for b in rep.blockers))

    def test_provenance_row_whose_value_is_absent_from_results_file_is_blocked(self):
        self.write("ledgers/NUMBER_PROVENANCE.csv",
                   "number_id,value,manuscript_location,results_file,locator,script,notes\n"
                   "n1,0.91,Results,results/metrics.csv,rmse,analysis/05.py,\n")
        self.write("manuscript/manuscript.md", "## Results\nRMSE was 0.91.\n")
        rep = rosctl.check_numbers(self.proj)
        self.assertTrue(any("not a correct rounding" in b for b in rep.blockers))

    def test_numbers_in_reference_list_are_not_checked(self):
        self.write("manuscript/manuscript.md", "## Results\nRMSE was 0.82.\n## References\nSmith 2020, 45(3), 112-130.\n")
        self.assertEqual(rosctl.check_numbers(self.proj).blockers, [])


class TestCitations(ProjectCase):
    def setUp(self):
        super().setUp()
        self.write("refs/refs.bib", "@article{smith2020yield,\n  title={T},\n  doi={10.1/x}\n}\n"
                                    "@article{nodoi2021,\n  title={U}\n}\n")
        self.write("ledgers/CLAIM_SUPPORT.csv",
                   "claim_id,manuscript_location,claim_text,citekey,evidence_location,evidence_quote,support_level,checked_by\n"
                   "c1,Intro,x,smith2020yield,p. 4,\"yields rose\",supports,agent\n")
        self.write("ledgers/REFERENCE_VERIFICATION.csv", LEDGER_HEADER +
                   "smith2020yield,10.1/x,,verified,0.990,T,2020,2020,no,doi.org,2026-11-14T00:00:00Z\n")

    def test_supported_citation_passes_and_emails_are_not_citations(self):
        self.write("literature/text/smith2020yield.txt", "ACCESS: full-text\nIn the panel, yields rose steadily.")
        self.write("manuscript/manuscript.md", "## Introduction\nYields rose [@smith2020yield]. Contact me@uni.edu.\n")
        rep = rosctl.check_citations(self.proj)
        self.assertFalse(any("smith2020yield" in b for b in rep.blockers))
        self.assertFalse(any("uni" in b for b in rep.blockers))

    def test_citation_missing_from_bib_is_blocked_to_prevent_hallucinated_references(self):
        self.write("manuscript/manuscript.md", "## Introduction\nAs shown [@ghost2024].\n")
        rep = rosctl.check_citations(self.proj)
        self.assertTrue(any("ghost2024" in b and "not in refs" in b for b in rep.blockers))

    def test_bib_entry_without_doi_or_url_is_blocked_because_it_cannot_be_verified(self):
        rep = rosctl.check_bib(self.proj)
        self.assertTrue(any("nodoi2021" in b for b in rep.blockers))

    def test_citation_without_claim_support_row_is_blocked(self):
        self.write("refs/refs.bib", "@article{lee2022,\n  doi={10.2/y}\n}\n")
        self.write("manuscript/manuscript.md", "## Introduction\nClaim [@lee2022].\n")
        rep = rosctl.check_citations(self.proj)
        self.assertTrue(any("CLAIM_SUPPORT" in b for b in rep.blockers))


class TestRecompute(ProjectCase):
    HEADER = "stat_id,hypothesis_id,description,primary_value,primary_method,independent_value,independent_method,abs_tolerance,rel_tolerance,status\n"

    def setUp(self):
        super().setUp()
        self.write("protocol/PROTOCOL.md", "## 2. Hypotheses\nH1 ... Decision rule: x\n## 11. Deviations\nNone\n")

    def test_matching_independent_values_pass(self):
        self.write("ledgers/RECOMPUTATION_AUDIT.csv", self.HEADER + "s1,H1,rmse,0.8213,sklearn,0.82131,numpy,1e-4,,\n")
        self.assertEqual(rosctl.check_recompute(self.proj).blockers, [])

    def test_mismatch_is_blocked_so_silent_bugs_stop_the_pipeline(self):
        self.write("ledgers/RECOMPUTATION_AUDIT.csv", self.HEADER + "s1,H1,rmse,0.82,sklearn,0.91,numpy,,,\n")
        self.assertTrue(any("exceeds tolerance" in b for b in rosctl.check_recompute(self.proj).blockers))

    def test_same_method_is_not_independent(self):
        self.write("ledgers/RECOMPUTATION_AUDIT.csv", self.HEADER + "s1,H1,rmse,0.82,sklearn,0.82,sklearn,,,\n")
        self.assertTrue(any("must differ" in b for b in rosctl.check_recompute(self.proj).blockers))

    def test_uncovered_hypothesis_is_blocked(self):
        self.write("protocol/PROTOCOL.md", "## 2. Hypotheses\nH1 H2\n## 11. Deviations\n")
        self.write("ledgers/RECOMPUTATION_AUDIT.csv", self.HEADER + "s1,H1,rmse,0.82,a,0.82,b,,,\n")
        self.assertTrue(any("H2" in b for b in rosctl.check_recompute(self.proj).blockers))


class TestGatesAndApprovals(ProjectCase):
    def test_gate_s0_fails_on_blank_template_and_passes_on_good_proposal(self):
        code, _ = quiet(rosctl.main, ["gate", "S0"])
        self.assertEqual(code, 1)
        self.write("PROPOSAL.md", EXAMPLE.read_text())
        code, out = quiet(rosctl.main, ["gate", "S0"])
        self.assertEqual(code, 0, out)
        self.assertIn("S0", self.state()["passed"])

    def test_failed_gate_clears_its_own_and_all_later_passes_so_status_never_lies(self):
        self.write("PROPOSAL.md", EXAMPLE.read_text())
        quiet(rosctl.main, ["gate", "S0"])
        state = self.state()
        state["passed"]["S1"] = {"at": "x", "commit": "y"}
        rosctl.save_state(self.proj, state)
        self.write("PROPOSAL.md", "# broken\n")
        code, _ = quiet(rosctl.main, ["gate", "S0"])
        self.assertEqual(code, 1)
        self.assertEqual(self.state()["passed"], {})

    def test_later_gate_requires_earlier_owner_approvals(self):
        self.write("PROPOSAL.md", EXAMPLE.read_text())
        code, out = quiet(rosctl.main, ["gate", "S3"])
        self.assertEqual(code, 1)
        self.assertIn("rosctl approve S1", out)

    def test_approve_refuses_non_interactive_callers_so_agents_cannot_self_approve(self):
        code, out = quiet(rosctl.main, ["approve", "S1"])
        self.assertEqual(code, 3)
        self.assertIn("REFUSED", out)

    def test_protocol_edit_after_freeze_is_detected_but_deviation_log_is_allowed(self):
        body = "## 2. Hypotheses\nH1 Decision rule: x\n## 11. Deviations\nNone yet.\n"
        self.write("protocol/PROTOCOL.md", body)
        state = self.state()
        state["protocol_hash"] = rosctl.protocol_hash(self.proj)
        rosctl.save_state(self.proj, state)
        self.write("protocol/PROTOCOL.md", body + "2026-12-01 | changed split | reason | none\n")
        self.assertFalse(any("changed after freeze" in b for b in rosctl.stage_s2(self.proj, state).blockers))
        self.write("protocol/PROTOCOL.md", body.replace("H1", "H1 (edited)"))
        self.assertTrue(any("changed after freeze" in b for b in rosctl.stage_s2(self.proj, state).blockers))

    def test_modified_raw_data_is_detected_by_hash(self):
        f = self.write("data/raw/d1/yield.csv", "a,b\n1,2\n")
        sha = rosctl.sha256_file(f)
        self.write("ledgers/DATA_PROVENANCE.csv",
                   "dataset_id,name,source_url,version_or_access_date,license,path,sha256,size_bytes,notes\n"
                   f"D1,yield,https://x.org,2026-11-14,CC-BY-4.0,data/raw/d1/yield.csv,{sha},8,\n")
        self.assertFalse(any("sha256" in b for b in rosctl.stage_s3(self.proj, {}).blockers))
        f.write_text("a,b\n1,3\n")
        self.assertTrue(any("sha256 mismatch" in b for b in rosctl.stage_s3(self.proj, {}).blockers))

    def test_run_logs_failures_and_propagates_exit_code(self):
        code, out = quiet(rosctl.main, ["run", "--", sys.executable, "-c", "raise SystemExit(3)"])
        self.assertEqual(code, 3)
        rows = rosctl.read_csv(self.proj / "ledgers/RUN_LOG.csv")
        self.assertEqual(rows[-1]["exit_code"], "3")
        self.assertIn("never invent results", out)


class TestReview(ProjectCase):
    def test_low_score_or_open_major_issue_blocks_review_gate(self):
        rows = ["dimension,score,evidence,reviewer"] + [f"{d},5,ok,r1" for d in rosctl.RUBRIC_DIMENSIONS]
        rows[2] = "novelty,3,incremental,r2"
        self.write("review/Q1_SCORECARD.csv", "\n".join(rows) + "\n")
        self.write("review/ISSUES.csv", "issue_id,reviewer,severity,location,issue,action,status,resolution_note\n"
                                        "I1,r1,major,Sec 3,leakage,fix,open,\n")
        blockers = rosctl.check_review(self.proj).blockers
        self.assertTrue(any("novelty" in b for b in blockers))
        self.assertTrue(any("I1" in b for b in blockers))


if __name__ == "__main__":
    unittest.main()
