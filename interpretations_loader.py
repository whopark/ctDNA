"""Clinical interpretation text resolver for SPEC-REPORT-001.

Resolution priority:
  1. interpretations.yaml exact case_id match
  2. interpretations.yaml longest-prefix match (key is a prefix of case_id)
  3. kb_map fallback (kb keys split on '|'; prefix before '|' is matched)
  4. empty string

PyYAML import is lazy so the rest of the pipeline keeps working when
pyyaml is not installed; yaml resolution then falls through to KB / empty.
"""

from __future__ import annotations

from pathlib import Path


# @AX:WARN [AUTO] pyyaml is lazy-imported; missing dependency falls through to KB/empty
# @AX:WARN [AUTO] rather than crashing — intentional for pipeline resilience.
def load_interpretations(yaml_path: str | Path) -> dict[str, str]:
    """Read a yaml file and return a {case_id_or_prefix: text} mapping.

    Returns {} if the file is missing, pyyaml is not installed, or parsing fails.
    """
    path = Path(yaml_path)
    if not path.exists():
        return {}
    try:
        import yaml  # lazy import — pyyaml may not be installed
    except ImportError:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}
    except Exception:
        # Malformed yaml — fall through to KB/empty rather than aborting
        return {}


# @AX:NOTE [AUTO] 4-step priority: yaml-exact → yaml-longest-prefix → KB → empty string.
# @AX:NOTE [AUTO] Empty string (not None) is intentional so set_cell_text receives a valid str.
def resolve_interpretation(
    case_id: str,
    yaml_path: str | Path | None = None,
    yaml_map: dict[str, str] | None = None,
    kb_map: dict[str, str] | None = None,
) -> str:
    """Resolve interpretation text using the four-step priority.

    Step 1: yaml exact match  — yaml_map[case_id]
    Step 2: yaml longest-prefix match — longest key k where case_id.startswith(k)
    Step 3: KB fallback — kb_map keys like '01-|GENE'; match prefix before '|'
    Step 4: empty string

    Either yaml_path (a file path) or yaml_map (a pre-loaded dict) may be
    supplied. When yaml_path is given it takes precedence and is loaded via
    load_interpretations(). Passing neither is valid and skips yaml steps.
    """
    # Build yaml mapping from path or pre-loaded dict
    if yaml_path is not None:
        mapping = load_interpretations(yaml_path)
    else:
        mapping = yaml_map or {}

    kb_map = kb_map or {}

    # Step 1: yaml exact match
    if case_id in mapping and mapping[case_id]:
        return mapping[case_id]

    # Step 2: yaml longest-prefix match (exclude exact key, sort by length desc)
    prefix_candidates = sorted(
        (k for k in mapping if k != case_id and case_id.startswith(k)),
        key=len,
        reverse=True,
    )
    for k in prefix_candidates:
        if mapping[k]:
            return mapping[k]

    # Step 3: KB fallback — split each key on '|' to extract the case prefix
    for k, text in kb_map.items():
        kb_case = k.split("|", 1)[0] if "|" in k else k
        if (case_id == kb_case or case_id.startswith(kb_case)) and text:
            return text

    # Step 4: empty string
    return ""
