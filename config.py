from pathlib import Path

# Project root = the folder that contains this config.py
ROOT = Path(__file__).parent.resolve()

# Input data 
DATA_DIR          = ROOT / "data"
RULE_SPEC_PATH    = DATA_DIR / "rule_specification.csv"
OCEL_PATH         = DATA_DIR / "dataset_preparing/Data/Order_procurement/output/NTS_OCEL_2026.json"
GROUND_TRUTH_PATH = DATA_DIR / "ground_truth.csv"

# Intermediate / shared outputs (written by one stage, read by next) ─
RULE_REPOSITORY_PATH = DATA_DIR / "rule_repository.csv"

# Final outputs 
OUTPUT_DIR               = ROOT / "output"
DETECTED_VIOLATIONS_PATH = OUTPUT_DIR / "detected_violations.csv"
INTERVENTION_PKG_PATH    = OUTPUT_DIR / "intervention_packages.csv"
CONFUSION_MATRIX_PATH    = OUTPUT_DIR / "confusion_matrix.csv"
EVALUATION_RESULTS_PATH  = OUTPUT_DIR / "evaluation_results.csv"
