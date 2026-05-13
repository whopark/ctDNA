"""
Phase 1.5 test scaffold — S4 (fail-soft on missing meta.json) + S6 (scaffold creation).

All tests in RED state (FAIL) until case_meta.py is implemented by Phase 2 executors.
"""
from __future__ import annotations

import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ImportError expected here — module does not exist yet (RED state)
from case_meta import load_case_meta, write_meta_scaffold, META_KEYS  # noqa: E402


class TestLoadCaseMetaS4FailSoft:
    """S4: missing meta.json → ({}, [warning]) without raising."""

    def test_missing_meta_json_returns_empty_dict(self, tmp_path):
        result, warnings = load_case_meta(str(tmp_path))
        assert result == {}, (
            f"Expected empty dict for missing meta.json, got {result!r}"
        )

    def test_missing_meta_json_returns_warning_list(self, tmp_path):
        result, warnings = load_case_meta(str(tmp_path))
        assert len(warnings) >= 1, (
            "Expected at least one warning for missing meta.json"
        )
        warning_text = " ".join(warnings).lower()
        assert "meta.json" in warning_text, (
            f"Warning must mention 'meta.json'; got: {warnings!r}"
        )

    def test_missing_meta_json_does_not_raise(self, tmp_path):
        # Must not raise any exception
        try:
            load_case_meta(str(tmp_path))
        except Exception as exc:
            raise AssertionError(
                f"load_case_meta must not raise on missing meta.json; got {exc!r}"
            ) from exc

    def test_warning_contains_case_id(self, tmp_path):
        """Warning message must contain a recognizable reference to the case folder."""
        case_dir = tmp_path / "06-ABC_99999"
        case_dir.mkdir()
        _, warnings = load_case_meta(str(case_dir))
        assert len(warnings) >= 1, "Expected warning for missing meta.json"
        combined = " ".join(warnings)
        # Either the case_id fragment or the full path must appear in the warning
        assert ("06-ABC_99999" in combined or str(case_dir) in combined), (
            f"Warning must reference the case_id or path; got: {warnings!r}"
        )

    def test_warning_emitted_exactly_once(self, tmp_path, caplog):
        """S4: exactly one warning per case (not multiple)."""
        case_dir = tmp_path / "07-TEST_12345"
        case_dir.mkdir()
        with caplog.at_level(logging.WARNING):
            load_case_meta(str(case_dir))
        meta_json_warnings = [
            r for r in caplog.records
            if "meta.json" in r.message.lower()
        ]
        assert len(meta_json_warnings) == 1, (
            f"Expected exactly 1 meta.json warning, got {len(meta_json_warnings)}: "
            f"{[r.message for r in meta_json_warnings]!r}"
        )

    def test_malformed_json_returns_warning_not_raise(self, tmp_path):
        """Malformed JSON → ({}, [warning containing 'malformed']) instead of raising."""
        meta_path = tmp_path / "meta.json"
        meta_path.write_text("{invalid json content", encoding="utf-8")
        result, warnings = load_case_meta(str(tmp_path))
        assert result == {}, f"Expected empty dict for malformed meta.json, got {result!r}"
        assert len(warnings) >= 1, "Expected warning for malformed meta.json"
        combined = " ".join(warnings).lower()
        assert "malformed" in combined or "parse" in combined or "invalid" in combined, (
            f"Warning should describe the parse failure; got: {warnings!r}"
        )


class TestWriteMetaScaffoldS6:
    """S6: write_meta_scaffold creates meta.json with all META_KEYS and correct defaults."""

    def test_scaffold_creates_meta_json(self, tmp_path):
        case_dir = tmp_path / "06-NEW_123"
        case_dir.mkdir()
        write_meta_scaffold(str(case_dir))
        assert (case_dir / "meta.json").exists(), (
            "write_meta_scaffold must create meta.json in the case folder"
        )

    def test_scaffold_has_all_meta_keys(self, tmp_path):
        case_dir = tmp_path / "06-NEW_123"
        case_dir.mkdir()
        write_meta_scaffold(str(case_dir))
        with open(str(case_dir / "meta.json"), encoding="utf-8") as f:
            data = json.load(f)
        for key in META_KEYS:
            assert key in data, f"META_KEY '{key}' missing from scaffold meta.json"

    def test_scaffold_examiners_two_empty_strings(self, tmp_path):
        case_dir = tmp_path / "06-NEW_123"
        case_dir.mkdir()
        write_meta_scaffold(str(case_dir))
        with open(str(case_dir / "meta.json"), encoding="utf-8") as f:
            data = json.load(f)
        assert data["examiners"] == ["", ""], (
            f"Expected examiners=['',''], got {data['examiners']!r}"
        )

    def test_scaffold_reporters_four_empty_strings(self, tmp_path):
        case_dir = tmp_path / "06-NEW_123"
        case_dir.mkdir()
        write_meta_scaffold(str(case_dir))
        with open(str(case_dir / "meta.json"), encoding="utf-8") as f:
            data = json.load(f)
        assert data["reporters"] == ["", "", "", ""], (
            f"Expected reporters=['','','',''], got {data['reporters']!r}"
        )

    def test_scaffold_is_idempotent(self, tmp_path):
        """Calling write_meta_scaffold twice must not overwrite an existing meta.json."""
        case_dir = tmp_path / "06-NEW_123"
        case_dir.mkdir()
        write_meta_scaffold(str(case_dir))
        # Edit the file to mark it as pre-existing
        meta_path = case_dir / "meta.json"
        with open(str(meta_path), encoding="utf-8") as f:
            data = json.load(f)
        data["birth_date"] = "1990-01-01"
        with open(str(meta_path), "w", encoding="utf-8") as f:
            json.dump(data, f)
        # Call again — should NOT overwrite
        write_meta_scaffold(str(case_dir))
        with open(str(meta_path), encoding="utf-8") as f:
            data2 = json.load(f)
        assert data2["birth_date"] == "1990-01-01", (
            "write_meta_scaffold overwrote existing meta.json (must be idempotent)"
        )
