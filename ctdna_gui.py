#!/usr/bin/env python3
"""
ctDNA Annotation Pipeline GUI — Lymphoma ctDNA Panel
Windows tkinter application integrating:
  1. VEP annotation (annotate_vcf.py)
  2. Tiered report generation (reformat_tiers.py)
  3. Clinical .docx report generation (generate_docx_reports.py)
"""

import sys
import os
import csv
import threading
import queue
import time
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path

# Add repo root and .claude/ to import path
REPO_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude"))

from annotate_vcf import (
    parse_vcf, build_vep_input, query_vep_batch,
    extract_annotation, assign_tier, OUT_FIELDS, BATCH_SIZE,
    ACTIONABLE_TIER3_GENES, DRUG_TARGET_GENES, RISK_STRATIFICATION_GENES,
)
from reformat_tiers import parse_hgvsc, parse_hgvsp

try:
    import generate_docx_reports as gdr
    from generate_docx_reports import generate_report
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# ---------------------------------------------------------------------------
# Stderr Redirector — routes print(..., file=sys.stderr) to GUI log queue
# ---------------------------------------------------------------------------
class StderrRedirector:
    def __init__(self, msg_queue, original):
        self.queue = msg_queue
        self.original = original

    def write(self, text):
        if text.strip():
            self.queue.put(("log", text.rstrip("\n")))
        self.original.write(text)

    def flush(self):
        self.original.flush()


