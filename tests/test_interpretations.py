"""
Phase 1.5 test scaffold — S3: interpretations search priority (4-step fallback chain).

Priority order:
  1. interpretations.yaml exact case_id match
  2. interpretations.yaml longest-prefix match
  3. KB_INTERPRETATIONS dict match
  4. empty string fallback

All tests in RED state (FAIL) until interpretations_loader.py is implemented.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ImportError expected here — module does not exist yet (RED state)
from interpretations_loader import resolve_interpretation, load_interpretations  # noqa: E402


def _write_yaml(path, mapping: dict) -> str:
    """Write a minimal interpretations.yaml from a dict and return its path string."""
    import yaml  # installed as pyyaml
    with open(str(path), "w", encoding="utf-8") as f:
        yaml.dump(mapping, f, allow_unicode=True)
    return str(path)


class TestResolveInterpretationS3:
    """S3: four-step resolution priority."""

    def test_exact_match_wins_over_prefix(self, tmp_path):
        """When yaml has both exact key and prefix key, exact key is returned."""
        yaml_path = _write_yaml(
            tmp_path / "interpretations.yaml",
            {
                "07-XYZ_999": "yaml-exact-text",
                "07-": "yaml-prefix-text",
            }
        )
        kb_map = {"07-|MYD88": "kb-text"}
        result = resolve_interpretation(
            case_id="07-XYZ_999",
            yaml_path=yaml_path,
            kb_map=kb_map,
        )
        assert result == "yaml-exact-text", (
            f"Expected 'yaml-exact-text' (exact match wins), got {result!r}"
        )

    def test_prefix_match_when_no_exact(self, tmp_path):
        """When yaml has only a prefix key, prefix match is returned."""
        yaml_path = _write_yaml(
            tmp_path / "interpretations.yaml",
            {
                "07-": "yaml-prefix-text",
            }
        )
        kb_map = {"07-|MYD88": "kb-text"}
        result = resolve_interpretation(
            case_id="07-OTHER_111",
            yaml_path=yaml_path,
            kb_map=kb_map,
        )
        assert result == "yaml-prefix-text", (
            f"Expected 'yaml-prefix-text' (prefix fallback), got {result!r}"
        )

    def test_kb_fallback_when_no_yaml_match(self, tmp_path):
        """When yaml has no matching key at all, KB dict is consulted."""
        yaml_path = _write_yaml(
            tmp_path / "interpretations.yaml",
            {
                "01-": "other-text",
                # no "07-" key
            }
        )
        kb_map = {"07-|MYD88": "kb-text"}
        result = resolve_interpretation(
            case_id="07-OTHER_111",
            yaml_path=yaml_path,
            kb_map=kb_map,
        )
        assert result == "kb-text", (
            f"Expected 'kb-text' (KB fallback), got {result!r}"
        )

    def test_empty_string_when_no_match_anywhere(self, tmp_path):
        """When no source has a matching key, returns empty string (not None)."""
        yaml_path = _write_yaml(
            tmp_path / "interpretations.yaml",
            {
                "01-": "some-text",
            }
        )
        kb_map = {}
        result = resolve_interpretation(
            case_id="99-MISSING",
            yaml_path=yaml_path,
            kb_map=kb_map,
        )
        assert result == "", (
            f"Expected '' (empty string) when no match found, got {result!r}"
        )
        assert result is not None, "Must return '' not None when no match found"


class TestLoadInterpretations:
    """load_interpretations: reads yaml and returns a dict keyed by case_id/prefix."""

    def test_load_returns_dict(self, tmp_path):
        yaml_path = _write_yaml(
            tmp_path / "interpretations.yaml",
            {"01-": "text-a", "02-XYZ_999": "text-b"}
        )
        result = load_interpretations(yaml_path)
        assert isinstance(result, dict), (
            f"Expected dict from load_interpretations, got {type(result).__name__}"
        )

    def test_load_preserves_values(self, tmp_path):
        yaml_path = _write_yaml(
            tmp_path / "interpretations.yaml",
            {"01-": "text-a", "02-XYZ_999": "text-b"}
        )
        result = load_interpretations(yaml_path)
        assert result.get("01-") == "text-a", (
            f"Expected result['01-']='text-a', got {result.get('01-')!r}"
        )
        assert result.get("02-XYZ_999") == "text-b", (
            f"Expected result['02-XYZ_999']='text-b', got {result.get('02-XYZ_999')!r}"
        )

    def test_load_missing_file_returns_empty_dict(self, tmp_path):
        """Missing yaml file must return empty dict without raising."""
        result = load_interpretations(str(tmp_path / "nonexistent.yaml"))
        assert result == {}, (
            f"Expected {{}} for missing yaml file, got {result!r}"
        )
