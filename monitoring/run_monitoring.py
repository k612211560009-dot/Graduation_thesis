import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import csv, logging
from typing import Any, Dict, List

from config import (OCEL_PATH, RULE_SPEC_PATH,
                    DETECTED_VIOLATIONS_PATH, INTERVENTION_PKG_PATH, OUTPUT_DIR)
from rule_design.rule_loader import load_rules
from rule_design.rule_repository_builder import build_repository, RuleRepository
from monitoring.event_stream_processor import EventStreamProcessor
from monitoring.rule_engine import RuleEngine
from monitoring.threshold_engine import ThresholdEngine
from monitoring.operational_context_enforcement_engine import OperationalContextEnforcementEngine

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "monitoring.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_monitoring")

VIOLATION_FIELDS = [
    "violation_id","rule_id","rule_name","rule_category","rule_type",
    "object_id","event_id","activity","timestamp","actor",
    "severity","response_mode","condition_met",
    "threshold_level","observed_value","p90_threshold","p95_threshold","detected_at",
]
PACKAGE_FIELDS = [
    "package_id","po_id","rule_id","rule_name","severity",
    "triggered_metric","threshold_level","observed_value","p90_threshold","p95_threshold",
    "threshold_information","related_objects","responsible_actor",
    "historical_context","potential_operational_impact","recommendations",
    "timestamp","generated_at",
]


def run_monitoring(ocel_path=OCEL_PATH, output_dir=OUTPUT_DIR,
                   repository: RuleRepository = None) -> Dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("=== MONITORING INSTANCE START ===")

    # 1. Repository
    if repository is None:
        repository = build_repository(load_rules(RULE_SPEC_PATH))

    # 2. Load OCEL
    processor = EventStreamProcessor(ocel_path)
    processor.load()
    all_events: List[Dict] = processor.events_as_list()
    logger.info("Events to process: %d", len(all_events))

    # 3. Engines
    rule_engine      = RuleEngine(repository, processor)
    threshold_engine = ThresholdEngine(repository, processor)
    ocee             = OperationalContextEnforcementEngine(repository)

    # 4. Calibrate thresholds
    threshold_engine.calibrate(all_events)

    # 5. Stream events
    logger.info("Processing event stream…")
    for i, event in enumerate(all_events, 1):
        if i % 100 == 0:
            logger.info("  %d / %d", i, len(all_events))
        ocee.process_deterministic_violations(rule_engine.evaluate(event))
        ocee.process_statistical_results(threshold_engine.evaluate(event))

    # 6. Finalize: post-stream rules (DG13 lifecycle, DG08/DG14 object attrs)
    logger.info("Finalizing post-stream rules…")
    ocee.process_deterministic_violations(rule_engine.finalize())
    ocee.process_statistical_results(threshold_engine.evaluate_objects())

    # 7. Outputs
    violations = ocee.all_violations()
    packages   = ocee.all_packages()

    _write_csv(violations, output_dir / "detected_violations.csv", VIOLATION_FIELDS)
    _write_csv(packages,   output_dir / "intervention_packages.csv", PACKAGE_FIELDS)

    stats = {
        "total_events":                len(all_events),
        "total_violations":            len(violations),
        "deterministic_violations":    sum(1 for v in violations if v.get("rule_type") == "Deterministic"),
        "statistical_violations":      sum(1 for v in violations if v.get("rule_type") == "Statistical"),
        "critical_threshold_breaches": sum(1 for v in violations if v.get("threshold_level") == "Critical"),
        "warning_threshold_breaches":  sum(1 for v in violations if v.get("threshold_level") == "Warning"),
        "intervention_packages":       len(packages),
    }
    logger.info("=== MONITORING COMPLETE ===")
    for k, v in stats.items():
        logger.info("  %-35s: %s", k, v)

    return {"violations": violations, "packages": packages, "stats": stats}


def _write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    logger.info("Written → %s  (%d rows)", path, len(rows))


if __name__ == "__main__":
    r = run_monitoring()
    s = r["stats"]
    print(f"\n Violations: {s['total_violations']}  |  Packages: {s['intervention_packages']}")
    print(f" Output → {OUTPUT_DIR}")
