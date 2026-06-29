"""
Flask web app: upload a CSV of reviews → get a product insights report.

Usage:
    ANTHROPIC_API_KEY=sk-... python -m src.web_app   # cloud / Claude API
    python -m src.web_app                             # local Ollama
"""
import csv
import io
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, Response

from .ingest import load_reviews, detect_apps
from .full_pipeline import aggregate_chunks, process_chunk, _text_verified_negatives
from .pipeline_strategy import get_strategy, estimate_time_minutes
from .synthesizer import run_synthesis, compute_quality_metrics
from .report_html import generate_html

app = Flask(__name__, template_folder=str(Path(__file__).parent.parent / "templates"))

PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_DIR = PROJECT_ROOT / "results" / "uploads"
RUNS_DIR = PROJECT_ROOT / "results" / "runs"
ALLOWED_EXTENSIONS = {"csv"}

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _update_job(job_id: str, **kwargs):
    with _jobs_lock:
        for k, v in kwargs.items():
            if v is not None:
                _jobs[job_id][k] = v


def _run_pipeline(job_id: str, csv_path: Path):
    try:
        _update_job(job_id, status="running", progress=2, message="Reading your reviews...")

        df = load_reviews(str(csv_path))
        total_uploaded = len(df)

        apps = detect_apps(df)

        run_dir = RUNS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{job_id[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)

        if apps:
            _update_job(job_id, progress=4,
                        message=f"Detected {len(apps)} apps — analyzing each separately...")
            app_results = {}
            all_rows = []
            for app_idx, app_name in enumerate(apps):
                app_df = df[df["app"] == app_name].copy()
                app_result, app_rows = _process_app(
                    job_id, app_name, app_df, run_dir,
                    app_idx, len(apps),
                )
                app_results[app_name] = app_result
                all_rows.extend(app_rows)

            with _jobs_lock:
                _jobs[job_id]["rows"] = all_rows

            _update_job(job_id, progress=93, message="Building your multi-app insights report...")

            html_path = run_dir / "report.html"
            output_path = run_dir / "output.json"
            with open(output_path, "w") as f:
                json.dump({"apps": app_results, "multi_app": True}, f, indent=2)

            generate_html(
                {"apps": app_results, "multi_app": True},
                str(html_path),
                data_path=str(csv_path),
                job_id=job_id,
            )
        else:
            # Single-app (or no app column) — original flow
            strategy = get_strategy(total_uploaded)
            sample_n = strategy["sample_size"]
            batch_size = strategy["batch_size"]
            tier = strategy["tier"]

            if sample_n < total_uploaded:
                df = df.sample(n=sample_n, random_state=42)

            rows = df.to_dict(orient="records")
            total = len(rows)

            est_time = estimate_time_minutes(total, batch_size)
            _update_job(
                job_id,
                progress=5,
                message=f"{strategy['label']} — estimated time: {est_time}",
                total_reviews=total_uploaded,
                analyzed_reviews=total,
                tier=tier,
            )

            with _jobs_lock:
                _jobs[job_id]["rows"] = rows

            chunks_dir = run_dir / "chunks"
            chunks_dir.mkdir(exist_ok=True)

            chunks = [rows[i:i + batch_size] for i in range(0, total, batch_size)]
            negatives = _text_verified_negatives(rows)
            if len(negatives) >= 5:
                chunks.append(negatives)

            n_chunks = len(chunks)
            chunk_results = []
            failed = 0

            progress_messages = [
                "Identifying customer pain points...",
                "Finding what customers love...",
                "Extracting key themes...",
                "Analyzing complaint patterns...",
                "Spotting improvement opportunities...",
                "Reviewing customer feedback...",
            ]

            for i, chunk_rows in enumerate(chunks):
                pct = 5 + int((i / n_chunks) * 72)
                msg = progress_messages[i % len(progress_messages)]
                _update_job(job_id, progress=pct, message=f"{msg} ({i + 1}/{n_chunks})")
                result = process_chunk(chunk_rows, i, chunks_dir)
                if result is None:
                    failed += 1
                chunk_results.append(result)

            _update_job(job_id, progress=78, message="Aggregating insights across all reviews...")

            n = len(rows)
            pos = sum(1 for r in rows if int(r["label"]) == 1)
            sentiment = {
                "positive_rate": round(pos / n, 4),
                "negative_rate": round((n - pos) / n, 4),
                "n_reviews": n,
            }

            top_strengths, top_complaints, summary_bullets = aggregate_chunks(chunk_results)
            aggregated = {
                "summary_bullets": summary_bullets,
                "top_strengths": top_strengths,
                "top_complaints": top_complaints,
                "sentiment": sentiment,
            }

            _update_job(job_id, progress=83, message="Generating executive summary and recommendations...")
            synthesis = run_synthesis(aggregated)

            _update_job(job_id, progress=88, message="Running quality checks...")
            quality = compute_quality_metrics(chunk_results, aggregated)

            final = {
                **aggregated,
                **synthesis,
                "unknowns": [],
                "quality": quality,
                "meta": {
                    "total_uploaded": total_uploaded,
                    "total_analyzed": total,
                    "tier": tier,
                    "chunks_processed": n_chunks - failed,
                    "chunks_failed": failed,
                    "batch_size": batch_size,
                },
            }

            output_path = run_dir / "output.json"
            with open(output_path, "w") as f:
                json.dump(final, f, indent=2)

            _update_job(job_id, progress=93, message="Building your insights report...")

            html_path = run_dir / "report.html"
            generate_html(final, str(html_path), data_path=str(csv_path), job_id=job_id)

        _update_job(
            job_id,
            status="done",
            progress=100,
            message="Your insights report is ready!",
            report_path=str(html_path),
            output_path=str(output_path),
            embed_status="pending",
        )

        t = threading.Thread(target=_run_embedding, args=(job_id,), daemon=True)
        t.start()

    except Exception as e:
        _update_job(job_id, status="error", error=str(e), message=f"Something went wrong: {e}")


def _process_app(job_id, app_name, app_df, run_dir, app_idx, total_apps):
    """Run the pipeline for a single app. Returns (final_dict, rows)."""
    n_app = len(app_df)
    strategy = get_strategy(n_app)
    sample_n = strategy["sample_size"]
    batch_size = strategy["batch_size"]
    tier = strategy["tier"]

    if sample_n < n_app:
        app_df = app_df.sample(n=sample_n, random_state=42)

    rows = app_df.to_dict(orient="records")
    total = len(rows)

    # Progress spans a slice of 5–90% divided by number of apps
    base_pct = 5 + int((app_idx / total_apps) * 85)
    end_pct = 5 + int(((app_idx + 1) / total_apps) * 85)

    _update_job(
        job_id,
        progress=base_pct,
        message=f"Analyzing {app_name} ({app_idx + 1}/{total_apps}) — {total} reviews...",
    )

    chunks_dir = run_dir / f"chunks_{app_name.replace(' ', '_').lower()}"
    chunks_dir.mkdir(exist_ok=True)

    chunks = [rows[i:i + batch_size] for i in range(0, total, batch_size)]
    negatives = _text_verified_negatives(rows)
    if len(negatives) >= 5:
        chunks.append(negatives)

    n_chunks = len(chunks)
    chunk_results = []
    failed = 0

    for i, chunk_rows in enumerate(chunks):
        pct = base_pct + int((i / n_chunks) * (end_pct - base_pct))
        _update_job(job_id, progress=pct,
                    message=f"Analyzing {app_name} — chunk {i + 1}/{n_chunks}...")
        result = process_chunk(chunk_rows, i, chunks_dir)
        if result is None:
            failed += 1
        chunk_results.append(result)

    n = len(rows)
    pos = sum(1 for r in rows if int(r["label"]) == 1)
    sentiment = {
        "positive_rate": round(pos / n, 4),
        "negative_rate": round((n - pos) / n, 4),
        "n_reviews": n,
    }

    top_strengths, top_complaints, summary_bullets = aggregate_chunks(chunk_results)
    aggregated = {
        "summary_bullets": summary_bullets,
        "top_strengths": top_strengths,
        "top_complaints": top_complaints,
        "sentiment": sentiment,
    }

    _update_job(
        job_id, progress=end_pct - 2,
        message=f"Synthesizing insights for {app_name}...",
    )
    synthesis = run_synthesis(aggregated)
    quality = compute_quality_metrics(chunk_results, aggregated)

    final = {
        **aggregated,
        **synthesis,
        "quality": quality,
        "meta": {
            "app": app_name,
            "total_uploaded": n_app,
            "total_analyzed": total,
            "tier": tier,
            "chunks_processed": n_chunks - failed,
            "chunks_failed": failed,
            "batch_size": batch_size,
        },
    }

    return final, rows


def _run_embedding(job_id: str):
    try:
        from .embeddings import build_index, collection_exists

        with _jobs_lock:
            rows = _jobs[job_id].get("rows", [])

        if not rows or collection_exists(job_id):
            _update_job(job_id, embed_status="ready")
            return

        total = len(rows)
        _update_job(job_id, embed_status="indexing", embed_progress=0,
                    embed_message=f"Preparing search index for {total} reviews...")

        def progress_cb(done, total, model):
            pct = int(done / total * 100)
            _update_job(job_id, embed_progress=pct,
                        embed_message=f"Indexing reviews for Q&A ({done}/{total})...")

        build_index(job_id, rows, progress_cb=progress_cb)
        _update_job(job_id, embed_status="ready", embed_progress=100,
                    embed_message="Search index ready!")

    except Exception as e:
        _update_job(job_id, embed_status="error", embed_message=f"Search indexing failed: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    using_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return render_template("index.html", using_claude=using_claude)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename or not _allowed(f.filename):
        return jsonify({"error": "File must be a .csv"}), 400

    job_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = UPLOAD_DIR / f"{job_id}.csv"
    f.save(str(csv_path))

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "message": "Starting analysis...",
            "embed_status": "waiting",
            "embed_progress": 0,
            "embed_message": "",
        }

    t = threading.Thread(target=_run_pipeline, args=(job_id, csv_path), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id: str):
    with _jobs_lock:
        job = {k: v for k, v in (_jobs.get(job_id) or {}).items() if k != "rows"}
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/report/<job_id>")
def report(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or job.get("status") != "done":
        return "Report not ready", 404
    report_path = job.get("report_path")
    if not report_path or not Path(report_path).exists():
        return "Report file missing", 404
    return send_file(report_path)


@app.route("/ask/<job_id>", methods=["POST"])
def ask(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job.get("embed_status") != "ready":
        return jsonify({"error": "Search index not ready yet — please wait a moment."}), 202

    data = request.get_json()
    question = (data or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        from .ask import ask_question
        result = ask_question(job_id, question)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/export/csv/<job_id>")
def export_csv(job_id: str):
    """Download enriched insights as CSV."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or job.get("status") != "done":
        return "Report not ready", 404

    output_path = job.get("output_path", "")
    if not output_path or not Path(output_path).exists():
        return "Output data missing", 404

    with open(output_path) as f:
        data = json.load(f)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "app", "type", "theme", "review_count", "confidence", "priority",
        "quote_1", "review_id_1", "quote_2", "review_id_2", "quote_3", "review_id_3"
    ])

    def ev(evidence, i):
        if i < len(evidence):
            return evidence[i].get("quote", ""), evidence[i].get("review_id", "")
        return "", ""

    def write_app_rows(app_label, d):
        for item in d.get("top_complaints", []):
            e = item.get("evidence", [])
            writer.writerow([app_label, "complaint", item["theme"], item["review_count"],
                             item["confidence"], "review", *ev(e,0), *ev(e,1), *ev(e,2)])
        for item in d.get("top_strengths", []):
            e = item.get("evidence", [])
            writer.writerow([app_label, "strength", item["theme"], item["review_count"],
                             item["confidence"], "", *ev(e,0), *ev(e,1), *ev(e,2)])
        for rec in d.get("improvement_recommendations", []):
            writer.writerow([app_label, "improvement", rec.get("title",""), "",
                             rec.get("priority",""), "action", rec.get("description",""), "",
                             rec.get("business_impact",""), "", "", ""])
        for rec in d.get("listing_recommendations", []):
            writer.writerow([app_label, "listing_rec", rec.get("title",""), "", "", "listing",
                             rec.get("description",""), "", rec.get("rationale",""), "", "", ""])

    if data.get("multi_app") and "apps" in data:
        for app_name, app_data in data["apps"].items():
            write_app_rows(app_name, app_data)
    else:
        write_app_rows("", data)

    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=review_insights.csv"},
    )


@app.route("/export/report/<job_id>")
def export_report(job_id: str):
    """Download the HTML report as a file."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or job.get("status") != "done":
        return "Report not ready", 404
    report_path = job.get("report_path")
    if not report_path or not Path(report_path).exists():
        return "Report file missing", 404
    return send_file(
        report_path,
        as_attachment=True,
        download_name="product_insights_report.html",
    )


@app.route("/sample")
def sample():
    sample_path = PROJECT_ROOT / "data" / "sample" / "angry_birds_50.csv"
    if not sample_path.exists():
        return "Sample not found", 404
    return send_file(str(sample_path), as_attachment=True, download_name="sample_reviews.csv")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = not os.environ.get("ANTHROPIC_API_KEY")
    app.run(host="0.0.0.0", port=port, debug=debug)
