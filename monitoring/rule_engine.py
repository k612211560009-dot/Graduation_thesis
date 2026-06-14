from __future__ import annotations
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rule_design.rule_loader import GovernanceRule
from rule_design.rule_repository_builder import RuleRepository
from monitoring.event_stream_processor import EventStreamProcessor

logger = logging.getLogger(__name__)

# Required lifecycle events for DG13 traceability check
DG13_REQUIRED_EVENTS = {
    "ReviewOrderInformation",
    "ValidateBOM",
    "ValidateQuotation",
    "ApproveFinancialDocuments",
    "CloseOrder",
}


class RuleEngine:
    def __init__(self, repository: RuleRepository, processor: EventStreamProcessor) -> None:
        self.repository   = repository
        self.processor    = processor
        self._det_rules   = repository.deterministic_rules()
        self._violations: List[Dict] = []
        self._counter     = 0

        # State for multi-event rules
        self._po_event_types: Dict[str, set] = defaultdict(set)    # DG13
        self._vq_has_po_ref:  Dict[str, bool] = {}                 # DG06/DG12
        self._bom_versions:   Dict[str, set]  = defaultdict(set)   # DG11
        self._dg13_reported:  set = set()

        logger.info("RuleEngine: %d deterministic rules: %s",
                    len(self._det_rules), [r.rule_id for r in self._det_rules])

    # public
    def evaluate(self, event: Dict) -> List[Dict]:
        new_v: List[Dict] = []
        etype = event.get("type", "")
        ea    = lambda name: EventStreamProcessor.get_event_attr(event, name)
        rel   = lambda prefix=None: EventStreamProcessor.get_related_ids(event, prefix)

        # Track PO lifecycle for DG13
        for po_id in rel("PO-NTS-"):
            self._po_event_types[po_id].add(etype)

        for rule in self._det_rules:
            v = self._check(rule, event, etype, ea, rel)
            if v:
                new_v.append(v)
                self._violations.append(v)
        return new_v

    def finalize(self) -> List[Dict]:
        new_v: List[Dict] = []
        rule_dg13 = self.repository.get("DG13")
        if rule_dg13:
            for po_id, seen_types in self._po_event_types.items():
                missing = DG13_REQUIRED_EVENTS - seen_types
                if missing and po_id not in self._dg13_reported:
                    self._dg13_reported.add(po_id)
                    v = self._make(rule_dg13, po_id, "", "",
                                  f"Traceability chain incomplete – missing: {sorted(missing)}")
                    new_v.append(v)
                    self._violations.append(v)
        return new_v

    def all_violations(self) -> List[Dict]:
        return list(self._violations)

    # dispatch─
    def _check(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        dispatch = {
            "DG01": self._dg01,
            "DG06": self._dg06,
            "DG09": self._dg09,
            "DG11": self._dg11,
            "DG12": self._dg12,
            "DG15": self._dg15,
        }
        fn = dispatch.get(rule.rule_id)
        return fn(rule, event, etype, ea, rel) if fn else None

    # DG0
    def _dg01(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype != "ReviewOrderInformation":
            return None
        if ea("status") == "Incomplete":
            po_ids = rel("PO-NTS-")
            if po_ids:
                return self._make(rule, po_ids[0], event["id"], event["time"],
                                  "ReviewOrderInformation status=Incomplete")
        return None

    # DG06 – VQ must have been requested via RequestVendorQuote
    def _dg06(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype == "RequestVendorQuote":
            for vq_id in rel("VQ-"):
                self._vq_has_po_ref[vq_id] = True
        if etype == "ReceiveVendorQuotation":
            for vq_id in rel("VQ-"):
                if not self._vq_has_po_ref.get(vq_id, False):
                    return self._make(rule, vq_id, event["id"], event["time"],
                                      "VendorQuotation received with no prior RequestVendorQuote")
        return None

    # DG09 – ValidateBOM = Incomplete
    def _dg09(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype != "ValidateBOM":
            return None
        if ea("status") == "Incomplete":
            bom_ids = rel("BOM-")
            if bom_ids:
                return self._make(rule, bom_ids[0], event["id"], event["time"],
                                  "ValidateBOM status=Incomplete (no documented justification)")
        return None

    # DG11 – multiple active BOM versions
    def _dg11(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype != "ValidateBOM":
            return None
        ver = ea("version")
        if not ver:
            return None
        for bom_id in rel("BOM-"):
            self._bom_versions[bom_id].add(ver)
            if len(self._bom_versions[bom_id]) > 1:
                return self._make(rule, bom_id, event["id"], event["time"],
                                  f"Multiple active BOM versions: {sorted(self._bom_versions[bom_id])}")
        return None

    # DG12 – document lineage: VQ must link to a PO
    def _dg12(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype != "ReceiveVendorQuotation":
            return None
        vq_ids = rel("VQ-")
        po_ids = rel("PO-NTS-")
        # If no PO reference in this event's relationships → lineage broken
        if vq_ids and not po_ids:
            return self._make(rule, vq_ids[0], event["id"], event["time"],
                              "VendorQuotation received with no PO in relationships (lineage broken)")
        return None

    # DG15 – ownership change without reassignment doc─
    _dg15_last_dept: Dict[str, str] = {}

    def _dg15(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        dept = ea("department")
        if not dept:
            return None
        for po_id in rel("PO-NTS-"):
            prev = self._dg15_last_dept.get(po_id)
            if prev and prev != dept:
                # Department changed without a formal reassignment event
                v = self._make(rule, po_id, event["id"], event["time"],
                               f"Department changed {prev}→{dept} without reassignment doc")
                self._dg15_last_dept[po_id] = dept
                return v
            self._dg15_last_dept[po_id] = dept
        return None

    # factory
    def _make(self, rule, obj_id, event_id, timestamp, condition) -> Dict:
        self._counter += 1
        return {
            "violation_id":  f"VIO-DET-{self._counter:04d}",
            "rule_id":       rule.rule_id,
            "rule_name":     rule.rule_name,
            "rule_category": rule.category,
            "rule_type":     "Deterministic",
            "object_id":     obj_id,
            "event_id":      event_id,
            "activity":      "",
            "timestamp":     timestamp,
            "actor":         None,
            "severity":      rule.severity,
            "response_mode": rule.response_mode,
            "condition_met": condition,
            "threshold_level":  "",
            "observed_value":   "",
            "p90_threshold":    "",
            "p95_threshold":    "",
            "detected_at":   datetime.now(timezone.utc).isoformat(),
        }
