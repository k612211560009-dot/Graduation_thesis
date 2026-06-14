#  Make project root importable from any working directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from typing import Any, Dict

from config import (
    GROUND_TRUTH_PATH, DETECTED_VIOLATIONS_PATH,
    CONFUSION_MATRIX_PATH, EVALUATION_RESULTS_PATH, OUTPUT_DIR,
)
from evaluation.evaluation_data_loader import EvaluationDataLoader
from evaluation.confusion_matrix import ConfusionMatrix
from evaluation.metrics import MetricsCalculator

#  Logging
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "evaluation.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_evaluation")


def run_evaluation(
    ground_truth_path=GROUND_TRUTH_PATH,
    detected_violations_path=DETECTED_VIOLATIONS_PATH,
    confusion_matrix_path=CONFUSION_MATRIX_PATH,
    evaluation_results_path=EVALUATION_RESULTS_PATH,
) -> Dict[str, Any]:
    logger.info("=== EVALUATION INSTANCE START ===")

    #  1. Load data
    loader = EvaluationDataLoader(ground_truth_path, detected_violations_path)
    ground_truth, detected = loader.load()

    #  2. Confusion matrix
    cm = ConfusionMatrix(ground_truth, detected)
    logger.info("Confusion matrix: %s", cm.summary())
    cm.to_csv(confusion_matrix_path)

    #  3. Metrics
    calc = MetricsCalculator(cm)
    calc.to_csv(evaluation_results_path)

    report = calc.report()
    print(report)
    logger.info("Metrics report:\n%s", report)

    logger.info("=== EVALUATION INSTANCE COMPLETE ===")

    return {
        "overall":  calc.overall(),
        "per_rule": calc.per_rule(),
        "cm_path":  confusion_matrix_path,
        "eval_path": evaluation_results_path,
    }


#  Run standalone
if __name__ == "__main__":
    # Guard: check prerequisites
    if not DETECTED_VIOLATIONS_PATH.exists():
        print(f"✗ Not found: {DETECTED_VIOLATIONS_PATH}")
        print("  → Run monitoring/run_monitoring.py first.")
        sys.exit(1)
    if not GROUND_TRUTH_PATH.exists():
        print(f"✗ Not found: {GROUND_TRUTH_PATH}")
        sys.exit(1)

    result = run_evaluation()
    o = result["overall"]
    print(f"\n Precision : {o['precision']:.4f}")
    print(f" Recall    : {o['recall']:.4f}")
    print(f" F1-score  : {o['f1_score']:.4f}")
    print(f" Outputs   → {OUTPUT_DIR}")
