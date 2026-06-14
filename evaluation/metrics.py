from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from evaluation.confusion_matrix import ConfusionMatrix

logger = logging.getLogger(__name__)


def precision(tp: int, fp: int) -> float:
    """Precision = TP / (TP + FP).  Returns 0.0 if denominator is zero."""
    denom = tp + fp
    return tp / denom if denom > 0 else 0.0


def recall(tp: int, fn: int) -> float:
    """Recall = TP / (TP + FN).  Returns 0.0 if denominator is zero."""
    denom = tp + fn
    return tp / denom if denom > 0 else 0.0


def f1_score(prec: float, rec: float) -> float:
    """F1 = 2 * (Precision * Recall) / (Precision + Recall).  Returns 0.0 if both are zero."""
    denom = prec + rec
    return 2 * prec * rec / denom if denom > 0 else 0.0


class MetricsCalculator:
    def __init__(self, confusion_matrix: ConfusionMatrix) -> None:
        self.cm = confusion_matrix

    # Overall metrics

    def overall(self) -> Dict[str, Any]:
        """Return overall Precision, Recall, F1 as a dict."""
        tp = self.cm.tp_count
        fp = self.cm.fp_count
        fn = self.cm.fn_count
        tn = self.cm.tn_count
        prec = precision(tp, fp)
        rec = recall(tp, fn)
        f1 = f1_score(prec, rec)

        return {
            "scope": "OVERALL",
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
        }

    # Per-rule metrics

    def per_rule(self) -> Dict[str, Dict[str, Any]]:
        """Return per-rule Precision, Recall, F1 as a nested dict."""
        per_rule_cm = self.cm.per_rule()
        results: Dict[str, Dict[str, Any]] = {}

        for rule_id, counts in per_rule_cm.items():
            tp = counts["tp"]
            fp = counts["fp"]
            fn = counts["fn"]
            tn = counts["tn"]
            prec = precision(tp, fp)
            rec = recall(tp, fn)
            f1 = f1_score(prec, rec)
            results[rule_id] = {
                "scope": rule_id,
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
            }

        return results

    # Serialisation

    def to_csv(self, output_path: str | Path) -> Path:
        """Write the full metrics table (per-rule + overall) to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["scope", "tp", "fp", "fn", "tn", "precision", "recall", "f1_score"]

        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted(self.per_rule().values(), key=lambda r: r["scope"]):
                writer.writerow(row)
            writer.writerow(self.overall())

        logger.info("Evaluation metrics written to %s.", output_path)
        return output_path

    # Console report

    def report(self) -> str:
        """Return a formatted metrics report string."""
        lines = [
            "=" * 60,
            "  EVALUATION METRICS REPORT",
            "=" * 60,
            f"  {'Rule':<12} {'TP':>5} {'FP':>5} {'FN':>5} {'Precision':>10} {'Recall':>10} {'F1':>10}",
            "  " + "-" * 56,
        ]

        for rule_id, m in sorted(self.per_rule().items()):
            lines.append(
                f"  {rule_id:<12} {m['tp']:>5} {m['fp']:>5} {m['fn']:>5} "
                f"{m['precision']:>10.4f} {m['recall']:>10.4f} {m['f1_score']:>10.4f}"
            )

        o = self.overall()
        lines += [
            "  " + "-" * 56,
            f"  {'OVERALL':<12} {o['tp']:>5} {o['fp']:>5} {o['fn']:>5} "
            f"{o['precision']:>10.4f} {o['recall']:>10.4f} {o['f1_score']:>10.4f}",
            "=" * 60,
        ]
        return "\n".join(lines)
