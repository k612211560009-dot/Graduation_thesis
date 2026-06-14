from __future__ import annotations
import csv, logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)
DetectionKey = Tuple[str, str]   # (rule_id, object_id)


class EvaluationDataLoader:
    def __init__(self, ground_truth_path: str | Path,
                 detected_violations_path: str | Path) -> None:
        self.ground_truth_path = Path(ground_truth_path)
        self.detected_path     = Path(detected_violations_path)

    def load(self) -> Tuple[Set[DetectionKey], Set[DetectionKey]]:
        gt_set  = self._load_ground_truth()
        det_set = self._load_detected(gt_rules={k[0] for k in gt_set})
        logger.info("Evaluation data: %d GT violations, %d detected (filtered to GT rules).",
                    len(gt_set), len(det_set))
        return gt_set, det_set

    def load_per_rule(self) -> Dict[str, Tuple[Set[str], Set[str]]]:
        gt_set, det_set = self.load()
        rules = {k[0] for k in gt_set} | {k[0] for k in det_set}
        return {
            r: (
                {obj for (ru, obj) in gt_set  if ru == r},
                {obj for (ru, obj) in det_set if ru == r},
            )
            for r in sorted(rules)
        }

    # private
    def _load_ground_truth(self) -> Set[DetectionKey]:
        keys: Set[DetectionKey] = set()
        with self.ground_truth_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rid = row.get("RuleID","").strip()
                oid = row.get("ObjectID","").strip()
                if rid and oid and row.get("ExpectedViolation","").strip() == "1":
                    keys.add((rid, oid))
        logger.info("Ground truth loaded: %d keys from %d rules.",
                    len(keys), len({k[0] for k in keys}))
        return keys

    def _load_detected(self, gt_rules: Set[str]) -> Set[DetectionKey]:
        """Load detected violations, keeping only rules that exist in ground truth."""
        keys: Set[DetectionKey] = set()
        with self.detected_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rid = row.get("rule_id","").strip()
                oid = row.get("object_id","").strip()
                # Only include if this rule is in ground truth
                if rid and oid and rid in gt_rules:
                    keys.add((rid, oid))
        logger.info("Detected violations loaded: %d keys (filtered to GT rules: %s).",
                    len(keys), sorted(gt_rules))
        return keys
