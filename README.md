# CRM-Based Monitoring Framework

A Python implementation of a Document Governance Monitoring Framework following
Design Science Research (DSR) principles.

---

## Project Structure

```
crm_monitoring/
├── src/
│   ├── rule_design/
│   │   ├── rule_loader.py                         # Load rule_specification.csv
│   │   ├── rule_repository_builder.py             # Build in-memory Rule Repository
│   │   └── run_rule_design.py                     # Rule Design Instance entry point
│   ├── monitoring/
│   │   ├── event_stream_processor.py              # Parse & stream OCEL events
│   │   ├── rule_engine.py                         # Evaluate deterministic rules
│   │   ├── threshold_engine.py                    # Calibrate & evaluate statistical rules
│   │   ├── operational_context_enforcement_engine.py  # Enforce response modes
│   │   └── run_monitoring.py                      # Monitoring Instance entry point
│   └── evaluation/
│       ├── evaluation_data_loader.py              # Load ground truth & detections
│       ├── confusion_matrix.py                    # Compute TP/FP/FN/TN
│       ├── metrics.py                             # Precision, Recall, F1-score
│       └── run_evaluation.py                      # Evaluation Instance entry point
├── data/
│   ├── order-management.json                      # OCEL event log (input)
│   ├── rule_specification.csv                     # Governance rules (input)
│   └── ground_truth.csv                           # Manual violations (input)
├── output/                                        # All generated outputs land here
├── main.py                                        # Top-level runner
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.12+
- pip

---

## Installation

```bash
# 1. Clone or extract the project
cd crm_monitoring

# 2. (Optional but recommended) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\activate             # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Framework

### Full pipeline (recommended)

```bash
python main.py
```

This runs all three instances in sequence and writes the following files to `output/`:

| File | Description |
|------|-------------|
| `rule_repository.csv` | Persisted rule repository with all 15 governance rules |
| `detected_violations.csv` | All detected violations (deterministic + statistical) |
| `intervention_packages.csv` | Managerial intervention packages (Critical-level only) |
| `confusion_matrix.csv` | Per-rule TP/FP/FN/TN counts |
| `evaluation_results.csv` | Precision / Recall / F1-score per rule and overall |
| `framework.log` | Full execution log |

### Custom paths

```bash
python main.py \
  --rule-spec  data/rule_specification.csv \
  --ocel       data/order-management.json \
  --ground-truth data/ground_truth.csv \
  --output-dir output/
```

### Skip evaluation

```bash
python main.py --skip-evaluation
```

---

## Architecture

```
INPUTS
  rule_specification.csv  ──►  RULE DESIGN INSTANCE
  order-management.json   ──►  MONITORING INSTANCE
  ground_truth.csv        ──►  EVALUATION INSTANCE

RULE DESIGN INSTANCE
  rule_loader.py               → Load & validate rules
  rule_repository_builder.py   → Build indexed repository
  Output: rule_repository.csv

        ↓ (Rule Repository)

MONITORING INSTANCE
  event_stream_processor.py              → Parse & stream OCEL events
  rule_engine.py                         → Evaluate deterministic rules (GR01,02,04,06,09,11,12,13,15)
  threshold_engine.py                    → Calibrate P90/P95 + evaluate statistical rules (GR03,05,07,08,10,14)
  operational_context_enforcement_engine.py → Enforce response modes
  Output: detected_violations.csv, intervention_packages.csv

        ↓ (Detected Violations)

EVALUATION INSTANCE
  evaluation_data_loader.py  → Load & align ground truth vs detected
  confusion_matrix.py        → Compute TP/FP/FN/TN
  metrics.py                 → Precision / Recall / F1-score
  Output: confusion_matrix.csv, evaluation_results.csv
```

---

## Rule Types

### Deterministic Rules (Fixed threshold)

| Rule ID | Name | Response |
|---------|------|----------|
| GR01 | Complete Information | Hard Stop |
| GR02 | Mandatory Document Validation | Hard Stop |
| GR04 | Ownership Assignment | Hard Stop |
| GR06 | Quotation Traceability | Hard Stop |
| GR09 | Rework Justification | Hard Stop |
| GR11 | Version Consistency | Intervention Package |
| GR12 | Document Lineage Control | Hard Stop |
| GR13 | Traceability Completeness | Intervention Package |
| GR15 | Ownership Governance Monitoring | Intervention Package |

### Statistical Rules (P90/P95 calibration)

| Rule ID | Name | Metric |
|---------|------|--------|
| GR03 | Communication Traceability | Non-standard comm count per PO |
| GR05 | Vendor Communication Traceability | Vendor non-standard channel count |
| GR07 | Negotiation Auditability | Undocumented revision count |
| GR08 | BOM Rework Control | Validation cycle count |
| GR10 | Master Data Consistency | Naming inconsistency count |
| GR14 | Operational Timeliness Monitoring | Days to shipment update |

---

## Threshold Configuration

| Threshold | Percentile | Purpose |
|-----------|-----------|---------|
| Warning | P90 | Logged to violation log; no package generated |
| Critical | P95 | Violation log + Intervention Package generated |

Thresholds are derived automatically from the historical OCEL event log.

---

## Managerial Principle

The framework **never** makes autonomous business decisions.  It only:
- Detects deviations
- Generates operational context
- Proposes recommendations
- Forwards Intervention Packages

**Final decisions always belong to managers.**

---

## Output Samples

### detected_violations.csv

```
violation_id,rule_id,rule_name,rule_type,object_id,severity,response_mode,condition_met,...
VIO-DET-0001,GR01,Complete Information,Deterministic,PO-NTS-2026-002,High,Hard Stop,...
```

### intervention_packages.csv

```
package_id,po_id,rule_id,severity,triggered_metric,threshold_level,observed_value,...
IP-0001,PO-NTS-2026-002,GR03,Medium,non_standard_comm_count,Critical,1.0,...
```

### evaluation_results.csv

```
scope,tp,fp,fn,tn,precision,recall,f1_score
GR01,...
GR03,...
OVERALL,...
```
