from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from rule_design.rule_loader import GovernanceRule

logger = logging.getLogger(__name__)


class RuleRepository:
    def __init__(self, rules: Iterable[GovernanceRule] = ()) -> None:
        self._index: Dict[str, GovernanceRule] = {}
        for rule in rules:
            self.add(rule)

    # Mutation

    def add(self, rule: GovernanceRule) -> None:
        """Add a rule to the repository (overwrites if same ID)."""
        if rule.rule_id in self._index:
            logger.warning("Duplicate rule ID %r – overwriting.", rule.rule_id)
        self._index[rule.rule_id] = rule

    # Queries

    def get(self, rule_id: str) -> Optional[GovernanceRule]:
        """Return the rule with the given ID, or *None* if not found."""
        return self._index.get(rule_id)

    def all_rules(self) -> List[GovernanceRule]:
        """Return all rules sorted by rule ID."""
        return sorted(self._index.values(), key=lambda r: r.rule_id)

    def deterministic_rules(self) -> List[GovernanceRule]:
        """Return only deterministic (Fixed) rules."""
        return [r for r in self.all_rules() if r.is_deterministic]

    def statistical_rules(self) -> List[GovernanceRule]:
        """Return only statistical rules."""
        return [r for r in self.all_rules() if r.is_statistical]

    def rules_by_category(self, category: str) -> List[GovernanceRule]:
        """Return rules belonging to *category* (case-insensitive)."""
        cat = category.strip().lower()
        return [r for r in self.all_rules() if r.category.lower() == cat]

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._index

    # Serialisation

    def to_csv(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "Rule ID", "Rule Name", "Rule Category", "Applicable Objects",
            "Monitoring Condition", "Threshold Type", "Severity",
            "Response Mode", "Managerial Intervention", "Is Deterministic",
        ]

        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for rule in self.all_rules():
                writer.writerow({
                    "Rule ID": rule.rule_id,
                    "Rule Name": rule.rule_name,
                    "Rule Category": rule.category,
                    "Applicable Objects": " / ".join(rule.applicable_objects),
                    "Monitoring Condition": rule.monitoring_condition,
                    "Threshold Type": rule.threshold_type,
                    "Severity": rule.severity,
                    "Response Mode": rule.response_mode,
                    "Managerial Intervention": "Yes" if rule.managerial_intervention else "No",
                    "Is Deterministic": "Yes" if rule.is_deterministic else "No",
                })

        logger.info("Rule repository written to %s (%d rules).", output_path, len(self))
        return output_path

    # Diagnostics

    def summary(self) -> str:
        """Return a short human-readable summary of the repository."""
        det = len(self.deterministic_rules())
        stat = len(self.statistical_rules())
        cats = {}
        for r in self.all_rules():
            cats[r.category] = cats.get(r.category, 0) + 1
        cat_str = ", ".join(f"{k}:{v}" for k, v in sorted(cats.items()))
        return (
            f"RuleRepository({len(self)} rules | "
            f"{det} deterministic, {stat} statistical | "
            f"categories: {cat_str})"
        )

# Builder functions

def build_repository(rules: Iterable[GovernanceRule]) -> RuleRepository:
    repo = RuleRepository(rules)
    logger.info("Built repository: %s", repo.summary())
    return repo
