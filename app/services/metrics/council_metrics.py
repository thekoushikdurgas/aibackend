"""
In-process counters for Council v2 (claim verification, abstention, coverage).
Prometheus may be wired later; these are safe to read from /metrics-style debug endpoints.
"""

import logging
from collections import defaultdict
from typing import Any, Dict

logger = logging.getLogger(__name__)


class CouncilMetrics:
    def __init__(self) -> None:
        self.claims_total: Dict[str, int] = defaultdict(int)  # status -> count
        self.abstain_total: int = 0
        self.coverage_samples: list = []  # last N coverage values (0..1)
        self._max_samples = 500

    def record_claim(self, status: str) -> None:
        key = (status or "UNKNOWN").upper()
        self.claims_total[key] += 1
        logger.debug("council_claim status=%s", key)

    def record_abstain(self, reason: str = "") -> None:
        self.abstain_total += 1
        logger.info("council_abstain reason=%s", reason or "unspecified")

    def record_coverage(self, coverage: float) -> None:
        c = max(0.0, min(1.0, coverage))
        self.coverage_samples.append(c)
        if len(self.coverage_samples) > self._max_samples:
            self.coverage_samples = self.coverage_samples[-self._max_samples :]

    def snapshot(self) -> Dict[str, Any]:
        cov = self.coverage_samples
        avg = sum(cov) / len(cov) if cov else 0.0
        return {
            "claims_total": dict(self.claims_total),
            "abstain_total": self.abstain_total,
            "coverage_avg": round(avg, 4),
            "coverage_samples": len(cov),
        }


council_metrics = CouncilMetrics()
