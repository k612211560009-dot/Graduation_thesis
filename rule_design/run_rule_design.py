# Make project root importable from any working directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging

from config import RULE_SPEC_PATH, RULE_REPOSITORY_PATH, OUTPUT_DIR
from rule_design.rule_loader import load_rules
from rule_design.rule_repository_builder import build_repository, RuleRepository

# Logging
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "rule_design.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_rule_design")


def run_rule_design(
    rule_spec_path=RULE_SPEC_PATH,
    output_path=RULE_REPOSITORY_PATH,
) -> RuleRepository:
    logger.info("=== RULE DESIGN INSTANCE START ===")

    # Step 1: Load rules
    rules = load_rules(rule_spec_path)
    logger.info("Loaded %d rules.", len(rules))

    # Step 2: Build repository
    repo = build_repository(rules)

    # Step 3: Persist to data/ (shared intermediate output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    repo.to_csv(output_path)
    logger.info("Rule repository written → %s", output_path)

    logger.info(repo.summary())
    logger.info("Deterministic rules : %s", [r.rule_id for r in repo.deterministic_rules()])
    logger.info("Statistical rules   : %s", [r.rule_id for r in repo.statistical_rules()])
    logger.info("=== RULE DESIGN INSTANCE COMPLETE ===")

    return repo


# Run standalone
if __name__ == "__main__":
    run_rule_design()
    print(f"\n Output → {RULE_REPOSITORY_PATH}")
