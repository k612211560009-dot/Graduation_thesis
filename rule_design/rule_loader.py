from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# Data class representing a single governance rule

@dataclass
class GovernanceRule:
    """Structured representation of one governance rule."""

    rule_id: str
    rule_name: str
    category: str
    applicable_objects: List[str]
    monitoring_condition: str
    threshold_type: str          # "Fixed" | "Statistical"
    severity: str                # "High" | "Medium"
    response_mode: str           # "Hard Stop" | "Intervention Package"
    managerial_intervention: bool

    # Derived flag set by loader
    is_deterministic: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_deterministic = self.threshold_type.strip().lower() == "fixed"

    # Convenience properties
    @property
    def is_statistical(self) -> bool:
        return not self.is_deterministic

    @property
    def is_hard_stop(self) -> bool:
        return self.response_mode.strip().lower() == "hard stop"

    def __repr__(self) -> str:
        kind = "Deterministic" if self.is_deterministic else "Statistical"
        return (
            f"GovernanceRule(id={self.rule_id!r}, name={self.rule_name!r}, "
            f"type={kind}, severity={self.severity!r})"
        )


# Loader

class RuleLoader:
    # Canonical column names after normalisation
    REQUIRED_COLUMNS = {
        "rule id", "rule name", "rule category", "applicable objects",
        "monitoring condition", "threshold type", "severity",
        "response mode", "managerial intervention",
    }

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self._rules: List[GovernanceRule] = []

    # Public interface

    def load(self) -> List[GovernanceRule]:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Rule specification not found: {self.filepath}")

        logger.info("Loading rule specification from: %s", self.filepath)

        rows = self._read_rows()

        if not rows:
            logger.warning("No rows found in rule specification.")
            return []

        # First row is the header
        header = [c.strip().lower() for c in rows[0]]
        missing = self.REQUIRED_COLUMNS - set(header)
        if missing:
            raise ValueError(f"Missing required columns in rule file: {missing}")

        self._rules = []
        for row_num, raw_values in enumerate(rows[1:], start=2):
            # Zip header with values (pad with empty strings if row is short)
            padded = list(raw_values) + [""] * (len(header) - len(raw_values))
            row = {header[i]: (padded[i] or "").strip() for i in range(len(header))}
            rule = self._parse_row(row, row_num)
            if rule:
                self._rules.append(rule)

        logger.info("Loaded %d governance rules.", len(self._rules))
        return self._rules

    def _read_rows(self) -> List[List[str]]:
        try:
            import openpyxl  # noqa: PLC0415
            wb = openpyxl.load_workbook(self.filepath, read_only=True, data_only=True)
            ws = wb.active
            rows = [
                [str(cell) if cell is not None else "" for cell in row]
                for row in ws.iter_rows(values_only=True)
            ]
            # Drop completely empty trailing rows
            while rows and all(c == "" or c == "None" for c in rows[-1]):
                rows.pop()
            # Replace "None" strings (openpyxl returns None for empty cells)
            rows = [["" if c == "None" else c for c in row] for row in rows]
            wb.close()
            logger.info("File read as Excel workbook (%d rows).", len(rows))
            return rows
        except Exception:  # noqa: BLE001
            pass  # Not a valid xlsx – try CSV fallback

        # Attempt 2: UTF-8 CSV
        try:
            return self._read_csv(encoding="utf-8")
        except UnicodeDecodeError:
            pass

        # Attempt 3: latin-1 / cp1252 CSV
        try:
            rows = self._read_csv(encoding="latin-1")
            logger.info("File read as CSV with latin-1 encoding.")
            return rows
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"Cannot read rule specification file '{self.filepath}'. "
                "Supported formats: .xlsx, UTF-8 CSV, latin-1 CSV."
            ) from exc

    def _read_csv(self, encoding: str) -> List[List[str]]:
        """Read a CSV file and return rows as lists of strings."""
        rows: List[List[str]] = []
        with self.filepath.open(newline="", encoding=encoding) as fh:
            reader = csv.reader(fh)
            for row in reader:
                rows.append(row)
        return rows

    # Private helpers

    @staticmethod
    def _parse_applicable_objects(raw: str) -> List[str]:
        """Split the comma/slash-separated objects field into a clean list."""
        separators = ["/", ","]
        parts = [raw]
        for sep in separators:
            new_parts = []
            for p in parts:
                new_parts.extend(p.split(sep))
            parts = new_parts
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return value.strip().lower() in ("yes", "true", "1")

    def _parse_row(self, row: Dict[str, str], row_num: int) -> Optional[GovernanceRule]:
        """Parse a normalised row dict into a GovernanceRule."""
        rule_id = row.get("rule id", "")
        if not rule_id:
            logger.warning("Row %d: empty Rule ID – skipping.", row_num)
            return None

        try:
            return GovernanceRule(
                rule_id=rule_id,
                rule_name=row.get("rule name", ""),
                category=row.get("rule category", ""),
                applicable_objects=self._parse_applicable_objects(
                    row.get("applicable objects", "")
                ),
                monitoring_condition=row.get("monitoring condition", ""),
                threshold_type=row.get("threshold type", "Fixed"),
                severity=row.get("severity", "Medium"),
                response_mode=row.get("response mode", "Intervention Package"),
                managerial_intervention=self._parse_bool(
                    row.get("managerial intervention", "No")
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Row %d: failed to parse rule %r – %s", row_num, rule_id, exc)
            return None


# Convenience function

def load_rules(filepath: str | Path) -> List[GovernanceRule]:
    return RuleLoader(filepath).load()
