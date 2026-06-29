"""
Flask web app: upload a CSV of reviews and get a Review Intelligence HTML report.

Usage:
    ANTHROPIC_API_KEY=sk-... python -m src.web_app
    # Or without API key (requires local Ollama):
    python -m src.web_app
"""
import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for

from .ingest import load_reviews
from .full_pipeline import aggregate_chunks, process_chunk
from .report_html import generate_html

app = Flask(__name__, template_folder=str(Path(__file__).parent.parent / "templates"))

UPLOAD_DIR = Path("results/uploads")
RUNS_DIR = Path("results/runs")
ALLOWED_EXTENSIONS = {"csv"}

# In-memory job store: job_id -> status dict
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _run_pipeline(job_id: str, csv_path: Path, max_reviews: int, chunk_size: int):
    def update(status=None, progress=None, message=None, error=None, report_path=None):
        with _jobs_lock:
            if status:
                _jobs[job_id]["status"] = status
            if progress is not None:
                _jobs[job_id]["progress"] = progress
            if message:
                _jobs[job_id]["message"] = message
            if error:
                _jobs[job_id]["error"] = error
            if report_path:
                _jobs[job_id]["report_path"] = report_path

    try:
        update(status="running", progress=0, message="Loading reviews...")

        df = load_reviews(str(csv_path))
        if max_reviews:
            sample_n = min(max_reviews, len(df))
            df = df.sample(n=sample_n, random_state=42)

        rows = df.to_dict(orient="records")
        total = len(rows)

        # Set up run directory
        run_dir = RUNS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{job_id[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)
        chunks_dir = run_dir / "chunks"
        chunks_dir.mkdir(exist_ok=True)

        chunks = [rows[i:i + chunk_size] for i in range(0, total, chunk_size)]
        negatives = [r for r in rows if int(r.get("label", 1)) == 0]
        if len(negatives) >= 5:
            chunks.append(negatives)

        n_chunks = len(chunks)
        update(message=f"Processing {total} reviews in {n_chunks} chunks...")

        chunk_results = []
        failed = 0
        for i, chunk_rows in enumerate(chunks):
            pct = int((i / n_chunks) * 85)  # reserve last 15% for aggregation
            update(progress=pct, message=f"Processing chunk {i + 1}/{n_chunks}...")
            result = process_chunk(chunk_rows, i, chunks_dir)
            if result is None:
                failed += 1
            chunk_results.append(result)

        update(progress=87, message="Aggregating themes...")

        n = len(rows)
        pos = sum(1 for r in rows if int(r["label"]) == 1)
        sentiment = {
            "positive_rate": round(pos / n, 4),
            "negative_rate": round((n - pos) / n, 4),
            "n_reviews": n,
        }

        top_strengths, top_complaints, summary_bullets = aggregate_chunks(chunk_results)

        final = {
            "summary_bullets": summary_bullets,
            "top_strengths": top_strengths,
            "top_complaints": top_complaints,
            "sentiment": sentiment,
            "unknowns": [],
            "meta": {
                "total_reviews": total,
                "chunks_processed": n_chunks - failed,
                "chunks_failed": failed,
                "chunk_size": chunk_size,
            },
        }

        output_path = run_dir / "output.json"
        with open(output_path, "w") as f:
            json.dump(final, f, indent=2)

        update(progress=95, message="Generating HTML report...")

        html_path = run_dir / "report.html"
        generate_html(final, str(html_path), data_path=str(csv_path))

        update(status="done", progress=100, message="Report ready!", report_path=str(html_path))

    except Exception as e:
        update(status="error", error=str(e), message=f"Pipeline failed: {e}")


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

    max_reviews = request.form.get("max_reviews", 200, type=int)
    chunk_size = request.form.get("chunk_size", 50, type=int)

    job_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = UPLOAD_DIR / f"{job_id}.csv"
    f.save(str(csv_path))

    with _jobs_lock:
        _jobs[job_id] = {"status": "queued", "progress": 0, "message": "Queued..."}

    t = threading.Thread(
        target=_run_pipeline, args=(job_id, csv_path, max_reviews, chunk_size), daemon=True
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
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


@app.route("/sample")
def sample():
    sample_path = Path("data/sample/angry_birds_50.csv")
    if not sample_path.exists():
        return "Sample not found", 404
    return send_file(str(sample_path), as_attachment=True, download_name="angry_birds_sample.csv")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = not os.environ.get("ANTHROPIC_API_KEY")  # debug off in prod
    app.run(host="0.0.0.0", port=port, debug=debug)
