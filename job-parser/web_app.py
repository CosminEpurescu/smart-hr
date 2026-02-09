"""
Web interface for CV to Job Matcher
"""
import os
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from cv_matcher import (
    CVJobMatchingPipeline,
    FileJobStore,
    extract_text_from_pdf,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize job store
JOBS_DIR = Path(__file__).parent / "jobs_extracted"
job_store = FileJobStore(str(JOBS_DIR))


def get_all_jobs_for_dropdown():
    """Get all jobs for the dropdown, with id and title."""
    jobs = job_store.get_all_jobs()
    return [
        {
            "job_id": job.get("job_id", ""),
            "job_title": job.get("job_title", "Unknown Title"),
            "location": job.get("location", {}),
        }
        for job in jobs
        if job.get("job_id")
    ]


@app.route("/")
def index():
    """Render the main page."""
    jobs = get_all_jobs_for_dropdown()
    # Sort by title
    jobs.sort(key=lambda x: x["job_title"])
    return render_template("index.html", jobs=jobs)


@app.route("/api/jobs")
def api_jobs():
    """API endpoint to get all jobs."""
    jobs = get_all_jobs_for_dropdown()
    jobs.sort(key=lambda x: x["job_title"])
    return jsonify(jobs)


@app.route("/api/match", methods=["POST"])
def api_match():
    """API endpoint to match a CV to jobs."""
    # Check for file
    if "cv_file" not in request.files:
        return jsonify({"error": "No CV file provided"}), 400
    
    cv_file = request.files["cv_file"]
    if cv_file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    # Get job ID
    job_id = request.form.get("job_id")
    if not job_id:
        return jsonify({"error": "No job selected"}), 400
    
    # Get top_n parameter
    top_n = int(request.form.get("top_n", 5))
    
    # Save file temporarily and extract text
    try:
        suffix = Path(cv_file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            cv_file.save(tmp.name)
            tmp_path = tmp.name
        
        # Extract text based on file type
        if suffix == ".pdf":
            cv_text = extract_text_from_pdf(tmp_path)
        else:
            with open(tmp_path, "r", encoding="utf-8") as f:
                cv_text = f.read()
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if not cv_text.strip():
            return jsonify({"error": "Could not extract text from CV"}), 400
        
        # Initialize pipeline and process
        pipeline = CVJobMatchingPipeline(
            use_files=True,
            jobs_directory=str(JOBS_DIR),
        )
        
        result = pipeline.process_application(
            cv_text=cv_text,
            applied_job_id=job_id,
            top_n=top_n,
        )
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500


if __name__ == "__main__":
    # Ensure credentials are set
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
    
    print("Starting CV Matcher Web Interface...")
    print(f"Jobs directory: {JOBS_DIR}")
    print(f"Total jobs available: {len(get_all_jobs_for_dropdown())}")
    
    app.run(debug=True, host="0.0.0.0", port=5001)
