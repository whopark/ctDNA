#!/usr/bin/env python3
"""
Knowledge Base for ctDNA annotation pipeline.

Schema (kb.json):
{
  "version": 1,
  "updated": "ISO-8601 timestamp",
  "therapeutics": {
      "<GENE>": {
          "text": "best-voted therapeutic implication string",
          "candidates": {"<text>": count, ...},     # seen across reports
          "sources": ["<report-path>", ...]
      },
      ...
  },
  "interpretations": {
      "<key>": {                              # key = gene or gene+hotspot
          "text": "full Korean interpretation paragraph",
          "sources": ["<report-path>", ...]
      },
      ...
  },
  "variant_evidence": {
      "<GENE>:<HGVSp or HGVSc>": {
          "tiers": {"Tier 1": n, "Tier 2": n, "Tier 3": n},
          "therapeutic": "optional text",
          "sources": ["<report-path>", ...],
          "last_vaf": "12.93%"
      }
  },
  "tier_hints": {
      # Variants observed at Tier 1 in >=2 historical reports become
      # "promote" candidates — annotate_vcf will lift their minimum tier.
      "<GENE>:<HGVSp or HGVSc>": {"min_tier": "Tier 1" | "Tier 2",
                                  "count": N,
                                  "reason": "..."}
  }
}

The KB is a plain JSON file kept in the repo root. Humans can edit it
directly; the updater always does a merge (never a destructive overwrite).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

KB_VERSION = 1

# Frozen exe support: use writable path when bundled by PyInstaller
try:
    from frozen_path import writable_kb_path
    DEFAULT_KB_PATH = Path(writable_kb_path())
except ImportError:
    DEFAULT_KB_PATH = Path(__file__).resolve().parent / "kb.json"

_EMPTY_KB: Dict[str, Any] = {
    "version": KB_VERSION,
    "updated": None,
    "therapeutics": {},
    "interpretations": {},
    "variant_evidence": {},
    "tier_hints": {},
}


def load_kb(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load KB from disk, returning an empty shell if the file is missing."""
    p = Path(path) if path else DEFAULT_KB_PATH
    if not p.exists():
        return json.loads(json.dumps(_EMPTY_KB))  # deep copy
    try:
        with open(p, encoding="utf-8") as f:
            kb = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to load KB at {p}: {e}") from e
    # Back-fill any missing sections so callers can always .get() safely
    for k, v in _EMPTY_KB.items():
        kb.setdefault(k, v if not isinstance(v, dict) else {})
    return kb


