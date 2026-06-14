from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from rule_design.rule_repository_builder import RuleRepository

logger = logging.getLogger(__name__)

class OperationalContextEnforcementEngine:

    # Potential impact templates per rule
    _IMPACT_TEMPLATES: Dict[str, str] = {
        "GR03": (
            "High frequency of non-standard communication channels reduces "
            "auditability and increases risk of undocumented commitments."
        ),
        "GR05": (
            "Vendor communications outside CRM may lead to unrecorded "
            "price changes or scope adjustments, creating contractual risk."
        ),
        "GR07": (
            "Quotation revisions without documented change reasons prevent "
            "traceability of commercial negotiations and audit trails."
        ),
        "GR08": (
            "Repeated BOM validation cycles without documented changes "
            "indicate quality control gaps and may delay production schedules."
        ),
        "GR10": (
            "Naming inconsistencies in master data create downstream "
            "reconciliation errors between engineering and procurement systems."
        ),
        "GR14": (
            "Delayed shipment status updates impair operational visibility "
            "and may cause stock-out events or missed customer commitments."
        ),
    }

    # Recommendation templates per rule
    _RECOMMENDATION_TEMPLATES: Dict[str, str] = {
        "GR03": (
            "1. Review and migrate all external communications to CRM. "
            "2. Brief team on approved communication channels. "
            "3. Manager to confirm if exceptions are justified."
        ),
        "GR05": (
            "1. Request vendor to use CRM portal for all formal communications. "
            "2. Retroactively document any commitments made outside CRM. "
            "3. Consider vendor training on portal usage."
        ),
        "GR07": (
            "1. Request vendor to resubmit quotation with formal change reasons. "
            "2. Validate that price/scope changes are intentional. "
            "3. Update negotiation log with documented rationale."
        ),
        "GR08": (
            "1. Review BOM change history to identify root cause of rework cycles. "
            "2. Require engineering sign-off before each re-validation. "
            "3. Assess impact on production timeline."
        ),
        "GR10": (
            "1. Cross-reference BOM with Product Master Data for naming alignment. "
            "2. Escalate to Master Data team for correction. "
            "3. Freeze BOM revisions until naming is resolved."
        ),
        "GR14": (
            "1. Contact logistics team to obtain current shipment status. "
            "2. Update CRM with latest status immediately. "
            "3. Assess customer communication requirements for delay."
        ),
    }

    def __init__(self, repository: RuleRepository) -> None:
        self.repository = repository
        self._violations: List[Dict[str, Any]] = []     # unified violation log
        self._packages: List[Dict[str, Any]] = []       # intervention packages
        self._package_counter = 0

        # Track context per PO for historical enrichment
        self._po_context: Dict[str, Dict[str, Any]] = {}

    # Ingestion methods

    def process_deterministic_violations(
        self, violations: List[Dict[str, Any]]
    ) -> None:
        for v in violations:
            self._violations.append(v)
            self._update_po_context(v["object_id"], v)
            logger.debug(
                "Hard Stop recorded: %s | %s | %s",
                v["rule_id"], v["object_id"], v["condition_met"],
            )

    def process_statistical_results(
        self, results: List[Dict[str, Any]]
    ) -> None:
        for r in results:
            # Log as violation regardless of level
            violation = self._stat_result_to_violation(r)
            self._violations.append(violation)
            self._update_po_context(r["object_id"], r)

            # Generate Intervention Package only at Critical level
            if r["threshold_level"] == "Critical":
                pkg = self._build_intervention_package(r)
                self._packages.append(pkg)
                logger.debug(
                    "Intervention Package generated: %s | %s | %s=%.2f (P95=%.2f)",
                    pkg["package_id"], r["rule_id"],
                    r["metric_name"], r["observed_value"], r["p95_threshold"],
                )

    # Output accessors

    def all_violations(self) -> List[Dict[str, Any]]:
        """Return the unified detected violations log."""
        return list(self._violations)

    def all_packages(self) -> List[Dict[str, Any]]:
        """Return all generated intervention packages."""
        return list(self._packages)

    # Internal helpers

    def _update_po_context(self, object_id: str, record: Dict[str, Any]) -> None:
        po_id = self._extract_po_id(object_id, record)
        if not po_id:
            return
        ctx = self._po_context.setdefault(po_id, {
            "violation_count": 0,
            "rule_ids": set(),
            "last_event": None,
            "actor": None,
        })
        ctx["violation_count"] += 1
        ctx["rule_ids"].add(record.get("rule_id", ""))
        ctx["last_event"] = record.get("timestamp")
        ctx["actor"] = record.get("actor") or ctx["actor"]

    @staticmethod
    def _extract_po_id(object_id: str, record: Dict[str, Any]) -> str:
        if "po_id" in record.get("attributes", {}):
            return record["attributes"]["po_id"]
        # Extract from composite IDs: VQ-PO-NTS-..., BOM-PO-NTS-..., SHP-PO-NTS-...
        if object_id.startswith(("VQ-", "BOM-", "SHP-")):
            return object_id.split("-", 1)[1]
        if object_id.startswith("PO-"):
            return object_id
        return object_id

    def _stat_result_to_violation(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a statistical threshold result into a violation record."""
        return {
            "violation_id": r.get("result_id", ""),
            "rule_id": r["rule_id"],
            "rule_name": r["rule_name"],
            "rule_category": r.get("rule_category", ""),
            "rule_type": "Statistical",
            "object_id": r["object_id"],
            "event_id": r["event_id"],
            "activity": r["activity"],
            "timestamp": r["timestamp"],
            "actor": r.get("actor"),
            "severity": r["severity"],
            "response_mode": r["response_mode"],
            "condition_met": r["condition_met"],
            "threshold_level": r["threshold_level"],
            "observed_value": r["observed_value"],
            "p90_threshold": r["p90_threshold"],
            "p95_threshold": r["p95_threshold"],
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_intervention_package(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Construct a rich Intervention Package for managerial escalation."""
        self._package_counter += 1
        pkg_id = f"IP-{self._package_counter:04d}"

        rule_id = r["rule_id"]
        object_id = r["object_id"]
        po_id = self._extract_po_id(object_id, r)
        ctx = self._po_context.get(po_id, {})

        historical_context = (
            f"PO {po_id} has accumulated {ctx.get('violation_count', 1)} "
            f"governance alert(s) across rules: "
            f"{', '.join(sorted(ctx.get('rule_ids', {rule_id})))}. "
            f"Last event timestamp: {ctx.get('last_event', r['timestamp'])}."
        )

        threshold_info = (
            f"P90 (Warning) = {r['p90_threshold']:.2f} | "
            f"P95 (Critical) = {r['p95_threshold']:.2f} | "
            f"Observed = {r['observed_value']:.2f} → {r['threshold_level']}"
        )

        return {
            "package_id": pkg_id,
            "po_id": po_id,
            "rule_id": rule_id,
            "rule_name": r["rule_name"],
            "severity": r["severity"],
            "triggered_metric": r["metric_name"],
            "threshold_level": r["threshold_level"],
            "observed_value": round(r["observed_value"], 4),
            "p90_threshold": round(r["p90_threshold"], 4),
            "p95_threshold": round(r["p95_threshold"], 4),
            "threshold_information": threshold_info,
            "related_objects": object_id,
            "responsible_actor": r.get("actor") or ctx.get("actor"),
            "historical_context": historical_context,
            "potential_operational_impact": self._IMPACT_TEMPLATES.get(
                rule_id, "Governance deviation detected – managerial review required."
            ),
            "recommendations": self._RECOMMENDATION_TEMPLATES.get(
                rule_id, "Review the deviation and take corrective action as appropriate."
            ),
            "timestamp": r["timestamp"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
