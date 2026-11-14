"""Tests for the v1.1 anti-fabrication / anti-leakage gates. Each encodes one way an agent could cheat."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_rosctl import LEDGER_HEADER, ProjectCase, rosctl  # noqa: E402

rosrefs = rosctl.rosrefs
rosstats = rosctl.rosstats


def fake_fetch(responses):
    """Offline stand-in for the network: maps URL substrings to (status, body)."""
    def fetch(url, headers):
        for needle, resp in responses.items():
            if needle in url:
                return resp
        return 404, ""
    return fetch


CSL = json.dumps({"title": "Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure",
                  "issued": {"date-parts": [[2017]]}})


class TestReferenceVerification(unittest.TestCase):
    def verify(self, bib_body, responses):
        return rosrefs.verify_bib({"k": bib_body}, fetch=fake_fetch(responses), pause_s=0)[0]

    def test_real_doi_with_matching_title_is_verified(self):
        row = self.verify("title={Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure},\n doi={10.1111/ecog.02881}",
                          {"doi.org/10.1111": (200, CSL), "openalex": (200, '{"is_retracted": false}')})
        self.assertEqual(row["status"], "verified")
        self.assertEqual(row["registered_year"], "2017")

    def test_nonexistent_doi_is_reported_not_found_to_stop_hallucinated_references(self):
        row = self.verify("title={Deep learning solves rice yield},\n doi={10.9999/fake.001}", {})
        self.assertEqual(row["status"], "not_found")

    def test_real_doi_attached_to_wrong_title_is_a_mismatch(self):
        row = self.verify("title={Transformers predict wheat yield in Punjab},\n doi={10.1111/ecog.02881}",
                          {"doi.org/10.1111": (200, CSL), "openalex": (200, "{}")})
        self.assertEqual(row["status"], "title_mismatch")

    def test_retracted_work_is_flagged(self):
        row = self.verify("title={Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure},\n doi={10.1111/ecog.02881}",
                          {"doi.org/10.1111": (200, CSL), "openalex": (200, '{"is_retracted": true}')})
        self.assertEqual(row["status"], "retracted")

    def test_nested_braces_and_doi_url_prefix_are_normalised(self):
        f = rosrefs.bib_fields("title = {{Deep} {Learning} for crops},\n doi = {https://doi.org/10.1/ABC},\n year = 2020,")
        self.assertEqual(f["title"], "Deep Learning for crops")
        self.assertEqual(rosrefs.norm_doi(f["doi"]), "10.1/abc")
        self.assertEqual(f["year"], "2020")


class TestBibGate(ProjectCase):
    def test_bib_entry_without_registry_verification_is_blocked(self):
        self.write("refs/refs.bib", "@article{fake2024,\n title={X},\n doi={10.9999/fake}\n}\n")
        self.assertTrue(any("run `rosctl verify-refs`" in b for b in rosctl.check_bib(self.proj).blockers))

    def test_failed_verification_blocks_and_edited_doi_invalidates_old_verification(self):
        self.write("refs/refs.bib", "@article{a,\n doi={10.1/new}\n}\n@article{b,\n doi={10.2/y}\n}\n")
        self.write("ledgers/REFERENCE_VERIFICATION.csv", LEDGER_HEADER +
                   "a,10.1/old,,verified,1.0,T,2020,2020,no,doi.org,t\n"
                   "b,10.2/y,,not_found,,,,,,doi.org,t\n")
        blockers = rosctl.check_bib(self.proj).blockers
        self.assertTrue(any("'a' not verified" in b for b in blockers))
        self.assertTrue(any("'b' failed registry verification: not_found" in b for b in blockers))


class TestNumberLocators(ProjectCase):
    def setUp(self):
        super().setUp()
        self.write("results/m.csv", "model,rmse,r2\nrf,0.83,0.80\nlm,0.77,0.61\n")
        self.write("results/s.json", json.dumps({"h1": {"gap": 0.1534, "ci": [0.08, 0.22]}}))
        self.write("results/log.txt", "fold summary\nmean rmse = 1.2345 t/ha\n")

    def prov(self, rows):
        self.write("ledgers/NUMBER_PROVENANCE.csv", "number_id,value,manuscript_location,results_file,locator,script,notes\n" + rows)

    def test_value_elsewhere_in_file_no_longer_counts(self):
        self.prov("n1,0.80,Results,results/m.csv,model=rf:rmse,a.py,\n")  # 0.80 exists (rf r2) but rf rmse is 0.83
        self.assertTrue(any("not a correct rounding" in b for b in rosctl.check_numbers(self.proj).blockers))

    def test_csv_json_and_line_locators_resolve_with_correct_rounding(self):
        self.prov("n1,0.83,R,results/m.csv,model=rf:rmse,a.py,\n"
                  "n2,15.3%,R,results/s.json,$.h1.gap,a.py,\n"
                  "n3,0.22,R,results/s.json,$.h1.ci.1,a.py,\n"
                  "n4,1.23,R,results/log.txt,line:2,a.py,\n")
        self.write("manuscript/manuscript.md", "## Results\nRMSE 0.83, gap 15.3% (CI up to 0.22), mean 1.23.\n")
        self.assertEqual(rosctl.check_numbers(self.proj).blockers, [])

    def test_ambiguous_or_missing_locator_is_blocked(self):
        self.prov("n1,0.83,R,results/m.csv,rmse,a.py,\nn2,0.83,R,results/m.csv,,a.py,\n")
        blockers = rosctl.check_numbers(self.proj).blockers
        self.assertEqual(sum("does not resolve uniquely" in b for b in blockers), 2)


class TestStatsCheck(ProjectCase):
    def test_engine_reproduces_textbook_critical_values(self):
        cases = [("t", 2.228, 10, None), ("F", 4.965, 1, 10), ("chi2", 3.841, 1, None),
                 ("chi2", 18.307, 10, None), ("z", 1.96, None, None), ("r", 0.361, 28, None)]
        for test, stat, d1, d2 in cases:
            self.assertAlmostEqual(rosstats.p_value(test, stat, d1, d2), 0.05, places=3, msg=test)

    def test_inconsistent_p_value_is_blocked_and_decision_errors_named(self):
        self.write("manuscript/manuscript.md", "## Results\nSignificant, t(10) = 2.23, p = 0.001. Also t(30) = 1.20, p < .05.\n")
        blockers = rosctl.check_stats(self.proj).blockers
        self.assertEqual(len(blockers), 2)
        self.assertTrue(all("DECISION ERROR" in b for b in blockers))

    def test_correctly_rounded_results_pass(self):
        self.write("manuscript/manuscript.md", "## Results\nt(10) = 2.23, p = .05; F(2, 57) = 4.10, p < .05; "
                                               "χ2(1) = 3.84, p = .05; r(40) = .31, p = .045; z = 1.96, p = .05.\n")
        self.assertEqual(rosctl.check_stats(self.proj).blockers, [])


class TestSplitAudit(ProjectCase):
    def test_group_in_train_and_test_of_same_fold_is_leakage(self):
        self.write("results/splits/cv.csv", "fold,split,group\n1,train,siteA\n1,test,siteA\n1,test,siteB\n")
        self.assertTrue(any("LEAKAGE" in b and "siteA" in b for b in rosctl.check_splits(self.proj).blockers))

    def test_disjoint_leave_group_out_folds_pass(self):
        self.write("results/splits/cv.csv", "fold,split,group\n1,train,A\n1,test,B\n2,train,B\n2,test,A\n")
        self.assertEqual(rosctl.check_splits(self.proj).blockers, [])

    def test_missing_manifest_needs_written_justification(self):
        self.assertTrue(rosctl.check_splits(self.proj).blockers)
        self.write("results/splits/NOT_APPLICABLE.md", "word " * 45)
        self.assertEqual(rosctl.check_splits(self.proj).blockers, [])


class TestReviewIndependence(ProjectCase):
    def test_self_review_without_reports_is_blocked(self):
        rows = ["dimension,score,evidence,reviewer"] + [f"{d},5,ok,self" for d in rosctl.RUBRIC_DIMENSIONS]
        self.write("review/Q1_SCORECARD.csv", "\n".join(rows) + "\n")
        self.write("review/ISSUES.csv", "issue_id,reviewer,severity,location,issue,action,status,resolution_note\nI1,r,minor,x,y,z,resolved,ok\n")
        blockers = rosctl.check_review(self.proj).blockers
        self.assertTrue(any("not independent" in b for b in blockers))
        self.assertEqual(sum("missing review/REVIEW_" in b for b in blockers), 4)


class TestQuoteVerification(ProjectCase):
    def test_misquote_is_blocked_when_source_text_exists(self):
        self.write("literature/text/smith2020.txt", "Yields de-\nclined by 4% under heat stress in our panel.")
        self.write("refs/refs.bib", "@article{smith2020,\n doi={10.1/x}\n}\n")
        self.write("manuscript/manuscript.md", "## Introduction\nHeat lowered yields [@smith2020].\n")
        base = "claim_id,manuscript_location,claim_text,citekey,evidence_location,evidence_quote,support_level,checked_by\n"
        self.write("ledgers/CLAIM_SUPPORT.csv", base + 'c1,I,x,smith2020,p. 3,"yields doubled under heat",supports,a\n')
        self.assertTrue(any("misquotation" in b for b in rosctl.check_citations(self.proj).blockers))
        self.write("ledgers/CLAIM_SUPPORT.csv", base + 'c1,I,x,smith2020,p. 3,"Yields declined by 4% under heat stress",supports,a\n')
        self.assertFalse(any("misquotation" in b for b in rosctl.check_citations(self.proj).blockers))


class TestCsvOutput(ProjectCase):
    def test_hash_rows_have_unix_newlines_so_pasting_into_ledgers_adds_no_phantom_row(self):
        import contextlib
        import io
        self.write("data/raw/d/x.csv", "a\n1\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rosctl.main(["hash", "data/raw/d/x.csv"])
        self.assertNotIn("\r", buf.getvalue())
        self.write("ledgers/DATA_PROVENANCE.csv", "dataset_id,name,source_url,version_or_access_date,license,path,sha256,size_bytes,notes\n"
                   + "D1,x,https://e.org,2026,CC0," + buf.getvalue().strip() + ",\n")
        self.assertEqual(len(rosctl.read_csv(self.proj / "ledgers/DATA_PROVENANCE.csv")), 1)


class TestDomainPacks(unittest.TestCase):
    PACK_FILES = ["DOMAIN.md", "DATASETS.md", "METHODS.md", "PITFALLS.md", "REPORTING.md", "JOURNALS.md"]

    def test_every_domain_pack_has_all_six_files_so_agents_never_hit_a_missing_playbook(self):
        packs = [p for p in (rosctl.FRAMEWORK_ROOT / "domains").iterdir() if p.is_dir()]
        self.assertGreaterEqual(len(packs), 3)
        for pack in packs:
            for name in self.PACK_FILES:
                self.assertTrue((pack / name).is_file() and (pack / name).stat().st_size > 100, f"{pack.name}/{name}")

    def test_pipeline_is_discipline_agnostic_with_blank_template_pack(self):
        import contextlib
        import io
        import os
        import tempfile
        from test_rosctl import EXAMPLE
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            proj = Path(d) / "ecology-paper"
            self.assertEqual(rosctl.main(["init", str(proj), "--domain", "_template"]), 0)
            (proj / "PROPOSAL.md").write_text(EXAMPLE.read_text().replace("agriculture", "_template"))
            os.chdir(proj)
            try:
                self.assertEqual(rosctl.main(["gate", "S0"]), 0)
            finally:
                os.chdir(old)


class TestApprovalHardening(unittest.TestCase):
    def test_agent_environment_and_agent_ancestry_are_refused(self):
        self.assertIn("environment marker", rosctl.approval_refusal({"CLAUDECODE": "1"}, [], True))
        self.assertIn("AI agent process", rosctl.approval_refusal({}, ["zsh", "claude", "Claude"], True))
        self.assertIn("AI agent process", rosctl.approval_refusal({}, ["bash", "language_server_macos_arm"], True))
        self.assertIn("interactive", rosctl.approval_refusal({}, ["zsh"], False))

    def test_plain_human_terminal_is_allowed(self):
        self.assertEqual(rosctl.approval_refusal({}, ["zsh", "login", "Terminal"], True), "")


if __name__ == "__main__":
    unittest.main()
