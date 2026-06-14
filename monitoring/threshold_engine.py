from __future__ import annotations
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np

from rule_design.rule_loader import GovernanceRule
from rule_design.rule_repository_builder import RuleRepository
from monitoring.event_stream_processor import EventStreamProcessor

logger = logging.getLogger(__name__)

# Non-standard channels (ERP and CRM are standard)
NONSTD_CHANNELS_PO  = {"Zalo", "WhatsApp"}  # DG03 – only Zalo/WhatsApp
NONSTD_CHANNELS_VQ  = {"Zalo", "WhatsApp"}  # DG05 – only Zalo/WhatsApp (Email is acceptable)
COMM_EVENT_TYPES = {
    "ConfirmCustomerOrder", "SubmitPurchaseOrder",
    "RequestAdditionalInformation", "RequestVendorQuote",
    "RequestTechnicalClarification", "CreateVendorOrder",
}
NAMING_KEYWORDS = ["name", "model", "naming", "mismatch", "does not match", "inconsist"]


class ThresholdEngine:
    def __init__(self, repository: RuleRepository, processor: EventStreamProcessor) -> None:
        self.repository   = repository
        self.processor    = processor
        self._stat_rules  = repository.statistical_rules()
        self._thresholds: Dict[str, Dict[str, float]] = {}
        self._results:    List[Dict] = []
        self._counter     = 0

        # Runtime streaming accumulators
        self._po_nonstd_comm:    Dict[str, int]   = defaultdict(int)  # DG03
        self._vq_nonstd_comm:    Dict[str, int]   = defaultdict(int)  # DG05
        self._bom_undoc_rev:     Dict[str, int]   = defaultdict(int)  # DG07
        self._po_naming_issues:  Dict[str, int]   = defaultdict(int)  # DG10

        # Object-attribute based (filled at calibration, evaluated after stream)
        self._bom_revision_count: Dict[str, int]   = {}  # bom_id → revisionCount (DG08)
        self._shp_transit_days:   Dict[str, float] = {}  # shp_id → transitDays   (DG14)

        logger.info("ThresholdEngine: %d statistical rules: %s",
                    len(self._stat_rules), [r.rule_id for r in self._stat_rules])

    # calibration
    def calibrate(self, events: List[Dict]) -> None:
        """Derive P90/P95 from all events + object attributes."""
        logger.info("Calibrating thresholds from %d events…", len(events))
        obj_map = self.processor.get_all_objects()

        # Calibration accumulators
        po_nonstd:    Dict[str, int]   = defaultdict(int)
        vq_nonstd:    Dict[str, int]   = defaultdict(int)
        bom_undoc:    Dict[str, int]   = defaultdict(int)
        po_naming:    Dict[str, int]   = defaultdict(int)
        bom_rev:      Dict[str, int]   = {}
        shp_days:     Dict[str, float] = {}

        for e in events:
            etype = e.get("type", "")
            ea    = lambda n, _e=e: EventStreamProcessor.get_event_attr(_e, n)
            rel   = lambda pfx=None, _e=e: EventStreamProcessor.get_related_ids(_e, pfx)

            # DG03 – non-standard comm channel per PO
            if etype in COMM_EVENT_TYPES and ea("channel") in NONSTD_CHANNELS_PO:
                for po in rel("PO-NTS-"):
                    po_nonstd[po] += 1

            # DG05 – vendor quote via non-ERP/CRM channel
            if etype in ("RequestVendorQuote", "CreateVendorOrder"):
                ch = ea("channel")
                if ch in NONSTD_CHANNELS_VQ:
                    for vq in rel("VQ-"):
                        vq_nonstd[vq] += 1

            # DG07 – BOM revision without documented reason
            if etype == "ValidateBOM":
                ver = ea("version") or "v1.0"
                if ver != "v1.0":
                    for bom in rel("BOM-"):
                        bom_undoc[bom] += 1

            if etype == "ReturnOrderForRevision":
                reason = (ea("reason") or "").strip()
                # If reason exists → documented → cancel undoc flag for related BOMs
                if reason:
                    for po in rel("PO-NTS-"):
                        bom_id = po.replace("PO-NTS-", "BOM-PO-NTS-")
                        bom_undoc[bom_id] = max(0, bom_undoc[bom_id] - 1)

            # DG10 – naming inconsistency in return reason
            if etype == "ReturnOrderForRevision":
                reason = (ea("reason") or "").lower()
                if any(k in reason for k in NAMING_KEYWORDS):
                    for po in rel("PO-NTS-"):
                        po_naming[po] += 1

        # From object attributes
        for oid, obj in obj_map.items():
            otype = obj.get("type", "")
            get_a = lambda n, _o=obj: next(
                (a["value"] for a in _o.get("attributes", []) if a["name"] == n), None)

            if otype == "BOM":
                rc = get_a("revisionCount")
                if rc is not None:
                    bom_rev[oid] = int(rc)

            if otype == "ShipmentDocument":
                td = get_a("transitDays")
                if td is not None:
                    shp_days[oid] = float(td)

        # Cache for evaluate_objects()
        self._bom_revision_count = bom_rev
        self._shp_transit_days   = shp_days

        # Build metric arrays
        all_po  = [oid for oid, o in obj_map.items() if o.get("type") == "PurchaseOrder"]
        all_vq  = [oid for oid, o in obj_map.items() if o.get("type") == "VendorQuotation"]
        all_bom = [oid for oid, o in obj_map.items() if o.get("type") == "BOM"]

        metrics = {
            "DG03": [float(po_nonstd.get(p, 0))  for p in all_po],
            "DG05": [float(vq_nonstd.get(v, 0))  for v in all_vq],
            "DG07": [float(bom_undoc.get(b, 0))  for b in all_bom],
            "DG08": [float(bom_rev.get(b, 1))    for b in all_bom],
            "DG10": [float(po_naming.get(p, 0))  for p in all_po],
            "DG14": list(shp_days.values()),
        }

        for rule_id, values in metrics.items():
            arr = np.array(values, dtype=float)
            nonzero = arr[arr > 0]
            if len(nonzero) < 2:
                # Not enough variation – use min nonzero as threshold so violations fire
                p90 = p95 = float(nonzero[0]) if len(nonzero) else 0.5
            else:
                p90 = float(np.percentile(arr, 90))
                p95 = float(np.percentile(arr, 95))
            self._thresholds[rule_id] = {"p90": p90, "p95": p95}
            logger.info("  %s: P90=%.2f  P95=%.2f  (n=%d, nonzero=%d)",
                        rule_id, p90, p95, len(values), len(nonzero))

    def get_thresholds(self) -> Dict:
        return dict(self._thresholds)

    # streaming evaluation
    def evaluate(self, event: Dict) -> List[Dict]:
        results = []
        etype = event.get("type", "")
        ea    = lambda n: EventStreamProcessor.get_event_attr(event, n)
        rel   = lambda pfx=None: EventStreamProcessor.get_related_ids(event, pfx)

        for rule in self._stat_rules:
            if rule.rule_id in ("DG08", "DG14"):
                continue  # object-attribute rules – handled in evaluate_objects()
            r = self._check(rule, event, etype, ea, rel)
            if r:
                results.append(r)
                self._results.append(r)
        return results

    def evaluate_objects(self) -> List[Dict]:
        results = []
        rule_dg08 = self.repository.get("DG08")
        rule_dg14 = self.repository.get("DG14")

        # DG08: BOM.revisionCount > 1 → report on PO level (GT uses PO)
        if rule_dg08:
            for bom_id, rc in self._bom_revision_count.items():
                if rc > 1:
                    # Map BOM-PO-NTS-2026-XXX → PO-NTS-2026-XXX
                    po_id = bom_id.replace("BOM-PO-NTS-", "PO-NTS-")
                    r = self._make_result(
                        rule_dg08, po_id, "", "",
                        metric_name="bom_revision_count",
                        observed_value=float(rc),
                        condition=f"BOM {bom_id} revisionCount={rc} — repeated rework without full justification",
                    )
                    if r:
                        results.append(r)
                        self._results.append(r)

        # DG14: ShipmentDocument.transitDays > threshold
        if rule_dg14:
            for shp_id, td in self._shp_transit_days.items():
                r = self._make_result(
                    rule_dg14, shp_id, "", "",
                    metric_name="transit_days",
                    observed_value=td,
                    condition=f"transitDays={td} for {shp_id}",
                )
                if r:
                    results.append(r)
                    self._results.append(r)

        return results

    def all_results(self) -> List[Dict]:
        return list(self._results)

    # per-rule streaming checkers─
    def _check(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        dispatch = {
            "DG03": self._dg03,
            "DG05": self._dg05,
            "DG07": self._dg07,
            "DG10": self._dg10,
        }
        fn = dispatch.get(rule.rule_id)
        return fn(rule, event, etype, ea, rel) if fn else None

    def _dg03(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype not in COMM_EVENT_TYPES:
            return None
        if ea("channel") not in NONSTD_CHANNELS_PO:
            return None
        po_ids = rel("PO-NTS-")
        if not po_ids:
            return None
        po_id = po_ids[0]
        self._po_nonstd_comm[po_id] += 1
        return self._make_result(
            rule, po_id, event["id"], event["time"],
            metric_name="nonstd_comm_count",
            observed_value=float(self._po_nonstd_comm[po_id]),
            condition=f"Communication via {ea('channel')} (Zalo/WhatsApp); count={self._po_nonstd_comm[po_id]}",
        )

    def _dg05(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype not in ("RequestVendorQuote", "CreateVendorOrder"):
            return None
        ch = ea("channel")
        if ch not in NONSTD_CHANNELS_VQ:
            return None
        vq_ids = rel("VQ-")
        if not vq_ids:
            return None
        vq_id = vq_ids[0]
        self._vq_nonstd_comm[vq_id] += 1
        return self._make_result(
            rule, vq_id, event["id"], event["time"],
            metric_name="vendor_nonstd_comm_count",
            observed_value=float(self._vq_nonstd_comm[vq_id]),
            condition=f"Vendor quote via {ch} (non-ERP/CRM); count={self._vq_nonstd_comm[vq_id]}",
        )

    def _dg07(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype != "ValidateBOM":
            return None
        ver = ea("version") or "v1.0"
        if ver == "v1.0":
            return None
        bom_ids = rel("BOM-")
        if not bom_ids:
            return None
        bom_id = bom_ids[0]
        self._bom_undoc_rev[bom_id] += 1
        return self._make_result(
            rule, bom_id, event["id"], event["time"],
            metric_name="undocumented_bom_revision",
            observed_value=float(self._bom_undoc_rev[bom_id]),
            condition=f"ValidateBOM version={ver} without ReturnOrderForRevision reason",
        )

    def _dg10(self, rule, event, etype, ea, rel) -> Optional[Dict]:
        if etype != "ReturnOrderForRevision":
            return None
        reason = (ea("reason") or "").lower()
        if not any(k in reason for k in NAMING_KEYWORDS):
            return None
        po_ids = rel("PO-NTS-")
        if not po_ids:
            return None
        po_id = po_ids[0]
        self._po_naming_issues[po_id] += 1
        return self._make_result(
            rule, po_id, event["id"], event["time"],
            metric_name="naming_inconsistency_count",
            observed_value=float(self._po_naming_issues[po_id]),
            condition=f"ReturnOrderForRevision reason contains naming mismatch: \"{ea('reason')}\"",
        )

    # result factory
    def _make_result(self, rule, obj_id, event_id, timestamp,
                     metric_name, observed_value, condition) -> Optional[Dict]:
        thr = self._thresholds.get(rule.rule_id, {"p90": 0.5, "p95": 1.0})
        p90, p95 = thr["p90"], thr["p95"]

        if observed_value > p95:
            level = "Critical"
        elif observed_value >= p90 and p90 > 0:
            level = "Warning"
        else:
            return None

        self._counter += 1
        return {
            "result_id":       f"STAT-{self._counter:04d}",
            "rule_id":         rule.rule_id,
            "rule_name":       rule.rule_name,
            "rule_category":   rule.category,
            "rule_type":       "Statistical",
            "object_id":       obj_id,
            "event_id":        event_id,
            "activity":        "",
            "timestamp":       timestamp,
            "actor":           None,
            "metric_name":     metric_name,
            "observed_value":  observed_value,
            "p90_threshold":   p90,
            "p95_threshold":   p95,
            "threshold_level": level,
            "severity":        rule.severity,
            "response_mode":   rule.response_mode,
            "condition_met":   condition,
        }
