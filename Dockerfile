# ctDNA Sandbox web UI — FastAPI on Python 3.12-slim.
# SANDBOX ONLY: do not deploy with real PHI.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CTDNA_SESSION_ROOT=/tmp

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pipeline source. The DOCX template lives under 0325/ (generate_clinical_reports
# falls back to ./0325/template.docx when no root-level template.docx is present).
COPY annotate_vcf.py reformat_tiers.py generate_clinical_reports.py \
     case_meta.py qc_stats.py report_tables.py interpretations_loader.py \
     interpretations.yaml ./
COPY 0325/template.docx ./0325/template.docx
COPY web ./web

EXPOSE 8000

# Railway injects $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
