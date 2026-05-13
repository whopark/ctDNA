"""FastAPI entrypoint for the ctDNA pipeline sandbox.

SANDBOX ONLY: do not upload real PHI. Railway / FastAPI deployment here is not
HIPAA-compliant and is intended for synthetic/de-identified inputs.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from web import pipeline, session
from web.session import (
    Session,
    append_log,
    create_session,
    get_session,
    get_state,
    purge_stale,
    read_log,
    set_state,
)

BASE_DIR = Path(__file__).resolve().parent
# cache_size=0 avoids a Python 3.14 + Jinja2 LRUCache incompatibility we hit
# during local smoke testing; production runtime is Python 3.12 in the Docker image.
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,
)
TEMPLATES = Jinja2Templates(env=_JINJA_ENV)

META_KEYS = [
    "patient_name", "sex", "birth_date", "reg_no", "test_no",
    "ordering_doctor", "specimen_type", "specimen_state",
    "specimen_collected_at", "specimen_received_at",
    "test_date", "preliminary_report_date", "final_report_date",
]
LIST_META_KEYS = ["examiners", "reporters"]

app = FastAPI(title="ctDNA Sandbox", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def _purge_on_startup() -> None:
    purge_stale()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "index.html")


@app.post("/upload")
async def upload(vcf: UploadFile = File(...)) -> RedirectResponse:
    if not vcf.filename or not vcf.filename.lower().endswith(".vcf"):
        raise HTTPException(400, "Please upload a .vcf file")
    sess = create_session()
    content = await vcf.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "VCF too large (limit 50 MB)")
    sess.vcf_path.write_bytes(content)
    set_state(sess, "uploaded")
    append_log(sess, f"VCF uploaded: {vcf.filename} ({len(content)} bytes)")
    return RedirectResponse(url=f"/session/{sess.id}", status_code=303)


@app.get("/session/{sid}", response_class=HTMLResponse)
def session_view(request: Request, sid: str) -> HTMLResponse:
    sess = _require_session(sid)
    state = get_state(sess)
    context = {
        "sess": sess,
        "state": state,
        "log_tail": read_log(sess, tail=30),
    }
    if state in {"annotated", "tiered", "report_ready"}:
        context["tiered_rows"] = pipeline.read_tiered_rows(sess.tiered_csv)
        context["meta"] = _load_meta(sess)
        context["meta_keys"] = META_KEYS
        context["list_meta_keys"] = LIST_META_KEYS
    return TEMPLATES.TemplateResponse(request, "session.html", context)


@app.post("/annotate/{sid}")
def annotate(request: Request, sid: str) -> HTMLResponse:
    sess = _require_session(sid)
    state = get_state(sess)
    if state == "annotating":
        return _progress_partial(request, sess)
    if state not in {"uploaded", "failed"}:
        raise HTTPException(409, f"Cannot start annotation from state '{state}'")
    set_state(sess, "annotating")
    append_log(sess, "Starting annotation pipeline (VEP + tiering)")
    threading.Thread(target=_run_pipeline_async, args=(sess,), daemon=True).start()
    return _progress_partial(request, sess)


@app.get("/progress/{sid}", response_class=HTMLResponse)
def progress(request: Request, sid: str) -> HTMLResponse:
    sess = _require_session(sid)
    return _progress_partial(request, sess)


@app.post("/meta/{sid}")
async def save_meta(request: Request, sid: str) -> HTMLResponse:
    sess = _require_session(sid)
    form = await request.form()
    meta = {}
    for key in META_KEYS:
        meta[key] = (form.get(key) or "").strip()
    for key in LIST_META_KEYS:
        raw = (form.get(key) or "").strip()
        meta[key] = [p.strip() for p in raw.split(",") if p.strip()]
    sess.meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_log(sess, "meta.json saved")
    return TEMPLATES.TemplateResponse(
        request, "_meta_saved.html", {"sess": sess, "meta": meta},
    )


@app.post("/generate/{sid}", response_class=HTMLResponse)
def generate(request: Request, sid: str) -> HTMLResponse:
    sess = _require_session(sid)
    if not sess.tiered_csv.exists():
        raise HTTPException(409, "Run annotation before generating the report")
    if not sess.meta_path.exists():
        # Create minimal placeholder meta; pipeline tolerates empties
        sess.meta_path.write_text(json.dumps({k: "" for k in META_KEYS} | {k: [] for k in LIST_META_KEYS}, ensure_ascii=False, indent=2), encoding="utf-8")
        append_log(sess, "No meta saved — using empty placeholder")
    try:
        pipeline.run_report(
            case_id=sess.id,
            tiered_csv=sess.tiered_csv,
            annotated_csv=sess.annotated_csv,
            out_docx=sess.docx_path,
            log=lambda m: append_log(sess, m),
        )
    except Exception as exc:  # pragma: no cover — surface to UI
        append_log(sess, f"ERROR generating DOCX: {exc}")
        raise HTTPException(500, f"Report generation failed: {exc}")
    set_state(sess, "report_ready")
    return TEMPLATES.TemplateResponse(
        request, "_download.html", {"sess": sess},
    )


@app.get("/download/{sid}")
def download(sid: str) -> FileResponse:
    sess = _require_session(sid)
    if not sess.docx_path.exists():
        raise HTTPException(404, "DOCX not generated yet")
    return FileResponse(
        path=str(sess.docx_path),
        filename=f"{sess.id}_clinical_report.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _require_session(sid: str) -> Session:
    sess = get_session(sid)
    if not sess:
        raise HTTPException(404, "Session not found or expired")
    return sess


def _load_meta(sess: Session) -> dict:
    if not sess.meta_path.exists():
        return {k: "" for k in META_KEYS} | {k: [] for k in LIST_META_KEYS}
    try:
        data = json.loads(sess.meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {k: "" for k in META_KEYS} | {k: [] for k in LIST_META_KEYS}
    for k in META_KEYS:
        data.setdefault(k, "")
    for k in LIST_META_KEYS:
        if not isinstance(data.get(k), list):
            data[k] = []
    return data


def _progress_partial(request: Request, sess: Session) -> HTMLResponse:
    state = get_state(sess)
    is_done = state in {"tiered", "annotated", "report_ready", "failed"}
    ctx = {
        "sess": sess,
        "state": state,
        "log_tail": read_log(sess, tail=30),
        "is_done": is_done,
    }
    return TEMPLATES.TemplateResponse(request, "_progress.html", ctx)


def _run_pipeline_async(sess: Session) -> None:
    """Background worker: annotation + tiering. Stays inside the session root."""
    try:
        result = pipeline.run_annotation(
            sess.vcf_path, sess.annotated_csv,
            log=lambda m: append_log(sess, m),
        )
        append_log(sess, f"Tier counts: {result['tier_counts']}")
        pipeline.run_tiering(
            sess.annotated_csv, sess.tiered_csv,
            log=lambda m: append_log(sess, m),
        )
        set_state(sess, "tiered")
        append_log(sess, "Pipeline complete — fill in meta and generate the report")
    except Exception as exc:
        append_log(sess, f"ERROR: {exc}")
        set_state(sess, "failed")
