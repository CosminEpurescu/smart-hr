"""
Gemini Job Analyzer - Analyzes job postings using Google's Gemini AI model via Vertex AI
"""
import json
import os
from pathlib import Path
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig


class GeminiJobAnalyzer:
    """Analyzes job postings using Gemini AI via Vertex AI."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-001",
        project_id: str = "ai-deniers-486907",
        location: str = "us-central1",
    ):
        """
        Initialize the Gemini analyzer.
        
        Args:
            model_name: The Gemini model to use
            project_id: Google Cloud project ID
            location: Google Cloud region
        """
        self.model_name = model_name
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI - uses GOOGLE_APPLICATION_CREDENTIALS env var
        vertexai.init(project=project_id, location=location)
        
        self.model = GenerativeModel(
            model_name=model_name,
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

    def analyze_job(self, job_data: dict, prompt: Optional[str] = None) -> str:
        """
        Analyze a single job posting.
        
        Args:
            job_data: Job posting data as a dictionary
            prompt: Custom prompt for analysis (optional)
        
        Returns:
            Analysis result from Gemini
        """
        if prompt is None:
            prompt = """Analyze the following job posting and provide:
1. A brief summary of the role (2-3 sentences)
2. Key skills required
3. Experience level assessment
4. Salary insights (if available)
5. Any red flags or notable points

Job Data:
"""
        
        full_prompt = f"{prompt}\n\n{json.dumps(job_data, indent=2)}"
        
        response = self.model.generate_content(full_prompt)
        return response.text

    def compare_jobs(self, jobs: list[dict]) -> str:
        """
        Compare multiple job postings.
        
        Args:
            jobs: List of job posting dictionaries
        
        Returns:
            Comparison analysis from Gemini
        """
        prompt = """Compare the following job postings and provide:
1. Key differences between the roles
2. Salary comparison (if available)
3. Which role might be better for different career goals
4. Common requirements across all roles

Job Postings:
"""
        
        jobs_text = "\n\n---\n\n".join([
            f"Job {i+1}: {job.get('title', 'Unknown')}\n{json.dumps(job, indent=2)}"
            for i, job in enumerate(jobs)
        ])
        
        full_prompt = f"{prompt}\n\n{jobs_text}"
        response = self.model.generate_content(full_prompt)
        return response.text

    def find_matching_jobs(self, jobs: list[dict], candidate_profile: str) -> str:
        """
        Find jobs matching a candidate profile.
        
        Args:
            jobs: List of job posting dictionaries
            candidate_profile: Description of the candidate's skills and experience
        
        Returns:
            Matching analysis from Gemini
        """
        prompt = f"""Given the following candidate profile:
{candidate_profile}

Analyze these job postings and rank them by fit. For each job, explain:
1. Match score (1-10)
2. Why it's a good/bad fit
3. Skills gaps the candidate might need to address

Job Postings:
"""
        
        jobs_text = "\n\n---\n\n".join([
            f"Job: {job.get('title', 'Unknown')}\n{json.dumps(job, indent=2)}"
            for job in jobs
        ])
        
        full_prompt = f"{prompt}\n\n{jobs_text}"
        response = self.model.generate_content(full_prompt)
        return response.text

    def chat(self, message: str) -> str:
        """
        Simple chat with Gemini.
        
        Args:
            message: User message
        
        Returns:
            Gemini response
        """
        response = self.model.generate_content(message)
        return response.text

    def extract_job_info(self, job_data: dict) -> dict:
        """
        Extract structured information from a job posting.
        
        Args:
            job_data: Raw job posting data
        
        Returns:
            Extracted job information as a dictionary
        """
        prompt = """You are a job posting analyzer. Extract the following information from the job posting below.
Output MUST be valid JSON only, no other text or markdown formatting.
All output MUST be in English, even if the job posting is in another language - translate as needed.

Extract these fields:
- job_id: The job ID from the original data
- job_title: The job title (in English)
- location: Object with city, country, and work_model (remote/hybrid/onsite)
- salary: Object with min, max, currency, and period (e.g., "yearly", "monthly") - set to null if not available
- description: A brief 2-3 sentence summary of the role in English
- skills: Array of hard/technical skills required (e.g., programming languages, tools, certifications)
- soft_skills: Array of soft skills mentioned (e.g., communication, leadership, teamwork)
- tasks: Array of main responsibilities/tasks for this role

Output format:
{
    "job_id": "string",
    "job_title": "string",
    "location": {
        "city": "string or null",
        "country": "string or null",
        "work_model": "remote|hybrid|onsite|null"
    },
    "salary": {
        "min": number or null,
        "max": number or null,
        "currency": "string or null",
        "period": "string or null"
    } or null,
    "description": "string",
    "skills": ["string"],
    "soft_skills": ["string"],
    "tasks": ["string"]
}

