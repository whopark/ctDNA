"""Per-case patient meta + signatory loader for SPEC-REPORT-001.

Schema lives in case folder as meta.json. Fail-soft: missing or malformed
file returns ({}, warnings) instead of raising, so the DOCX pipeline
can continue and the report leaves the affected cells blank.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# @AX:NOTE [AUTO] Canonical key list mirrors spec.md Table 0 mapping; adding/removing
# @AX:NOTE [AUTO] keys here breaks DOCX cell rendering in report_tables.py fill_table0_patient_info.
# Canonical key list — matches the 12-cell Table 0 mapping in spec.md
# plus Table 15 signature names.
META_KEYS = [
    # Table 0 patient meta (12 cells)
    "patient_name", "sex", "birth_date", "reg_no", "test_no",
    "ordering_doctor", "specimen_type", "specimen_state",
    "specimen_collected_at", "specimen_received_at",
    "test_date", "preliminary_report_date", "final_report_date",
    # Table 15 signatures (2 examiners + 4 reporters)
    "examiners",   # list[str], expected length 2
    "reporters",   # list[str], expected length 4
]


# @AX:WARN [AUTO] Fail-soft contract: never raises. Missing or malformed meta.json returns
# @AX:WARN [AUTO] ({}, [warning]) so the report pipeline can continue per REQ-6.
def load_case_meta(case_dir: str | Path) -> Tuple[dict, list[str]]:
    """Load meta.json from case_dir. Returns (meta_dict, warnings_list).

    Never raises. Missing file -> ({}, ["missing meta.json: <path>"]).
    Malformed JSON -> ({}, ["malformed meta.json: <reason>"]).
    Valid -> (parsed_dict, []).

    Exactly one warning log line is emitted per call when meta.json is
    absent or unparseable (REQ-6: one warning per case).
    """
    path = Path(case_dir) / "meta.json"
    if not path.exists():
        msg = f"missing meta.json: {path}"
        logger.warning(msg)
        return {}, [msg]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            msg = "malformed meta.json: top-level is not an object"
            logger.warning(msg)
            return {}, [msg]
        return data, []
    except json.JSONDecodeError as e:
        msg = f"malformed meta.json: {e}"
        logger.warning(msg)
        return {}, [msg]
    except OSError as e:
        msg = f"unreadable meta.json: {e}"
        logger.warning(msg)
        return {}, [msg]


# @AX:NOTE [AUTO] Idempotent — does not overwrite existing meta.json to preserve operator-edited PHI fields.
def write_meta_scaffold(case_dir: str | Path, case_id: str | None = None) -> Path:
    """Create meta.json scaffold inside case_dir if absent. Idempotent.

    Every META_KEYS field is present:
      - strings default to ""
      - examiners defaults to ["", ""]
      - reporters defaults to ["", "", "", ""]

    Returns the meta.json path. Does NOT overwrite if file already exists.
    """
    path = Path(case_dir) / "meta.json"
    if path.exists():
        return path
    scaffold = {k: "" for k in META_KEYS}
    scaffold["examiners"] = ["", ""]
    scaffold["reporters"] = ["", "", "", ""]
    if case_id:
        # Convenience: pre-fill reg_no from case_id pattern NN-INITIALS_REGNO if matched
        # e.g. "01-JJH_10679562" -> reg_no="10679562"
        if "_" in case_id:
            scaffold["reg_no"] = case_id.split("_", 1)[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scaffold, f, ensure_ascii=False, indent=2)
    return path
