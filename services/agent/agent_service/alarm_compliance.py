"""ISA-18.2 / EEMUA 191 compliance validator.

Checks an alarm database against ISA-18.2 benchmarks and produces a compliance
report with pass/fail status for each metric.

ISA-18.2 Target Benchmarks:
    - Average alarm rate: < 150 alarms/day (target: 144 per EEMUA 191)
    - Peak rate: < 10 alarms per 10 minutes (EEMUA 191)
    - Stale alarm %: < 5% of total
    - Rationalization: 100% of alarms must have rationalization text
    - Chatter: no alarm should re-trigger > 2 times in 5 minutes
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .alarm_manager import AlarmManager


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ISA-18.2 / EEMUA 191 compliance thresholds
MAX_AVG_ALARMS_PER_DAY = 150       # ISA-18.2: target 144, allow up to 150
MAX_PEAK_ALARMS_PER_10MIN = 10     # EEMUA 191
MAX_STALE_PCT = 5.0                # ISA-18.2
MAX_CHATTER_OCCURRENCES = 2        # > 2 occurrences in 5 min = chatter violation
CHATTER_WINDOW_SECONDS = 300       # 5 minutes


@dataclass
class ComplianceCheck:
    """Result of a single compliance check."""
    name: str
    description: str
    passed: bool
    actual_value: float
    threshold: float
    unit: str


@dataclass
class ComplianceReport:
    """Full ISA-18.2 compliance report."""
    checks: list[ComplianceCheck] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    overall_compliant: bool = False
    generated_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def add_check(self, check: ComplianceCheck):
        self.checks.append(check)
        if check.passed:
            self.passed_count += 1
        else:
            self.failed_count += 1

    def finalize(self):
        self.overall_compliant = self.failed_count == 0


def validate_compliance(manager: AlarmManager) -> ComplianceReport:
    """Validate an AlarmManager against ISA-18.2 benchmarks.

    Args:
        manager: An AlarmManager instance with alarms populated.

    Returns:
        ComplianceReport with pass/fail for each benchmark.
    """
    report = ComplianceReport()
    metrics = manager.get_performance_metrics()
    rationalization = manager.get_rationalization_report()

    # 1. Average alarms per day < 150
    report.add_check(ComplianceCheck(
        name="avg_alarm_rate",
        description="Average alarms per day must be < 150 (ISA-18.2 target: 144)",
        passed=metrics["average_alarms_per_day"] < MAX_AVG_ALARMS_PER_DAY,
        actual_value=metrics["average_alarms_per_day"],
        threshold=MAX_AVG_ALARMS_PER_DAY,
        unit="alarms/day",
    ))

    # 2. Peak alarm rate < 10 per 10 min
    report.add_check(ComplianceCheck(
        name="peak_alarm_rate",
        description="Peak alarm rate must be < 10 per 10 minutes (EEMUA 191)",
        passed=metrics["peak_alarm_rate_10min"] < MAX_PEAK_ALARMS_PER_10MIN,
        actual_value=float(metrics["peak_alarm_rate_10min"]),
        threshold=float(MAX_PEAK_ALARMS_PER_10MIN),
        unit="alarms/10min",
    ))

    # 3. Stale alarm % < 5%
    report.add_check(ComplianceCheck(
        name="stale_alarm_pct",
        description="Stale alarm percentage must be < 5% (ISA-18.2)",
        passed=metrics["stale_alarm_pct"] < MAX_STALE_PCT,
        actual_value=metrics["stale_alarm_pct"],
        threshold=MAX_STALE_PCT,
        unit="%",
    ))

    # 4. All alarms must be rationalized
    total = len(rationalization)
    rationalized = sum(1 for r in rationalization if r["is_rationalized"])
    rationalized_pct = (rationalized / total * 100) if total > 0 else 100.0
    report.add_check(ComplianceCheck(
        name="rationalization_coverage",
        description="100% of alarms must have rationalization text (ISA-18.2)",
        passed=total == 0 or rationalized == total,
        actual_value=rationalized_pct,
        threshold=100.0,
        unit="%",
    ))

    # 5. No chattering alarms
    chatter_count = sum(1 for r in rationalization if r["is_chatter"])
    report.add_check(ComplianceCheck(
        name="chatter_free",
        description=f"No alarm should re-trigger > {MAX_CHATTER_OCCURRENCES} times in 5 min (ISA-18.2)",
        passed=chatter_count == 0,
        actual_value=float(chatter_count),
        threshold=0.0,
        unit="alarms",
    ))

    report.finalize()
    return report


def get_unrationalized_alarms(manager: AlarmManager) -> list[dict]:
    """Return all alarms that lack rationalization text.

    This is useful for generating a punch list during commissioning.
    """
    report = manager.get_rationalization_report()
    return [r for r in report if not r["is_rationalized"]]


def get_chattering_alarms(manager: AlarmManager) -> list[dict]:
    """Return all alarms flagged as chattering.

    These should be investigated for re-tuning or suppression.
    """
    report = manager.get_rationalization_report()
    return [r for r in report if r["is_chatter"]]