Job Posting Data:
"""
        
        full_prompt = f"{prompt}\n\n{json.dumps(job_data, indent=2)}"
        
        response = self.model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.startswith("```")]
            response_text = "\n".join(lines)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response_text[:500]}...")
            return {
                "job_id": job_data.get("job_id", "unknown"),
                "job_title": job_data.get("title", "unknown"),
                "error": f"Failed to parse response: {str(e)}",
                "raw_response": response_text[:1000]
            }


def load_jobs_from_directory(directory: str) -> list[tuple[Path, dict]]:
    """Load all job JSON files from a directory."""
    jobs = []
    path = Path(directory)
    
    for json_file in sorted(path.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                job_data = json.load(f)
                jobs.append((json_file, job_data))
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return jobs


def process_and_extract_jobs(input_dir: str, output_dir: str, limit: Optional[int] = None, skip_existing: bool = True, workers: int = 10):
    """
    Process all job files and extract structured information.
    
    Args:
        input_dir: Directory containing raw job JSON files
        output_dir: Directory to save extracted job information
        limit: Maximum number of jobs to process (None for all)
        skip_existing: Skip jobs that have already been processed
        workers: Number of parallel workers (default: 10)
    """
    from tqdm import tqdm
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load jobs
    jobs = load_jobs_from_directory(input_dir)
    print(f"Loaded {len(jobs)} jobs from {input_dir}")
    
    if not jobs:
        print("No jobs found!")
        return
    
    # Apply limit
    if limit is not None:
        jobs = jobs[:limit]
        print(f"Processing {len(jobs)} jobs (limit: {limit})")
    
    # Filter out already processed jobs if skip_existing
    jobs_to_process = []
    skipped = 0
    for json_file, job_data in jobs:
        job_id = job_data.get("job_id", json_file.stem)
        output_file = output_path / f"{job_id}_extracted.json"
        if skip_existing and output_file.exists():
            skipped += 1
        else:
            jobs_to_process.append((json_file, job_data, output_file))
    
    if skipped > 0:
        print(f"Skipping {skipped} already processed jobs")
    
    if not jobs_to_process:
        print("All jobs already processed!")
        return
    
    print(f"Processing {len(jobs_to_process)} jobs with {workers} workers")
    
    # Worker function
    def process_single_job(args):
        json_file, job_data, output_file = args
        job_id = job_data.get("job_id", json_file.stem)
        
        try:
            # Each worker needs its own analyzer instance
            analyzer = GeminiJobAnalyzer()
            
            # Extract information using Gemini
            extracted = analyzer.extract_job_info(job_data)
            
            # Save to output directory
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extracted, f, indent=2, ensure_ascii=False)
            
            return (job_id, True, None)
        except Exception as e:
            return (job_id, False, str(e))
    
    # Process in parallel
    successful = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_job, job): job for job in jobs_to_process}
        
        with tqdm(total=len(jobs_to_process), desc="Extracting job info") as pbar:
            for future in as_completed(futures):
                job_id, success, error = future.result()
                if success:
                    successful += 1
                else:
                    failed += 1
                    print(f"\nError processing {job_id}: {error}")
                pbar.update(1)
    
    print(f"\nProcessing complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")


def main():
    """Main function to extract structured job information."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract structured job information using Gemini AI")
    parser.add_argument(
        "-i", "--input",
        default=str(Path(__file__).parent / "jobs_detailed"),
        help="Input directory containing raw job JSON files (default: jobs_detailed)"
    )
    parser.add_argument(
        "-o", "--output",
        default=str(Path(__file__).parent / "jobs_extracted"),
        help="Output directory for extracted job information (default: jobs_extracted)"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Maximum number of jobs to process (default: all)"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Reprocess jobs even if they already exist"
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash-001",
        help="Gemini model to use (default: gemini-2.0-flash-001)"
    )
    parser.add_argument(
        "--project",
        default="ai-deniers-486907",
        help="Google Cloud project ID"
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Google Cloud region (default: us-central1)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=10,
        help="Number of parallel workers (default: 10)"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        return
    
    print("=" * 60)
    print("Job Information Extractor")
    print("=" * 60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Limit:  {args.limit or 'all'}")
    print(f"Model:  {args.model}")
    print(f"Workers: {args.workers}")
    print("=" * 60)
    
    process_and_extract_jobs(
        str(input_dir),
        str(output_dir),
        limit=args.limit,
        skip_existing=not args.no_skip,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
