"""
Unit tests for the pure, deterministic logic underlying the pipeline's
evidence reporting, remediation targeting, and dashboard input validation.

These deliberately avoid anything that calls the LLM or runs Maven - that
behaviour is exercised empirically instead, by running the full pipeline
against real applications (see Chapter 5, Sections 5.4 and 5.5). What's
tested here is the logic that turns raw scan/build output into the numbers
and decisions the dissertation reports.

Run with:  python -m unittest discover -s tests -v
(from the agents/ directory)
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPT_DIR)

from generate_evaluation_report import count_vulnerabilities, parse_test_count
from remediation_agent import get_prioritized_targets
import app as dashboard_app


class TestCountVulnerabilities(unittest.TestCase):
    """count_vulnerabilities() must count each CVE once overall, even when
    the same CVE is listed against more than one dependency entry."""

    def _write_fixture(self, dependencies):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump({"dependencies": dependencies}, f)
        f.close()
        return f.name

    def test_dedupes_shared_cve_across_dependencies(self):
        path = self._write_fixture([
            {"vulnerabilities": [{"name": "CVE-2024-0001", "severity": "HIGH"}]},
            {"vulnerabilities": [{"name": "CVE-2024-0001", "severity": "HIGH"}]},
            {"vulnerabilities": [{"name": "CVE-2024-0002", "severity": "CRITICAL"}]},
        ])
        result = count_vulnerabilities(path)
        os.remove(path)
        self.assertEqual(result["total_cves"], 2)
        self.assertEqual(result["vulnerable_dependencies"], 3)
        self.assertEqual(result["by_severity"]["CRITICAL"], 1)
        self.assertEqual(result["by_severity"]["HIGH"], 1)

    def test_missing_file_returns_none(self):
        self.assertIsNone(count_vulnerabilities("does_not_exist.json"))


class TestParseTestCount(unittest.TestCase):
    """parse_test_count() pulls counts out of a stage's free-text detail
    string; it must handle the expected format and fail safely on others."""

    def test_valid_string(self):
        tests, failures = parse_test_count("Tests: 171, Failures: 0")
        self.assertEqual((tests, failures), (171, 0))

    def test_malformed_string_returns_none_none(self):
        self.assertEqual(parse_test_count("BUILD SUCCESS"), (None, None))

    def test_none_input_returns_none_none(self):
        self.assertEqual(parse_test_count(None), (None, None))


class TestGetPrioritizedTargets(unittest.TestCase):
    """get_prioritized_targets() must sort by severity then confidence,
    deduplicate by (group_id, artifact_id), and respect max_targets."""

    def test_sorts_by_severity_then_confidence(self):
        findings = [
            {"group_id": "a", "artifact_id": "1", "severity": "HIGH", "confidence": "HIGH"},
            {"group_id": "b", "artifact_id": "2", "severity": "CRITICAL", "confidence": "LOW"},
            {"group_id": "c", "artifact_id": "3", "severity": "CRITICAL", "confidence": "HIGHEST"},
        ]
        result = get_prioritized_targets(findings)
        self.assertEqual(
            [(f["group_id"], f["artifact_id"]) for f in result],
            [("c", "3"), ("b", "2"), ("a", "1")],
        )

    def test_deduplicates_by_dependency_keeping_first(self):
        findings = [
            {"group_id": "x", "artifact_id": "y", "severity": "CRITICAL", "confidence": "HIGH"},
            {"group_id": "x", "artifact_id": "y", "severity": "HIGH", "confidence": "LOW"},
        ]
        result = get_prioritized_targets(findings)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["severity"], "CRITICAL")

    def test_respects_max_targets_cap(self):
        findings = [
            {"group_id": str(i), "artifact_id": str(i), "severity": "HIGH", "confidence": "HIGH"}
            for i in range(10)
        ]
        result = get_prioritized_targets(findings, max_targets=5)
        self.assertEqual(len(result), 5)


class TestValidateAppId(unittest.TestCase):
    """_validate_app_id() is the fix for the path-traversal issue described
    in Section 4.2: any app_id not in the known set must be rejected."""

    @patch("app._discover_app_ids", return_value=["app7-h2crud", "app8-restdemo"])
    def test_known_app_id_accepted(self, _mock):
        self.assertTrue(dashboard_app._validate_app_id("app7-h2crud"))

    @patch("app._discover_app_ids", return_value=["app7-h2crud"])
    def test_reference_run_always_accepted(self, _mock):
        self.assertTrue(dashboard_app._validate_app_id("reference-run"))

    @patch("app._discover_app_ids", return_value=["app7-h2crud"])
    def test_unknown_app_id_rejected(self, _mock):
        self.assertFalse(dashboard_app._validate_app_id("app99-nonexistent"))

    @patch("app._discover_app_ids", return_value=["app7-h2crud"])
    def test_path_traversal_attempt_rejected(self, _mock):
        self.assertFalse(dashboard_app._validate_app_id("../../../../etc/passwd"))


if __name__ == "__main__":
    unittest.main()