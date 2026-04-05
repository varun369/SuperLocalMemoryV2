# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.compliance.eu_ai_act — EU AI Act Verification.

Covers:
  - check_compliance for Mode A: full compliance, minimal risk, data local
  - check_compliance for Mode B: full compliance, minimal risk, local LLM
  - check_compliance for Mode C: NOT compliant, limited risk, cloud LLM
  - verify_all_modes: returns reports for all three modes
  - get_compliant_modes: returns only A and B
  - ComplianceReport field correctness
  - Transparency always met, human oversight always met
"""

from __future__ import annotations

import pytest

from superlocalmemory.storage.models import Mode
from superlocalmemory.compliance.eu_ai_act import ComplianceReport, EUAIActChecker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def checker() -> EUAIActChecker:
    return EUAIActChecker()


# ---------------------------------------------------------------------------
# Mode A — Local Guardian
# ---------------------------------------------------------------------------

class TestModeA:
    def test_is_compliant(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.compliant is True

    def test_risk_category_minimal(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.risk_category == "minimal"

    def test_data_stays_local(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.data_stays_local is True

    def test_no_generative_ai(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.uses_generative_ai is False

    def test_transparency_met(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.transparency_met is True

    def test_human_oversight(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.human_oversight is True

    def test_has_timestamp(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        assert report.timestamp  # non-empty ISO string

    def test_findings_contain_minimal_risk(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        joined = " ".join(report.findings)
        assert "Minimal risk" in joined


# ---------------------------------------------------------------------------
# Mode B — Smart Local
# ---------------------------------------------------------------------------

class TestModeB:
    def test_is_compliant(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.B)
        assert report.compliant is True

    def test_risk_category_minimal(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.B)
        assert report.risk_category == "minimal"

    def test_data_stays_local(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.B)
        assert report.data_stays_local is True

    def test_uses_generative_ai_locally(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.B)
        assert report.uses_generative_ai is True

    def test_findings_mention_local_ollama(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.B)
        joined = " ".join(report.findings)
        assert "local-only" in joined.lower() or "Ollama" in joined


# ---------------------------------------------------------------------------
# Mode C — Full Power
# ---------------------------------------------------------------------------

class TestModeC:
    def test_not_compliant(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.C)
        assert report.compliant is False

    def test_risk_category_limited(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.C)
        assert report.risk_category == "limited"

    def test_data_does_not_stay_local(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.C)
        assert report.data_stays_local is False

    def test_uses_generative_ai(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.C)
        assert report.uses_generative_ai is True

    def test_findings_mention_mode_c_not_compliant(
        self, checker: EUAIActChecker
    ) -> None:
        report = checker.check_compliance(Mode.C)
        joined = " ".join(report.findings)
        assert "NOT EU AI Act compliant" in joined

    def test_findings_mention_dpa(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.C)
        joined = " ".join(report.findings)
        assert "DPA" in joined or "Data Processing Agreement" in joined

    def test_transparency_still_met(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.C)
        assert report.transparency_met is True


# ---------------------------------------------------------------------------
# verify_all_modes
# ---------------------------------------------------------------------------

class TestVerifyAllModes:
    def test_returns_three_reports(self, checker: EUAIActChecker) -> None:
        reports = checker.verify_all_modes()
        assert len(reports) == 3
        assert set(reports.keys()) == {"a", "b", "c"}

    def test_all_reports_are_compliance_reports(
        self, checker: EUAIActChecker
    ) -> None:
        reports = checker.verify_all_modes()
        for report in reports.values():
            assert isinstance(report, ComplianceReport)

    def test_a_and_b_compliant_c_not(self, checker: EUAIActChecker) -> None:
        reports = checker.verify_all_modes()
        assert reports["a"].compliant is True
        assert reports["b"].compliant is True
        assert reports["c"].compliant is False


# ---------------------------------------------------------------------------
# get_compliant_modes
# ---------------------------------------------------------------------------

class TestGetCompliantModes:
    def test_returns_mode_a_and_b(self, checker: EUAIActChecker) -> None:
        modes = checker.get_compliant_modes()
        assert Mode.A in modes
        assert Mode.B in modes

    def test_does_not_include_mode_c(self, checker: EUAIActChecker) -> None:
        modes = checker.get_compliant_modes()
        assert Mode.C not in modes

    def test_returns_list_of_mode_enum(self, checker: EUAIActChecker) -> None:
        modes = checker.get_compliant_modes()
        assert all(isinstance(m, Mode) for m in modes)


# ---------------------------------------------------------------------------
# ComplianceReport is frozen dataclass
# ---------------------------------------------------------------------------

class TestComplianceReportImmutability:
    def test_cannot_mutate_report(self, checker: EUAIActChecker) -> None:
        report = checker.check_compliance(Mode.A)
        with pytest.raises(AttributeError):
            report.compliant = False  # type: ignore[misc]
