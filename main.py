# Make project root importable 
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
import time

from config import (
    RULE_SPEC_PATH, OCEL_PATH, GROUND_TRUTH_PATH,
    DETECTED_VIOLATIONS_PATH, OUTPUT_DIR,
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "framework.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def main():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("  CRM-BASED MONITORING FRAMEWORK")
    logger.info("=" * 70)

    # Instance 1: Rule Design
    from rule_design.run_rule_design import run_rule_design
    t1 = time.time()
    repository = run_rule_design()
    logger.info("Rule Design done in %.2fs", time.time() - t1)

    # Instance 2: Monitoring
    from monitoring.run_monitoring import run_monitoring
    t2 = time.time()
    result = run_monitoring(repository=repository)
    s = result["stats"]
    logger.info("Monitoring done in %.2fs | violations=%d  packages=%d",
                time.time() - t2, s["total_violations"], s["intervention_packages"])

    # Instance 3: Evaluation
    if DETECTED_VIOLATIONS_PATH.exists() and GROUND_TRUTH_PATH.exists():
        from evaluation.run_evaluation import run_evaluation
        t3 = time.time()
        ev = run_evaluation()
        o  = ev["overall"]
        logger.info("Evaluation done in %.2fs | P=%.4f  R=%.4f  F1=%.4f",
                    time.time() - t3, o["precision"], o["recall"], o["f1_score"])
    else:
        logger.warning("Skipping evaluation — missing ground truth or detections.")

    logger.info("=" * 70)
    logger.info("  Total runtime: %.2fs", time.time() - t0)
    logger.info("  Outputs → %s", OUTPUT_DIR.resolve())
    logger.info("=" * 70)

    print("\nOutput files:")
    for f in sorted(OUTPUT_DIR.glob("*.*")):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
