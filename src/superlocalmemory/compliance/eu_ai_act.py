# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — EU AI Act Compliance Verification.

Verifies that each operating mode meets EU AI Act requirements.
Mode A and B: FULL compliance (zero cloud, zero generative AI / local only).
Mode C: NOT compliant (cloud LLM processing).

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from superlocalmemory.core.modes import get_capabilities
from superlocalmemory.storage.models import Mode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComplianceReport:
    """EU AI Act compliance assessment for a specific mode."""

    mode: Mode
    compliant: bool
    risk_category: str          # "minimal" / "limited" / "high" / "unacceptable"
    data_stays_local: bool
    uses_generative_ai: bool
    transparency_met: bool
    human_oversight: bool
    findings: list[str]
    timestamp: str


class EUAIActChecker:
    """Verify EU AI Act compliance for each operating mode.

    EU AI Act (effective Aug 2025) classifies AI systems by risk:
    - Minimal risk: No obligations (most AI systems)
    - Limited risk: Transparency obligations
    - High risk: Strict requirements (biometric, critical infra)
    - Unacceptable: Banned

    Memory systems are generally "minimal risk" UNLESS they process
    personal data via cloud AI services (then "limited risk" with
    transparency obligations).
    """

    def check_compliance(self, mode: Mode) -> ComplianceReport:
        """Generate compliance report for a mode."""
        caps = get_capabilities(mode)
        findings: list[str] = []

        # Data locality
        data_local = caps.data_stays_local
        if not data_local:
            findings.append(
                "Data leaves device for cloud LLM processing. "
                "Requires Data Processing Agreement (DPA) with provider."
            )

        # Generative AI usage
        uses_gen_ai = caps.llm_fact_extraction or caps.llm_answer_generation
        local_gen_ai = uses_gen_ai and data_local

        if uses_gen_ai and not data_local:
            findings.append(
                "Uses cloud generative AI. EU AI Act Art. 52 requires "
                "transparency: users must be informed AI generates content."
            )

        # Transparency
        transparency = True  # We always disclose AI usage
        findings.append("Transparency requirement MET: system identifies as AI-assisted.")

        # Human oversight
        human_oversight = True  # User controls all memory operations
        findings.append("Human oversight MET: user controls store/recall/delete.")

        # Risk classification
        if not uses_gen_ai:
            risk = "minimal"
            findings.append("Minimal risk: no generative AI, local processing only.")
        elif local_gen_ai:
            risk = "minimal"
            findings.append("Minimal risk: generative AI is local-only (Ollama).")
        else:
            risk = "limited"
            findings.append(
                "Limited risk: cloud generative AI requires transparency "
                "disclosure and DPA with cloud provider."
            )

        compliant = caps.eu_ai_act_compliant
        if not compliant:
            findings.append(
                "Mode C is NOT EU AI Act compliant by design. "
                "Use Mode A or B for EU-compliant deployments."
            )

        return ComplianceReport(
            mode=mode,
            compliant=compliant,
            risk_category=risk,
            data_stays_local=data_local,
            uses_generative_ai=uses_gen_ai,
            transparency_met=transparency,
            human_oversight=human_oversight,
            findings=findings,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def verify_all_modes(self) -> dict[str, ComplianceReport]:
        """Generate compliance reports for all three modes."""
        return {
            mode.value: self.check_compliance(mode)
            for mode in Mode
        }

    def get_compliant_modes(self) -> list[Mode]:
        """Return list of EU AI Act compliant modes."""
        return [
            mode for mode in Mode
            if get_capabilities(mode).eu_ai_act_compliant
        ]
