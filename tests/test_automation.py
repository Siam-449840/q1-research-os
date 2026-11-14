"""v1.3 automation helpers: they must write ledgers the gates accept, and refuse when unsafe."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_rosctl import ProjectCase, quiet, rosctl  # noqa: E402

rosauto = rosctl.rosauto

BIBTEX = ("@article{Roberts_2017, title={Cross-validation strategies for data with temporal, spatial, hierarchical, "
          "or phylogenetic structure}, volume={40}, DOI={10.1111/ecog.02881}, journal={Ecography}, "
          "author={Roberts, David R. and Bahn, Volker}, year={2017}}")
CSL = json.dumps({"title": "Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure",
                  "issued": {"date-parts": [[2017]]}, "author": [{"family": "Roberts"}], "type": "journal-article"})
OPENALEX_WORK = json.dumps({"is_retracted": False, "abstract_inverted_index": {"Spatial": [0], "blocking": [1], "reduces": [2], "optimism": [3]}})


def registry(url, headers):
    accept = headers.get("Accept", "")
    if "doi.org/10.1111/ecog.02881" in url:
        return (200, BIBTEX) if "bibtex" in accept else (200, CSL)
    if "api.openalex.org/works/doi:" in url:
        return 200, OPENALEX_WORK
    if "api.openalex.org/works?" in url:
        return 200, json.dumps({"meta": {"count": 42}, "results": []})
    return 404, ""


class TestSearchHelper(ProjectCase):
    def test_search_saves_raw_output_and_logs_a_row_the_gate_accepts(self):
        row = rosauto.run_search(self.proj, "spatial cross-validation crop yield", "openalex", "counter-evidence", "2015", registry)
        self.assertEqual(row["hits"], "42")
        raw = json.loads((self.proj / row["raw_output"]).read_text())
        self.assertEqual(raw["total"], 42)
        rep = rosctl.Report("s")
        rosctl._check_search_log(self.proj, rosctl.read_csv(self.proj / "ledgers/SEARCH_LOG.csv"), rep)
        self.assertFalse(any("raw_output" in b or "hits" in b for b in rep.blockers))

    def test_truncated_response_is_retried_then_refused_never_parsed(self):
        calls = []
        partial = '{"meta": {"count": 7}, "results": ['
        full = json.dumps({"meta": {"count": 7}, "results": []})

        def flaky(url, headers):
            calls.append(url)
            return (200, partial) if len(calls) < 2 else (200, full)
        row = rosauto.run_search(self.proj, "q", "openalex", "main", "", flaky)
        self.assertEqual((row["hits"], len(calls)), ("7", 2))
        self.assertIn("select=", calls[0])
        with self.assertRaises(RuntimeError):
            rosauto.run_search(self.proj, "q", "openalex", "main", "", lambda u, h: (200, partial))
        self.assertEqual(len(rosctl.read_csv(self.proj / "ledgers/SEARCH_LOG.csv")), 1)

    def test_failed_search_logs_nothing(self):
        with self.assertRaises(RuntimeError):
            rosauto.run_search(self.proj, "q", "openalex", "main", "", lambda u, h: (503, ""))
        self.assertEqual(rosctl.read_csv(self.proj / "ledgers/SEARCH_LOG.csv"), [])


class TestReferenceHelper(ProjectCase):
    def test_add_ref_appends_registry_bibtex_with_stable_key_and_verifies_it(self):
        key, row = rosauto.add_reference(self.proj, "https://doi.org/10.1111/ECOG.02881", registry)
        self.assertEqual(key, "roberts2017cross")
        self.assertEqual(row["status"], "verified")
        self.assertIn("@article{roberts2017cross,", (self.proj / "refs/refs.bib").read_text())
        self.assertEqual(rosctl.check_bib(self.proj).blockers, [])
        key2, row2 = rosauto.add_reference(self.proj, "10.1111/ecog.02881", registry)
        self.assertEqual((key2, row2["status"]), ("roberts2017cross", "already_present"))

    def test_unresolvable_doi_is_never_added(self):
        with self.assertRaises(RuntimeError):
            rosauto.add_reference(self.proj, "10.9999/fake.001", registry)
        self.assertNotIn("fake", (self.proj / "refs/refs.bib").read_text())


class TestTextHelper(ProjectCase):
    def test_fetch_text_writes_honest_abstract_only_header(self):
        rosauto.add_reference(self.proj, "10.1111/ecog.02881", registry)
        self.assertEqual(rosauto.fetch_text(self.proj, "roberts2017cross", registry), "abstract-only")
        text = (self.proj / "literature/text/roberts2017cross.txt").read_text()
        self.assertTrue(text.startswith("ACCESS: abstract-only"))
        self.assertIn("Spatial blocking reduces optimism", text)

    def test_fetch_text_refuses_unknown_key(self):
        with self.assertRaises(RuntimeError):
            rosauto.fetch_text(self.proj, "ghost2020", registry)


class TestDataHelper(ProjectCase):
    def download(self, license_="CC-BY-4.0"):
        return rosauto.download_dataset(self.proj, "https://example.org/data/yield.csv", "D1", license_, "yields",
                                        lambda url: b"site,yield\nA,4.2\n", rosctl.sha256_file)

    def test_fetch_downloads_hashes_and_records_provenance_the_s3_gate_accepts(self):
        row = self.download()
        self.assertEqual(row["path"], "data/raw/D1/yield.csv")
        self.assertFalse(os.access(self.proj / row["path"], os.W_OK))
        self.assertFalse(any("D1" in b for b in rosctl.stage_s3(self.proj, {}).blockers))

    def test_api_urls_without_extension_get_a_readable_name(self):
        url = "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M&format=CSV"
        self.assertEqual(rosauto.download_filename(url, "D1"), "D1_point.csv")
        self.assertEqual(rosauto.download_filename("https://x.org/a/yield.csv", "D2"), "yield.csv")

    def test_fetch_refuses_missing_license_and_never_overwrites_raw_data(self):
        with self.assertRaises(RuntimeError):
            self.download(license_="")
        self.download()
        with self.assertRaises(RuntimeError):
            self.download()


class TestProvenanceHelper(ProjectCase):
    def test_unique_match_is_applied_ambiguous_and_missing_are_reported(self):
        self.write("analysis/m.py", "open('results/m.csv','w').write('model,rmse,r2\\nrf,0.8213,0.61\\nlm,0.9377,0.61\\n')\n")
        quiet(rosctl.main, ["run", "--", sys.executable, "analysis/m.py"])
        self.write("manuscript/manuscript.md", "## Results\nRMSE was 0.821 for RF; R2 was 0.61 for both; MAE was 0.555.\n")
        code, out = quiet(rosctl.main, ["provenance", "--apply"])
        self.assertEqual(code, 1)  # 0.555 has no source
        self.assertIn("applied  0.821", out)
        self.assertIn("CHOOSE   0.61", out)
        self.assertIn("MISSING  0.555", out)
        rows = rosctl.read_csv(self.proj / "ledgers/NUMBER_PROVENANCE.csv")
        self.assertEqual([(r["locator"], r["script"]) for r in rows], [("model=rf:rmse", "analysis/m.py")])
        self.assertFalse(any("0.821" in b for b in rosctl.check_numbers(self.proj).blockers))


class TestPilotFindings(ProjectCase):
    def test_negative_cell_keeps_its_sign_found_in_the_real_pilot(self):
        self.assertTrue(rosctl.value_matches_cell("-8.1%", "-0.08050304001810171"))
        self.assertFalse(rosctl.value_matches_cell("1.1%", "-0.0107"))

    def test_cite_number_validates_before_writing(self):
        self.write("analysis/m.py", "import json\njson.dump({'a': 1.5781, 'b': 1.5781}, open('results/m.json', 'w'))\n")
        quiet(rosctl.main, ["run", "--", sys.executable, "analysis/m.py"])
        code, out = quiet(rosctl.main, ["cite-number", "1.578", "results/m.json", "$.b", "--at", "manuscript/manuscript.md:3"])
        self.assertEqual(code, 0, out)
        code, out = quiet(rosctl.main, ["cite-number", "1.700", "results/m.json", "$.b", "--at", "x"])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        rows = rosctl.read_csv(self.proj / "ledgers/NUMBER_PROVENANCE.csv")
        self.assertEqual([(r["value"], r["script"]) for r in rows], [("1.578", "analysis/m.py")])


class TestGuidanceHelpers(ProjectCase):
    def test_next_maps_blockers_to_fix_commands(self):
        code, out = quiet(rosctl.main, ["next"])
        self.assertEqual(code, 1)
        self.assertIn("Current stage S0", out)
        self.assertIn("q1-proposal skill", out)

    def test_log_ai_produces_a_row_the_ai_gate_accepts(self):
        quiet(rosctl.main, ["log-ai", "--tool", "Claude Code", "--model", "claude-opus-5-5", "--purpose", "drafting methods"])
        self.write("manuscript/manuscript.md", "## Declaration of Generative AI Use\nClaude Code drafted text; authors verified.\n")
        self.assertEqual(rosctl.check_ai_log(self.proj).blockers, [])


if __name__ == "__main__":
    unittest.main()