# ---------------------------------------------------------------------------
# Pipeline Worker — runs annotation steps in a background thread
# ---------------------------------------------------------------------------
class PipelineWorker:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue
        self.cancel_flag = threading.Event()
        # Filter config — set by GUI before each run
        self.min_vaf = 0.01
        self.include_tiers = {"Tier 1", "Tier 2", "Tier 3"}
        self.tier3_actionable_only = True
        self.actionable_genes = set(ACTIONABLE_TIER3_GENES)

    def post(self, msg_type, data):
        self.msg_queue.put((msg_type, data))

    # -- Step 1: VEP Annotation --
    def run_annotate(self, vcf_path, output_dir):
        case_id = Path(vcf_path).stem
        case_dir = Path(output_dir) / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        out_path = case_dir / f"{case_id}_annotated.csv"

        self.post("log", f"Parsing {Path(vcf_path).name}...")
        variants = parse_vcf(vcf_path)
        self.post("log", f"Found {len(variants)} variants")

        vep_inputs = [build_vep_input(v) for v in variants]
        all_results = []
        n_batches = (len(vep_inputs) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(vep_inputs), BATCH_SIZE):
            if self.cancel_flag.is_set():
                self.post("log", "Cancelled.")
                return None

            batch = vep_inputs[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            self.post("log", f"  VEP batch {batch_num}/{n_batches} ({len(batch)} variants)...")
            self.post("progress", (batch_num, n_batches,
                                   f"VEP batch {batch_num}/{n_batches}"))

            results = query_vep_batch(batch)
            all_results.extend(results)

            if batch_num < n_batches:
                time.sleep(1)

        result_by_input = {}
        for r in all_results:
            inp = r.get("input", "").strip()
            if inp:
                result_by_input[inp] = r

        min_vaf = self.min_vaf
        include_tiers = self.include_tiers
        tier3_actionable = self.tier3_actionable_only
        tier_counts = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0, "Tier 4": 0}
        matched = 0
        written = 0
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
            writer.writeheader()
            for v, vep_inp in zip(variants, vep_inputs):
                row = {k: v[k] for k in
                       ["chrom", "pos", "id", "ref", "alt", "ad", "dp", "sample_af"]}
                result = result_by_input.get(vep_inp)
                if result:
                    row.update(extract_annotation(result))
                    matched += 1
                else:
                    row.update({k: "NA" for k in
                                ["gene", "most_severe_consequence", "hgvsc",
                                 "hgvsp", "rsid", "max_pop_af", "clin_sig", "uniprot"]})
                row["tier"] = assign_tier(row)
                tier_counts[row["tier"]] += 1
                # Apply filters from configuration
                if float(row["sample_af"]) < min_vaf:
                    continue
                if row["tier"] not in include_tiers:
                    continue
                if tier3_actionable and row["tier"] == "Tier 3" \
                        and row.get("gene", "NA") not in self.actionable_genes:
                    continue
                writer.writerow(row)
                written += 1

        vaf_pct = f"{min_vaf * 100:.1f}%"
        tiers_str = "/".join(sorted(include_tiers))
        self.post("log", f"  Done! {matched}/{len(variants)} annotated, "
                         f"{written} written (VAF>={vaf_pct}, {tiers_str}) "
                         f"→ {out_path.name}")
        self.post("tier_result", {
            "case_id": case_id,
            "tier_counts": tier_counts,
            "total": len(variants),
            "status": "Annotated",
        })
        return str(out_path)

    # -- Step 2: Tiered Report CSV --
    def run_tier_report(self, annotated_csv, output_dir):
        case_id = Path(annotated_csv).stem.replace("_annotated", "")
        out_path = Path(annotated_csv).parent / f"{case_id}_tiered_report.csv"

        out_fields = ["ASCO/AMP Classification", "Gene", "Canonical name",
                      "Accession", "Nucleotide change", "AA change", "% VAF"]

        with open(annotated_csv, encoding="utf-8") as fin:
            rows = list(csv.DictReader(fin))

        min_vaf = self.min_vaf
        include_tiers = self.include_tiers
        tier3_actionable = self.tier3_actionable_only
        tier_order = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}
        reportable = []
        for r in rows:
            if r["tier"] not in tier_order:
                continue
            if r["tier"] not in include_tiers:
                continue
            if float(r["sample_af"]) < min_vaf:
                continue
            if tier3_actionable and r["tier"] == "Tier 3" \
                    and r["gene"] not in self.actionable_genes:
                continue
            reportable.append(r)
        reportable.sort(key=lambda r: (tier_order[r["tier"]], -float(r["sample_af"])))

        with open(out_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fields)
            writer.writeheader()
            for r in reportable:
                transcript, nuc_change = parse_hgvsc(r["hgvsc"])
                accession, aa_change = parse_hgvsp(r["hgvsp"])
                writer.writerow({
                    "ASCO/AMP Classification": r["tier"],
                    "Gene": r["gene"],
                    "Canonical name": transcript,
                    "Accession": accession,
                    "Nucleotide change": nuc_change,
                    "AA change": aa_change,
                    "% VAF": f"{float(r['sample_af']) * 100:.2f}%",
                })

        counts = {}
        for r in reportable:
            counts[r["tier"]] = counts.get(r["tier"], 0) + 1
        self.post("log", f"  Tiered report: {out_path.name} "
                         f"({len(reportable)} reportable — "
                         f"T1:{counts.get('Tier 1',0)} "
                         f"T2:{counts.get('Tier 2',0)} "
                         f"T3:{counts.get('Tier 3',0)})")
        return str(out_path)

    # -- Step 3: Clinical DOCX Report --
    def run_docx_report(self, case_id, tiered_csv, annotated_csv,
                        output_dir, metadata):
        if not HAS_DOCX:
            self.post("error", "python-docx not installed. Skipping DOCX generation.")
            return None

        gdr.CASES[case_id] = {
            "patient": metadata.get("patient", ""),
            "reg_no": metadata.get("reg_no", ""),
            "specimen": metadata.get("specimen", "Peripheral Blood"),
            "test_date": metadata.get("test_date",
                                      datetime.now().strftime("%Y-%m-%d")),
        }
        if metadata.get("interpretation"):
            gdr.INTERPRETATIONS[case_id] = metadata["interpretation"]

        case_dir = Path(output_dir) / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(case_dir / f"{case_id}_clinical_report.docx")

        generate_report(case_id, tiered_csv, annotated_csv, output_path)
        self.post("log", f"  DOCX report: {Path(output_path).name}")
        return output_path


