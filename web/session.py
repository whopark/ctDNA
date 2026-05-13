"""Per-request session storage rooted under a tmp directory.

Sessions are short-lived (TTL ~2h) and never written to repo-tracked paths.
SANDBOX scope only — no PHI lifecycle management here.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


SESSION_ROOT = Path(os.environ.get("CTDNA_SESSION_ROOT", tempfile.gettempdir())) / "ctdna-sessions"
TTL_SECONDS = int(os.environ.get("CTDNA_SESSION_TTL", "7200"))


@dataclass
class Session:
    id: str
    root: Path

    @property
    def vcf_path(self) -> Path:
        return self.root / "input.vcf"

    @property
    def annotated_csv(self) -> Path:
        return self.root / f"{self.id}_annotated.csv"

    @property
    def tiered_csv(self) -> Path:
        return self.root / f"{self.id}_tiered_report.csv"

    @property
    def docx_path(self) -> Path:
        return self.root / f"{self.id}_clinical_report.docx"

    @property
    def meta_path(self) -> Path:
        return self.root / "meta.json"

    @property
    def state_path(self) -> Path:
        return self.root / "state.txt"

    @property
    def log_path(self) -> Path:
        return self.root / "progress.log"


def create_session() -> Session:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    sid = uuid.uuid4().hex[:12]
    root = SESSION_ROOT / sid
    root.mkdir(parents=True, exist_ok=False)
    sess = Session(id=sid, root=root)
    set_state(sess, "created")
    return sess


def get_session(sid: str) -> Optional[Session]:
    if not sid or "/" in sid or "\\" in sid or ".." in sid:
        return None
    root = SESSION_ROOT / sid
    if not root.is_dir():
        return None
    return Session(id=sid, root=root)


def set_state(sess: Session, state: str) -> None:
    sess.state_path.write_text(state, encoding="utf-8")


def get_state(sess: Session) -> str:
    if not sess.state_path.exists():
        return "unknown"
    return sess.state_path.read_text(encoding="utf-8").strip()


def append_log(sess: Session, line: str) -> None:
    with sess.log_path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def read_log(sess: Session, tail: int = 50) -> list[str]:
    if not sess.log_path.exists():
        return []
    lines = sess.log_path.read_text(encoding="utf-8").splitlines()
    return lines[-tail:]


def purge_stale() -> int:
    if not SESSION_ROOT.is_dir():
        return 0
    cutoff = time.time() - TTL_SECONDS
    removed = 0
    for child in SESSION_ROOT.iterdir():
        if not child.is_dir():
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
    return removed
