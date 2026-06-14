from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, Set, Tuple

logger = logging.getLogger(__name__)

# (rule_id, object_id)
DetectionKey = Tuple[str, str]


class ConfusionMatrix:
    def __init__(
        self,
        ground_truth: Set[DetectionKey],
        detected: Set[DetectionKey],
    ) -> None:
        self.ground_truth = ground_truth
        self.detected = detected

        # Compute overall counts
        self.tp: Set[DetectionKey] = ground_truth & detected
        self.fp: Set[DetectionKey] = detected - ground_truth
        self.fn: Set[DetectionKey] = ground_truth - detected

        # TN: neither expected nor detected (per-rule universe)
        universe = ground_truth | detected
        all_objects = {obj for (_, obj) in universe}
        all_rules = {r for (r, _) in universe}
        all_pairs: Set[DetectionKey] = {
            (r, obj) for r in all_rules for obj in all_objects
        }
        self.tn: Set[DetectionKey] = all_pairs - ground_truth - detected

    # Counts

    @property
    def tp_count(self) -> int:
        return len(self.tp)

    @property
    def fp_count(self) -> int:
        return len(self.fp)

    @property
    def fn_count(self) -> int:
        return len(self.fn)

    @property
    def tn_count(self) -> int:
        return len(self.tn)

    # Per-rule breakdown

    def per_rule(self) -> Dict[str, Dict[str, int]]:
        all_rules = sorted(
            {r for (r, _) in self.ground_truth | self.detected}
        )
        result: Dict[str, Dict[str, int]] = {}

        for rule_id in all_rules:
            gt_rule = {obj for (r, obj) in self.ground_truth if r == rule_id}
            det_rule = {obj for (r, obj) in self.detected if r == rule_id}
            all_objs = gt_rule | det_rule

            tp = len(gt_rule & det_rule)
            fp = len(det_rule - gt_rule)
            fn = len(gt_rule - det_rule)
            tn = 0  # TN is not meaningful for per-rule per-object without full universe

            result[rule_id] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}

        return result

    # String representation

    def summary(self) -> str:
        return (
            f"ConfusionMatrix(TP={self.tp_count}, FP={self.fp_count}, "
            f"FN={self.fn_count}, TN={self.tn_count})"
        )

    # Serialisation

    def to_csv(self, output_path: str | Path) -> Path:
        """Write the per-rule confusion matrix to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        per_rule = self.per_rule()
        fieldnames = ["rule_id", "tp", "fp", "fn", "tn"]

        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for rule_id, counts in per_rule.items():
                writer.writerow({"rule_id": rule_id, **counts})
            # Overall row
            writer.writerow({
                "rule_id": "OVERALL",
                "tp": self.tp_count,
                "fp": self.fp_count,
                "fn": self.fn_count,
                "tn": self.tn_count,
            })

        logger.info("Confusion matrix written to %s.", output_path)
        return output_path