# ---------------------------------------------------------------------------
# Main GUI Application
# ---------------------------------------------------------------------------
class PipelineApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        master.title("ctDNA Annotation Pipeline — Lymphoma Panel")
        master.geometry("960x920")
        master.minsize(820, 780)

        self.vcf_files = []
        self.output_dir = tk.StringVar()
        self.batch_name = tk.StringVar()
        self.metadata_map = {}
        self.msg_queue = queue.Queue()
        self.worker = PipelineWorker(self.msg_queue)

        today = datetime.now().strftime("%m%d")
        self.output_dir.set(str(REPO_ROOT))
        self.batch_name.set(today)

        # Filter config variables
        self.tier1_var = tk.BooleanVar(value=True)
        self.tier2_var = tk.BooleanVar(value=True)
        self.tier3_var = tk.BooleanVar(value=True)
        self.tier3_actionable_var = tk.BooleanVar(value=True)
        self.min_vaf_var = tk.DoubleVar(value=1.0)

        self._build_ui()
        self._redirect_stderr()
        self._poll_queue()

    def _redirect_stderr(self):
        sys.stderr = StderrRedirector(self.msg_queue, sys.__stderr__)

    # ---- UI Construction ----

    def _build_ui(self):
        self.pack(fill="both", expand=True)

        top = ttk.Frame(self)
        top.pack(fill="x")
        self._build_input_frame(top)
        self._build_output_frame(top)
        self._build_filter_frame(top)
        self._build_metadata_frame(top)
        self._build_control_frame(top)

        self._build_log_frame(self)
        self._build_action_frame(self)

    def _build_input_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=" Input Files ", padding=8)
        frame.pack(fill="x", padx=10, pady=(10, 2))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Browse VCF Files...",
                   command=self._browse_vcf).pack(side="left")
        ttk.Button(btn_row, text="Browse Folder...",
                   command=self._browse_folder).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Clear All",
                   command=self._clear_files).pack(side="right")

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="x", pady=4)
        self.file_listbox = tk.Listbox(list_frame, height=4,
                                       selectmode="extended",
                                       font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_output_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=" Output Settings ", padding=8)
        frame.pack(fill="x", padx=10, pady=2)

        row1 = ttk.Frame(frame)
        row1.pack(fill="x")
        ttk.Label(row1, text="Base Directory:").pack(side="left")
        ttk.Entry(row1, textvariable=self.output_dir,
                  width=45).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(row1, text="Browse...",
                   command=self._browse_output).pack(side="right")

        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=(4, 0))
        ttk.Label(row2, text="Batch Folder:").pack(side="left")
        ttk.Entry(row2, textvariable=self.batch_name,
                  width=20).pack(side="left", padx=4)
        self.full_output_label = ttk.Label(
            row2, text="", font=("Segoe UI", 8), foreground="#555555")
        self.full_output_label.pack(side="left", padx=8)
        self._update_output_label()
        self.output_dir.trace_add("write", lambda *_: self._update_output_label())
        self.batch_name.trace_add("write", lambda *_: self._update_output_label())

    def _update_output_label(self):
        base = self.output_dir.get()
        batch = self.batch_name.get().strip()
        if batch:
            full = str(Path(base) / batch)
        else:
            full = base
        self.full_output_label.config(text=f"→ {full}")

    def _get_effective_output_dir(self):
        base = self.output_dir.get()
        batch = self.batch_name.get().strip()
        if batch:
            return str(Path(base) / batch)
        return base

    def _build_filter_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=" Filter Configuration ", padding=8)
        frame.pack(fill="x", padx=10, pady=2)

        # Row 1: Tier selection + VAF
        row = ttk.Frame(frame)
        row.pack(fill="x")

        ttk.Label(row, text="Include Tiers:").pack(side="left")
        ttk.Checkbutton(row, text="Tier 1", variable=self.tier1_var
                        ).pack(side="left", padx=(8, 2))
        ttk.Checkbutton(row, text="Tier 2", variable=self.tier2_var
                        ).pack(side="left", padx=2)
        ttk.Checkbutton(row, text="Tier 3", variable=self.tier3_var,
                        command=self._on_tier3_toggle
                        ).pack(side="left", padx=2)

        sep = ttk.Separator(row, orient="vertical")
        sep.pack(side="left", fill="y", padx=10)

        ttk.Label(row, text="Min VAF (%):").pack(side="left")
        self.vaf_spinbox = ttk.Spinbox(
            row, from_=0.0, to=100.0, increment=0.5,
            textvariable=self.min_vaf_var, width=6, format="%.1f")
        self.vaf_spinbox.pack(side="left", padx=4)

        # Row 2: Tier 3 filter toggle + reset
        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=(4, 0))

        self.tier3_actionable_cb = ttk.Checkbutton(
            row2, text="Tier 3: Report only genes in lists below",
            variable=self.tier3_actionable_var,
            command=self._on_actionable_toggle)
        self.tier3_actionable_cb.pack(side="left", padx=(24, 0))

        self.tier3_reset_btn = ttk.Button(
            row2, text="Reset Defaults",
            command=self._reset_gene_lists, width=13)
        self.tier3_reset_btn.pack(side="right", padx=4)

        # Row 3: Two editable gene list panels side by side
        self.gene_lists_frame = ttk.Frame(frame)
        self.gene_lists_frame.pack(fill="x", pady=(6, 0))

        # Left: Actionable Drug Targets
        left = ttk.Frame(self.gene_lists_frame)
        left.pack(side="left", fill="both", expand=True, padx=(24, 4))

        left_header = ttk.Frame(left)
        left_header.pack(fill="x")
        ttk.Label(left_header, text="Actionable Drug Targets",
                  font=("Segoe UI", 8, "bold")).pack(side="left")
        self.drug_count_label = ttk.Label(
            left_header, text="", font=("Segoe UI", 8), foreground="#555")
        self.drug_count_label.pack(side="right")

        self.drug_text = tk.Text(left, height=3, width=40,
                                 font=("Consolas", 8), wrap="word",
                                 borderwidth=1, relief="sunken")
        self.drug_text.pack(fill="x", pady=(2, 0))
        self.drug_text.bind("<KeyRelease>", lambda e: self._update_gene_counts())

        # Right: Risk Stratification
        right = ttk.Frame(self.gene_lists_frame)
        right.pack(side="left", fill="both", expand=True, padx=(4, 0))

        right_header = ttk.Frame(right)
        right_header.pack(fill="x")
        ttk.Label(right_header, text="Risk Stratification",
                  font=("Segoe UI", 8, "bold")).pack(side="left")
        self.risk_count_label = ttk.Label(
            right_header, text="", font=("Segoe UI", 8), foreground="#555")
        self.risk_count_label.pack(side="right")

        self.risk_text = tk.Text(right, height=3, width=40,
                                 font=("Consolas", 8), wrap="word",
                                 borderwidth=1, relief="sunken")
        self.risk_text.pack(fill="x", pady=(2, 0))
        self.risk_text.bind("<KeyRelease>", lambda e: self._update_gene_counts())

        # Populate defaults
        self._populate_gene_texts(DRUG_TARGET_GENES, RISK_STRATIFICATION_GENES)
        self._on_actionable_toggle()

    def _populate_gene_texts(self, drug_genes, risk_genes):
        self.drug_text.delete("1.0", "end")
        self.drug_text.insert("1.0", ", ".join(sorted(drug_genes)))
        self.risk_text.delete("1.0", "end")
        self.risk_text.insert("1.0", ", ".join(sorted(risk_genes)))
        self._update_gene_counts()

    def _parse_gene_text(self, text_widget):
        raw = text_widget.get("1.0", "end").strip()
        genes = set()
        for token in raw.replace("\n", ",").replace(";", ",").split(","):
            g = token.strip().upper()
            if g:
                genes.add(g)
        return genes

    def _update_gene_counts(self):
        drug = self._parse_gene_text(self.drug_text)
        risk = self._parse_gene_text(self.risk_text)
        self.drug_count_label.config(text=f"({len(drug)} genes)")
        self.risk_count_label.config(text=f"({len(risk)} genes)")

    def _reset_gene_lists(self):
        self._populate_gene_texts(DRUG_TARGET_GENES, RISK_STRATIFICATION_GENES)

    def _on_tier3_toggle(self):
        state = "normal" if self.tier3_var.get() else "disabled"
        self.tier3_actionable_cb.config(state=state)
        self.tier3_reset_btn.config(state=state)
        self._set_gene_list_state(state)

    def _on_actionable_toggle(self):
        if self.tier3_actionable_var.get() and self.tier3_var.get():
            self._set_gene_list_state("normal")
        else:
            self._set_gene_list_state("disabled")

    def _set_gene_list_state(self, state):
        for widget in (self.drug_text, self.risk_text, self.tier3_reset_btn):
            widget.config(state=state)

    def _sync_filter_config(self):
        """Push GUI filter settings to the worker before pipeline run."""
        tiers = set()
        if self.tier1_var.get():
            tiers.add("Tier 1")
        if self.tier2_var.get():
            tiers.add("Tier 2")
        if self.tier3_var.get():
            tiers.add("Tier 3")
        self.worker.include_tiers = tiers
        self.worker.min_vaf = self.min_vaf_var.get() / 100.0
        self.worker.tier3_actionable_only = self.tier3_actionable_var.get()
        # Build effective actionable set from editable text fields
        drug = self._parse_gene_text(self.drug_text)
        risk = self._parse_gene_text(self.risk_text)
        self.worker.actionable_genes = drug | risk

    def _build_metadata_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=" Patient Metadata (Optional) ",
                               padding=8)
        frame.pack(fill="x", padx=10, pady=2)

        sel_row = ttk.Frame(frame)
        sel_row.pack(fill="x")
        ttk.Label(sel_row, text="File:").pack(side="left")
        self.meta_file_var = tk.StringVar()
        self.meta_combo = ttk.Combobox(sel_row,
                                       textvariable=self.meta_file_var,
                                       state="readonly", width=40)
        self.meta_combo.pack(side="left", padx=4)
        self.meta_combo.bind("<<ComboboxSelected>>",
                             self._on_meta_file_selected)

        fields = ttk.Frame(frame)
        fields.pack(fill="x", pady=4)
        self.meta_patient = tk.StringVar()
        self.meta_reg_no = tk.StringVar()
        self.meta_specimen = tk.StringVar(value="Peripheral Blood")
        self.meta_test_date = tk.StringVar(
            value=datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(fields, text="Patient:").grid(row=0, column=0, sticky="w")
        ttk.Entry(fields, textvariable=self.meta_patient,
                  width=20).grid(row=0, column=1, padx=4)
        ttk.Label(fields, text="Reg No:").grid(row=0, column=2, sticky="w")
        ttk.Entry(fields, textvariable=self.meta_reg_no,
                  width=20).grid(row=0, column=3, padx=4)
        ttk.Label(fields, text="Specimen:").grid(row=1, column=0, sticky="w",
                                                  pady=2)
        ttk.Entry(fields, textvariable=self.meta_specimen,
                  width=20).grid(row=1, column=1, padx=4)
        ttk.Label(fields, text="Test Date:").grid(row=1, column=2, sticky="w")
        ttk.Entry(fields, textvariable=self.meta_test_date,
                  width=20).grid(row=1, column=3, padx=4)

        ttk.Button(fields, text="Save",
                   command=self._save_metadata).grid(row=0, column=4,
                                                      rowspan=2, padx=8)

    def _build_control_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=" Pipeline Control ", padding=8)
        frame.pack(fill="x", padx=10, pady=2)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x")

        self.btn_annotate = ttk.Button(btn_row, text="Step 1: Annotate VCF",
                                       command=self._run_step1)
        self.btn_annotate.pack(side="left", padx=2)
        self.btn_tier = ttk.Button(btn_row, text="Step 2: Tier Report",
                                   command=self._run_step2)
        self.btn_tier.pack(side="left", padx=2)
        self.btn_docx = ttk.Button(btn_row, text="Step 3: DOCX Report",
                                   command=self._run_step3)
        self.btn_docx.pack(side="left", padx=2)
        if not HAS_DOCX:
            self.btn_docx.config(state="disabled")

        sep = ttk.Separator(btn_row, orient="vertical")
        sep.pack(side="left", fill="y", padx=8)

        self.btn_full = ttk.Button(btn_row,
                                   text="  Run Full Pipeline  ",
                                   command=self._run_full)
        self.btn_full.pack(side="left", padx=2)

        self.btn_cancel = ttk.Button(btn_row, text="Cancel",
                                     command=self._cancel, state="disabled")
        self.btn_cancel.pack(side="right", padx=2)

        # Progress
        prog_row = ttk.Frame(frame)
        prog_row.pack(fill="x", pady=(6, 0))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_row,
                                            variable=self.progress_var,
                                            maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.file_progress_label = ttk.Label(prog_row, text="",
                                             font=("Segoe UI", 9))
        self.file_progress_label.pack(side="right")

        self.progress_label = ttk.Label(frame, text="Ready",
                                        font=("Segoe UI", 9))
        self.progress_label.pack(anchor="w")

    def _build_log_frame(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=4)

        # Tab 1: Log
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="  Log  ")
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=14, font=("Consolas", 9),
            state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text.tag_config("error", foreground="#cc0000")
        self.log_text.tag_config("success", foreground="#007700")
        self.log_text.tag_config("header", foreground="#0055aa",
                                 font=("Consolas", 9, "bold"))

        # Tab 2: Tier Summary
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="  Tier Summary  ")

        columns = ("case_id", "total", "tier1", "tier2", "tier3", "tier4",
                    "status")
        self.results_tree = ttk.Treeview(results_frame, columns=columns,
                                         show="headings", height=10)
        for col, heading, width in [
            ("case_id", "Case ID", 200),
            ("total", "Total", 65),
            ("tier1", "Tier 1", 65),
            ("tier2", "Tier 2", 65),
            ("tier3", "Tier 3", 65),
            ("tier4", "Tier 4", 65),
            ("status", "Status", 120),
        ]:
            self.results_tree.heading(col, text=heading)
            self.results_tree.column(col, width=width, anchor="center")
        self.results_tree.column("case_id", anchor="w")
        self.results_tree.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_action_frame(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(frame, text="Open Output Folder",
                   command=self._open_output_folder).pack(side="left", padx=2)
        ttk.Button(frame, text="Open Latest Report",
                   command=self._open_latest_report).pack(side="left", padx=2)

        dep_text = "python-docx: installed" if HAS_DOCX else "python-docx: NOT installed (pip install python-docx)"
        dep_color = "#007700" if HAS_DOCX else "#cc0000"
        dep_label = ttk.Label(frame, text=dep_text,
                              font=("Segoe UI", 8), foreground=dep_color)
        dep_label.pack(side="right", padx=4)

    # ---- Event Handlers ----

    def _browse_vcf(self):
        files = filedialog.askopenfilenames(
            title="Select VCF Files",
            filetypes=[("VCF files", "*.vcf"), ("All files", "*.*")],
            initialdir=str(REPO_ROOT))
        self._add_files(files)

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            title="Select Folder with VCF Files",
            initialdir=str(REPO_ROOT))
        if folder:
            files = sorted(str(f) for f in Path(folder).glob("*.vcf"))
            self._add_files(files)

    def _add_files(self, files):
        for f in files:
            f = str(f)
            if f not in self.vcf_files:
                self.vcf_files.append(f)
                self.file_listbox.insert("end", Path(f).name)
        self._update_meta_combo()
        self._auto_populate_metadata()

    def _clear_files(self):
        self.vcf_files.clear()
        self.file_listbox.delete(0, "end")
        self.meta_combo["values"] = []
        self.meta_file_var.set("")

    def _browse_output(self):
        folder = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir.get() or str(REPO_ROOT))
        if folder:
            self.output_dir.set(folder)

    def _update_meta_combo(self):
        case_ids = [Path(f).stem for f in self.vcf_files]
        self.meta_combo["values"] = case_ids
        if case_ids and not self.meta_file_var.get():
            self.meta_file_var.set(case_ids[0])
            self._load_metadata_for(case_ids[0])

    def _on_meta_file_selected(self, event=None):
        case_id = self.meta_file_var.get()
        if case_id:
            self._load_metadata_for(case_id)

    def _load_metadata_for(self, case_id):
        meta = self.metadata_map.get(case_id, {})
        self.meta_patient.set(meta.get("patient", ""))
        self.meta_reg_no.set(meta.get("reg_no", ""))
        self.meta_specimen.set(meta.get("specimen", "Peripheral Blood"))
        self.meta_test_date.set(
            meta.get("test_date", datetime.now().strftime("%Y-%m-%d")))

    def _save_metadata(self):
        case_id = self.meta_file_var.get()
        if not case_id:
            return
        self.metadata_map[case_id] = {
            "patient": self.meta_patient.get(),
            "reg_no": self.meta_reg_no.get(),
            "specimen": self.meta_specimen.get(),
            "test_date": self.meta_test_date.get(),
        }
        self._append_log(f"Metadata saved for {case_id}", tag="success")

    def _auto_populate_metadata(self):
        for vcf in self.vcf_files:
            case_id = Path(vcf).stem
            if case_id in self.metadata_map:
                continue
            # Try to parse patient name / reg no from filename pattern
            # e.g. "01-JJH_10679562" → patient=JJH, reg_no=10679562
            parts = case_id.split("-", 1)
            if len(parts) == 2:
                name_reg = parts[1].split("_", 1)
                patient = name_reg[0] if len(name_reg) >= 1 else ""
                reg_no = name_reg[1] if len(name_reg) >= 2 else ""
            else:
                patient, reg_no = "", ""
            self.metadata_map[case_id] = {
                "patient": patient,
                "reg_no": reg_no,
                "specimen": "Peripheral Blood",
                "test_date": datetime.now().strftime("%Y-%m-%d"),
            }
        # Load first file's metadata into fields
        if self.meta_file_var.get():
            self._load_metadata_for(self.meta_file_var.get())

    # ---- Pipeline Execution ----

    def _disable_buttons(self):
        for btn in (self.btn_annotate, self.btn_tier,
                    self.btn_docx, self.btn_full):
            btn.config(state="disabled")
        self.btn_cancel.config(state="normal")

    def _enable_buttons(self):
        for btn in (self.btn_annotate, self.btn_tier, self.btn_full):
            btn.config(state="normal")
        if HAS_DOCX:
            self.btn_docx.config(state="normal")
        self.btn_cancel.config(state="disabled")

    def _cancel(self):
        self.worker.cancel_flag.set()
        self._append_log("Cancelling...", tag="error")

    def _validate_files(self):
        if not self.vcf_files:
            messagebox.showwarning("No Files",
                                   "Please select VCF files first.")
            return False
        return True

    def _run_step1(self):
        if not self._validate_files():
            return
        self._disable_buttons()
        self._sync_filter_config()
        self.worker.cancel_flag.clear()
        self.progress_var.set(0)
        out = self._get_effective_output_dir()

        def worker():
            try:
                total = len(self.vcf_files)
                for idx, vcf in enumerate(self.vcf_files):
                    if self.worker.cancel_flag.is_set():
                        break
                    self.worker.post("file_progress",
                                     (idx + 1, total))
                    self.worker.post("log", "")
                    self.worker.post("log",
                        f"[{idx+1}/{total}] {Path(vcf).name}")
                    self.worker.run_annotate(vcf, out)
                self.worker.post("step_done", "annotate")
            except Exception as e:
                self.worker.post("error", traceback.format_exc())
                self.worker.post("step_done", "annotate")

        threading.Thread(target=worker, daemon=True).start()

    def _run_step2(self):
        """Run tier report on existing annotated CSVs in output dir."""
        if not self._validate_files():
            return
        self._disable_buttons()
        self._sync_filter_config()
        self.progress_var.set(0)
        out = self._get_effective_output_dir()

        def worker():
            try:
                total = len(self.vcf_files)
                for idx, vcf in enumerate(self.vcf_files):
                    case_id = Path(vcf).stem
                    annotated = Path(out) / case_id / f"{case_id}_annotated.csv"
                    if not annotated.exists():
                        self.worker.post("error",
                            f"{annotated.name} not found. Run Step 1 first.")
                        continue
                    self.worker.post("file_progress", (idx + 1, total))
                    self.worker.post("progress",
                        (idx + 1, total, f"Tiering {case_id}"))
                    self.worker.run_tier_report(str(annotated), out)
                self.worker.post("step_done", "tier")
            except Exception as e:
                self.worker.post("error", traceback.format_exc())
                self.worker.post("step_done", "tier")

        threading.Thread(target=worker, daemon=True).start()

    def _run_step3(self):
        """Run DOCX generation on existing tiered + annotated CSVs."""
        if not self._validate_files():
            return
        if not HAS_DOCX:
            messagebox.showwarning("Missing Dependency",
                "python-docx is not installed.\n"
                "Run: pip install python-docx")
            return
        self._disable_buttons()
        self.progress_var.set(0)
        out = self._get_effective_output_dir()

        def worker():
            try:
                total = len(self.vcf_files)
                for idx, vcf in enumerate(self.vcf_files):
                    case_id = Path(vcf).stem
                    case_dir = Path(out) / case_id
                    annotated = case_dir / f"{case_id}_annotated.csv"
                    tiered = case_dir / f"{case_id}_tiered_report.csv"
                    if not annotated.exists() or not tiered.exists():
                        self.worker.post("error",
                            f"{case_id}: missing annotated/tiered CSV. "
                            "Run Steps 1-2 first.")
                        continue
                    self.worker.post("file_progress", (idx + 1, total))
                    self.worker.post("progress",
                        (idx + 1, total, f"DOCX {case_id}"))
                    meta = self.metadata_map.get(case_id, {
                        "patient": "", "reg_no": "",
                        "specimen": "Peripheral Blood",
                        "test_date": datetime.now().strftime("%Y-%m-%d"),
                    })
                    self.worker.run_docx_report(
                        case_id, str(tiered), str(annotated), out, meta)
                self.worker.post("step_done", "docx")
            except Exception as e:
                self.worker.post("error", traceback.format_exc())
                self.worker.post("step_done", "docx")

        threading.Thread(target=worker, daemon=True).start()

    def _run_full(self):
        if not self._validate_files():
            return
        self._disable_buttons()
        self._sync_filter_config()
        self.worker.cancel_flag.clear()
        self.progress_var.set(0)
        out = self._get_effective_output_dir()
        vaf_pct = f"{self.min_vaf_var.get():.1f}%"
        tiers_str = []
        if self.tier1_var.get():
            tiers_str.append("T1")
        if self.tier2_var.get():
            tiers_str.append("T2")
        if self.tier3_var.get():
            t3 = "T3-actionable" if self.tier3_actionable_var.get() else "T3-all"
            tiers_str.append(t3)
        self._append_log("=" * 60, tag="header")
        self._append_log(f"Starting full pipeline  "
                         f"[VAF>={vaf_pct}  {'/'.join(tiers_str)}  "
                         f"→ {Path(out).name}/]", tag="header")
        self._append_log("=" * 60, tag="header")

        def worker():
            try:
                total = len(self.vcf_files)
                for idx, vcf in enumerate(self.vcf_files):
                    if self.worker.cancel_flag.is_set():
                        self.worker.post("log", "Pipeline cancelled.")
                        break

                    case_id = Path(vcf).stem
                    self.worker.post("file_progress", (idx + 1, total))
                    self.worker.post("log", "")
                    self.worker.post("log", f"{'='*50}")
                    self.worker.post("log",
                        f"[{idx+1}/{total}] {case_id}")
                    self.worker.post("log", f"{'='*50}")

                    # Step 1
                    annotated = self.worker.run_annotate(vcf, out)
                    if annotated is None:
                        continue

                    # Step 2
                    tiered = self.worker.run_tier_report(annotated, out)

                    # Step 3
                    if HAS_DOCX:
                        meta = self.metadata_map.get(case_id, {
                            "patient": "", "reg_no": "",
                            "specimen": "Peripheral Blood",
                            "test_date": datetime.now().strftime("%Y-%m-%d"),
                        })
                        self.worker.run_docx_report(
                            case_id, tiered, annotated, out, meta)

                self.worker.post("pipeline_done", None)
            except Exception as e:
                self.worker.post("error", traceback.format_exc())
                self.worker.post("pipeline_done", None)

        threading.Thread(target=worker, daemon=True).start()

    # ---- Queue Polling ----

    def _poll_queue(self):
        while not self.msg_queue.empty():
            try:
                msg_type, data = self.msg_queue.get_nowait()
            except queue.Empty:
                break

            if msg_type == "log":
                self._append_log(data)
            elif msg_type == "error":
                self._append_log(data, tag="error")
            elif msg_type == "progress":
                current, total, label = data
                self.progress_var.set(current / total * 100)
                self.progress_label.config(text=label)
            elif msg_type == "file_progress":
                idx, total = data
                self.file_progress_label.config(
                    text=f"File {idx}/{total}")
            elif msg_type == "tier_result":
                self._update_results_table(data)
            elif msg_type == "step_done":
                self._enable_buttons()
                self.progress_label.config(text=f"Step '{data}' complete")
            elif msg_type == "pipeline_done":
                self._enable_buttons()
                self.progress_label.config(text="Pipeline complete")
                self.progress_var.set(100)
                self._append_log("", tag=None)
                self._append_log("Pipeline complete!", tag="success")

        self.master.after(100, self._poll_queue)

    def _append_log(self, text, tag=None):
        self.log_text.config(state="normal")
        if tag:
            self.log_text.insert("end", text + "\n", tag)
        else:
            self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _update_results_table(self, data):
        case_id = data["case_id"]
        tc = data["tier_counts"]

        # Update or insert
        existing = None
        for item in self.results_tree.get_children():
            if self.results_tree.set(item, "case_id") == case_id:
                existing = item
                break

        values = (case_id, data["total"],
                  tc.get("Tier 1", 0), tc.get("Tier 2", 0),
                  tc.get("Tier 3", 0), tc.get("Tier 4", 0),
                  data.get("status", "Done"))

        if existing:
            self.results_tree.item(existing, values=values)
        else:
            self.results_tree.insert("", "end", values=values)

    # ---- Action Buttons ----

    def _open_output_folder(self):
        folder = self._get_effective_output_dir()
        if os.path.isdir(folder):
            os.startfile(folder)
        else:
            messagebox.showinfo("Info",
                f"Directory does not exist yet:\n{folder}")

    def _open_latest_report(self):
        folder = self._get_effective_output_dir()
        if not os.path.isdir(folder):
            messagebox.showinfo("Info", "No output directory found.")
            return
        # Find most recent .docx
        docx_files = sorted(Path(folder).rglob("*_clinical_report.docx"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        if docx_files:
            os.startfile(str(docx_files[0]))
        else:
            # Try CSV
            csv_files = sorted(Path(folder).rglob("*_tiered_report.csv"),
                               key=lambda p: p.stat().st_mtime, reverse=True)
            if csv_files:
                os.startfile(str(csv_files[0]))
            else:
                messagebox.showinfo("Info", "No reports found in output.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()

    style = ttk.Style(root)
    available = style.theme_names()
    for theme in ("vista", "winnative", "clam", "default"):
        if theme in available:
            style.theme_use(theme)
            break

    app = PipelineApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
