"""
Web interface for CV to Job Matcher
"""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from cv_matcher import (
    CVJobMatchingPipeline,
    FileJobStore,
    extract_text_from_pdf,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = 'ing-smart-hr-2026'

# Initialize job store
JOBS_DIR = Path(__file__).parent / "jobs_extracted"
JOBS_DETAILED_DIR = Path(__file__).parent / "jobs_detailed"
job_store = FileJobStore(str(JOBS_DIR))

# Store analytics data in memory (in production, use a database)
analytics_data = {
    "searches": [],
    "skill_frequency": {},
    "location_distribution": {},
    "match_scores": [],
}


def get_job_url(job_id: str) -> str:
    """Get the URL for a job from the detailed jobs directory."""
    # Try to find the detailed job file
    for json_file in JOBS_DETAILED_DIR.glob(f"{job_id}_*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                job_data = json.load(f)
                if job_data.get("url"):
                    return job_data["url"]
        except:
            pass
    # Fallback: construct a search URL
    return f"https://careers.ing.com/en/search-jobs/{job_id}"


def get_all_jobs_for_dropdown():
    """Get all jobs for the dropdown, with id and title."""
    jobs = job_store.get_all_jobs()
    return [
        {
            "job_id": job.get("job_id", ""),
            "job_title": job.get("job_title", "Unknown Title"),
            "location": job.get("location", {}),
            "url": get_job_url(job.get("job_id", "")),
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
    
    # Get optional salary range from HR
    hr_salary_min = request.form.get("salary_min")
    hr_salary_max = request.form.get("salary_max")
    hr_salary_range = None
    if hr_salary_min or hr_salary_max:
        hr_salary_range = {
            "min": int(hr_salary_min) if hr_salary_min else None,
            "max": int(hr_salary_max) if hr_salary_max else None,
        }
    
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
        
        # Store HR salary range in result for interview questions
        result["hr_salary_range"] = hr_salary_range
        
        # Add job URLs to results
        if result.get("applied_job") and result["applied_job"].get("match"):
            result["applied_job"]["match"]["url"] = get_job_url(job_id)
        
        for alt_job in result.get("alternative_jobs", []):
            alt_job["url"] = get_job_url(alt_job.get("job_id", ""))
        
        # Update analytics
        analytics_data["searches"].append({
            "timestamp": datetime.now().isoformat(),
            "candidate_name": result.get("cv_profile", {}).get("name", "Unknown"),
            "applied_job_id": job_id,
            "applied_job_score": result.get("applied_job", {}).get("match", {}).get("match_score", 0),
            "top_alternative_score": result.get("alternative_jobs", [{}])[0].get("match_score", 0) if result.get("alternative_jobs") else 0,
        })
        
        # Track skill frequency
        for skill in result.get("cv_profile", {}).get("skills", []):
            analytics_data["skill_frequency"][skill] = analytics_data["skill_frequency"].get(skill, 0) + 1
        
        # Track location distribution
        location = result.get("cv_profile", {}).get("location", "Unknown")
        analytics_data["location_distribution"][location] = analytics_data["location_distribution"].get(location, 0) + 1
        
        # Track match scores
        if result.get("applied_job", {}).get("match"):
            analytics_data["match_scores"].append(result["applied_job"]["match"]["match_score"])
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500


@app.route("/api/analytics")
def api_analytics():
    """API endpoint to get analytics data."""
    # Calculate summary statistics
    searches = analytics_data["searches"]
    match_scores = analytics_data["match_scores"]
    
    summary = {
        "total_searches": len(searches),
        "avg_applied_score": sum(s.get("applied_job_score", 0) for s in searches) / len(searches) if searches else 0,
        "avg_top_alternative_score": sum(s.get("top_alternative_score", 0) for s in searches) / len(searches) if searches else 0,
        "score_distribution": {
            "excellent": len([s for s in match_scores if s >= 80]),
            "good": len([s for s in match_scores if 60 <= s < 80]),
            "fair": len([s for s in match_scores if 40 <= s < 60]),
            "poor": len([s for s in match_scores if s < 40]),
        },
        "top_skills": sorted(analytics_data["skill_frequency"].items(), key=lambda x: x[1], reverse=True)[:15],
        "location_distribution": analytics_data["location_distribution"],
        "recent_searches": searches[-10:][::-1],  # Last 10, newest first
    }
    
    return jsonify(summary)


@app.route("/api/interview-questions", methods=["POST"])
def api_interview_questions():
    """Generate interview questions based on CV and job matches."""
    try:
        data = request.get_json()
        
        cv_profile = data.get("cv_profile", {})
        applied_job = data.get("applied_job", {})
        alternative_jobs = data.get("alternative_jobs", [])[:3]  # Top 3 alternatives
        hr_salary_range = data.get("hr_salary_range")
        
        # Initialize Vertex AI
        vertexai.init(project="ai-deniers-486907", location="us-central1")
        model = GenerativeModel(
            model_name="gemini-2.0-flash-001",
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            )
        )
        
        # Build salary context
        salary_context = ""
        if hr_salary_range:
            salary_context = f"\nHR Budget Range: {hr_salary_range.get('min', 'N/A')} - {hr_salary_range.get('max', 'N/A')} EUR"
        if cv_profile.get("desired_salary"):
            sal = cv_profile["desired_salary"]
            salary_context += f"\nCandidate Expectation: {sal.get('min', 'N/A')} - {sal.get('max', 'N/A')} {sal.get('currency', 'EUR')}"
        
        # Build prompt
        prompt = f"""You are an expert HR interviewer at ING Bank. Generate interview questions and suggested answers for a candidate.

CANDIDATE PROFILE:
- Name: {cv_profile.get('name', 'Unknown')}
- Years of Experience: {cv_profile.get('years_of_experience', 'Unknown')}
- Skills: {', '.join(cv_profile.get('skills', [])[:15])}
- Soft Skills: {', '.join(cv_profile.get('soft_skills', []))}
- Languages: {', '.join(cv_profile.get('languages', []))}
- Location: {cv_profile.get('location', 'Unknown')}{salary_context}

APPLIED JOB:
- Title: {applied_job.get('job_title', 'Unknown')}
- Match Score: {applied_job.get('match', {}).get('match_score', 'N/A')}/100
- Matching Skills: {', '.join(applied_job.get('match', {}).get('matching_skills', []))}
- Missing Skills: {', '.join(applied_job.get('match', {}).get('missing_skills', []))}

TOP ALTERNATIVE JOBS (better fits):
{chr(10).join([f"- {j.get('job_title', 'Unknown')} (Score: {j.get('match_score', 'N/A')})" for j in alternative_jobs])}

Generate interview questions in these categories. For each question, provide a suggested ideal answer based on the candidate's profile.
Output MUST be valid JSON only.

{{
    "technical_questions": [
        {{
            "question": "string",
            "purpose": "What this question assesses",
            "ideal_answer": "Suggested answer based on candidate profile",
            "follow_up": "Optional follow-up question"
        }}
    ],
    "behavioral_questions": [
        {{
            "question": "string",
            "purpose": "string",
            "ideal_answer": "string",
            "follow_up": "string"
        }}
    ],
    "skill_gap_questions": [
        {{
            "question": "string",
            "skill": "The missing skill being addressed",
            "purpose": "string",
            "what_to_look_for": "What would indicate candidate can learn this"
        }}
    ],
    "career_fit_questions": [
        {{
            "question": "string",
            "purpose": "string",
            "red_flags": "What answers might be concerning",
            "green_flags": "What answers would be positive"
        }}
    ],
    "salary_negotiation": {{
        "suggested_talking_points": ["string"],
        "market_context": "Brief context about the role and compensation"
    }}
}}

Generate 3 questions per category."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up response
        if "```" in response_text:
            lines = response_text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(lines)
        
        questions = json.loads(response_text)
        return jsonify(questions)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Ensure credentials are set
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
    
    print("Starting CV Matcher Web Interface...")
    print(f"Jobs directory: {JOBS_DIR}")
    print(f"Total jobs available: {len(get_all_jobs_for_dropdown())}")
    
    app.run(debug=True, host="0.0.0.0", port=5001)