def save_kb(kb: Dict[str, Any], path: Optional[Path] = None) -> Path:
    """Atomically write the KB to disk (write-temp-then-rename)."""
    p = Path(path) if path else DEFAULT_KB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    kb["version"] = KB_VERSION
    kb["updated"] = datetime.now().isoformat(timespec="seconds")
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".kb-", suffix=".json.tmp", dir=str(p.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(kb, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, p)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return p


# ---------------------------------------------------------------------------
# Merge helpers — used by kb_update.py when ingesting new reports
# ---------------------------------------------------------------------------

def _add_source(entry: Dict[str, Any], source: str) -> None:
    srcs = entry.setdefault("sources", [])
    if source and source not in srcs:
        srcs.append(source)


def merge_therapeutic(
    kb: Dict[str, Any],
    gene: str,
    text: str,
    source: str,
) -> bool:
    """Record a therapeutic-implication observation for a gene.

    We keep a vote counter across reports; kb['therapeutics'][gene]['text']
    exposes the currently most-voted value. Returns True if anything changed.
    """
    if not gene or not text:
        return False
    gene = gene.strip().upper()
    text = text.strip()
    if not text or text.lower() in ("nan", "none"):
        return False

    bucket = kb["therapeutics"].setdefault(gene, {
        "text": text,
        "candidates": {},
        "sources": [],
    })
    candidates = bucket.setdefault("candidates", {})
    candidates[text] = candidates.get(text, 0) + 1
    _add_source(bucket, source)
    # Recompute best — highest vote, tie-broken by longest string (more info)
    best = max(candidates.items(), key=lambda kv: (kv[1], len(kv[0])))
    bucket["text"] = best[0]
    return True


def merge_interpretation(
    kb: Dict[str, Any],
    key: str,
    text: str,
    source: str,
) -> bool:
    """Store a long-form Korean interpretation paragraph keyed by case_id
    or gene+hotspot signature."""
    if not key or not text or len(text.strip()) < 20:
        return False
    key = key.strip()
    entry = kb["interpretations"].setdefault(key, {"text": "", "sources": []})
    entry["text"] = text.strip()
    _add_source(entry, source)
    return True


def _variant_key(gene: str, hgvsp: str, hgvsc: str) -> Optional[str]:
    g = (gene or "").strip().upper()
    p = (hgvsp or "").strip()
    c = (hgvsc or "").strip()
    if not g:
        return None
    return f"{g}:{p or c or '?'}"


def merge_variant_evidence(
    kb: Dict[str, Any],
    gene: str,
    hgvsp: str,
    hgvsc: str,
    tier: str,
    vaf: str,
    therapeutic: str,
    source: str,
) -> bool:
    """Record a per-variant observation (gene+HGVSp), tier-votes and therapy."""
    key = _variant_key(gene, hgvsp, hgvsc)
    if not key or tier not in ("Tier 1", "Tier 2", "Tier 3"):
        return False
    entry = kb["variant_evidence"].setdefault(key, {
        "tiers": {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0},
        "therapeutic": "",
        "sources": [],
        "last_vaf": "",
    })
    entry["tiers"][tier] = entry["tiers"].get(tier, 0) + 1
    if therapeutic and therapeutic.strip():
        entry["therapeutic"] = therapeutic.strip()
    if vaf:
        entry["last_vaf"] = vaf.strip()
    _add_source(entry, source)
    return True


def recompute_tier_hints(kb: Dict[str, Any], min_reports: int = 2) -> int:
    """Scan variant_evidence and fill tier_hints with promotion candidates.

    A variant observed at Tier 1 in >= min_reports reports gets a
    "promote to Tier 1" hint. Tier 2 requires the same count. Tier 3 alone
    never triggers promotion. Returns number of hints added or removed
    (changes to the count/reason of an already-present hint don't count).
    """
    hints = kb.setdefault("tier_hints", {})
    changed = 0
    seen: set = set()
    for key, entry in kb["variant_evidence"].items():
        tiers = entry.get("tiers", {})
        t1 = tiers.get("Tier 1", 0)
        t2 = tiers.get("Tier 2", 0)
        target: Optional[str] = None
        reason = ""
        if t1 >= min_reports:
            target = "Tier 1"
            reason = f"Observed Tier 1 in {t1} prior reports"
        elif t1 + t2 >= min_reports and (t1 + t2) > 0:
            target = "Tier 2"
            reason = (
                f"Observed Tier 1/2 in {t1 + t2} prior reports "
                f"(T1={t1}, T2={t2})"
            )

        if target is None:
            if key in hints:
                hints.pop(key)
                changed += 1
            continue

        seen.add(key)
        prev = hints.get(key)
        new = {"min_tier": target, "count": t1 + t2, "reason": reason}
        if prev is None:
            hints[key] = new
            changed += 1
        elif prev.get("min_tier") != target:
            hints[key] = new
            changed += 1
        else:
            # Update count/reason silently — not counted as "changed"
            hints[key] = new

    # Drop hints whose evidence entry has been removed
    for stale in list(hints.keys()):
        if stale not in seen:
            hints.pop(stale)
            changed += 1
    return changed


# ---------------------------------------------------------------------------
# Read-side conveniences — used by annotate_vcf.py / generate_clinical_reports
# ---------------------------------------------------------------------------

def therapeutic_map(kb: Dict[str, Any]) -> Dict[str, str]:
    """Return a flat {gene: best-text} dict."""
    return {g: rec.get("text", "") for g, rec in kb.get("therapeutics", {}).items()
            if rec.get("text")}


def interpretations_map(kb: Dict[str, Any]) -> Dict[str, str]:
    return {k: rec.get("text", "") for k, rec in kb.get("interpretations", {}).items()
            if rec.get("text")}


def tier_hint_for(
    kb: Dict[str, Any],
    gene: str,
    hgvsp: str = "",
    hgvsc: str = "",
) -> Optional[Dict[str, Any]]:
    """Look up a tier-promotion hint for a specific variant.

    Tries gene+hgvsp first, then gene+hgvsc, then gene-only fallback (handled
    by callers who want only variant-level precision should skip fallback).
    """
    if not gene:
        return None
    g = gene.strip().upper()
    hints = kb.get("tier_hints", {})
    for candidate in (f"{g}:{(hgvsp or '').strip()}",
                      f"{g}:{(hgvsc or '').strip()}"):
        if candidate in hints:
            return hints[candidate]
    return None


def stats(kb: Dict[str, Any]) -> Dict[str, int]:
    return {
        "therapeutics": len(kb.get("therapeutics", {})),
        "interpretations": len(kb.get("interpretations", {})),
        "variant_evidence": len(kb.get("variant_evidence", {})),
        "tier_hints": len(kb.get("tier_hints", {})),
    }


if __name__ == "__main__":
    # `python kb.py` — print a summary of the current KB
    import sys
    kb_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KB_PATH
    try:
        kb = load_kb(kb_path)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print(f"KB: {kb_path}")
    print(f"Updated: {kb.get('updated')}")
    for k, v in stats(kb).items():
        print(f"  {k}: {v}")
