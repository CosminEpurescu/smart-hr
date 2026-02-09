"""
CV to Job Matcher - Matches CVs against job postings using Gemini AI and MongoDB
"""
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from pymongo import MongoClient
from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    reader = PdfReader(pdf_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


@dataclass
class CVProfile:
    """Structured CV data extracted by the model."""
    name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    summary: str
    years_of_experience: Optional[int]
    education: list[dict]  # [{degree, field, institution, year}]
    skills: list[str]  # Technical/hard skills
    soft_skills: list[str]
    languages: list[str]
    work_experience: list[dict]  # [{title, company, duration, responsibilities}]
    certifications: list[str]
    desired_role: Optional[str]
    desired_salary: Optional[dict]  # {min, max, currency}


@dataclass
class JobMatch:
    """A job match result with score and reasoning."""
    job_id: str
    job_title: str
    location: dict
    match_score: float  # 0-100
    skill_match: float  # 0-100
    experience_match: float  # 0-100
    matching_skills: list[str]
    missing_skills: list[str]
    reasoning: str
    is_applied_job: bool = False


class FileJobStore:
    """File-based job store - reads directly from extracted JSON files."""
    
    def __init__(self, jobs_directory: str = "jobs_extracted"):
        self.jobs_dir = Path(jobs_directory)
        self._jobs_cache: Optional[list[dict]] = None
        
    def _load_jobs(self) -> list[dict]:
        """Load all jobs from JSON files."""
        if self._jobs_cache is not None:
            return self._jobs_cache
            
        jobs = []
        for json_file in self.jobs_dir.glob("*_extracted.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    if "error" not in job_data:
                        jobs.append(job_data)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        self._jobs_cache = jobs
        return jobs
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get a job by ID."""
        jobs = self._load_jobs()
        for job in jobs:
            if job.get("job_id") == job_id:
                return job
        return None
    
    def get_all_jobs(self, limit: Optional[int] = None) -> list[dict]:
        """Get all jobs."""
        jobs = self._load_jobs()
        if limit:
            return jobs[:limit]
        return jobs
    
    def search_jobs_by_skills(self, skills: list[str], limit: int = 50) -> list[dict]:
        """Search jobs that match any of the given skills."""
        jobs = self._load_jobs()
        matched = []
        skills_lower = [s.lower() for s in skills]
        
        for job in jobs:
            job_skills = job.get("skills", [])
            if isinstance(job_skills, list):
                job_skills_lower = [s.lower() for s in job_skills]
                # Check if any skills match
                if any(skill in " ".join(job_skills_lower) for skill in skills_lower):
                    matched.append(job)
                    if len(matched) >= limit:
                        break
        
        return matched


class JobDatabase:
    """MongoDB interface for job data."""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017", db_name: str = "smart_hr"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.jobs = self.db.jobs
        
    def insert_job(self, job_data: dict) -> str:
        """Insert or update a job."""
        job_id = job_data.get("job_id")
        if job_id:
            self.jobs.update_one({"job_id": job_id}, {"$set": job_data}, upsert=True)
            return job_id
        else:
            result = self.jobs.insert_one(job_data)
            return str(result.inserted_id)
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get a job by ID."""
        return self.jobs.find_one({"job_id": job_id})
    
    def get_all_jobs(self, limit: Optional[int] = None) -> list[dict]:
        """Get all jobs."""
        cursor = self.jobs.find({})
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    
    def search_jobs_by_skills(self, skills: list[str], limit: int = 50) -> list[dict]:
        """Search jobs that match any of the given skills."""
        # Case-insensitive regex search for skills
        skill_patterns = [{"skills": {"$regex": skill, "$options": "i"}} for skill in skills]
        query = {"$or": skill_patterns} if skill_patterns else {}
        return list(self.jobs.find(query).limit(limit))
    
    def import_from_directory(self, directory: str) -> int:
        """Import all extracted job JSON files into MongoDB."""
        imported = 0
        path = Path(directory)
        for json_file in path.glob("*_extracted.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    if "error" not in job_data:  # Skip failed extractions
                        self.insert_job(job_data)
                        imported += 1
            except Exception as e:
                print(f"Error importing {json_file}: {e}")
        return imported


class CVParser:
    """Parse CVs using Gemini Pro for better understanding."""
    
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-001",  # Using flash model
        project_id: str = "ai-deniers-486907",
        location: str = "us-central1",
    ):
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel(
            model_name=model_name,
            generation_config=GenerationConfig(
                temperature=0.2,  # Lower temperature for more consistent extraction
                max_output_tokens=8192,  # Increased to prevent truncation
            )
        )
    
    def _clean_json_response(self, text: str) -> str:
        """Clean and fix common JSON issues in LLM responses."""
        # Remove markdown code blocks
        if "```" in text:
            lines = text.split("\n")
            cleaned_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block or (in_code_block and not line.strip().startswith("```")):
                    cleaned_lines.append(line)
            text = "\n".join(cleaned_lines)
        
        # Find the JSON object boundaries
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        
        # Fix common issues: unescaped newlines in strings
        # Replace literal newlines inside strings with \n
        import re
        # This pattern finds strings and escapes newlines within them
        def fix_string(match):
            s = match.group(0)
            # Replace actual newlines with escaped ones (but not already escaped)
            s = s.replace('\n', '\\n').replace('\r', '\\r')
            return s
        
        return text
    
    def parse_cv(self, cv_text: str) -> CVProfile:
        """Parse a CV and extract structured information."""
        prompt = """You are an expert CV/Resume analyzer. Extract the following information from the CV below.
Output MUST be valid JSON only, no other text or markdown formatting.
All output MUST be in English, translate if needed.
IMPORTANT: Escape all special characters in strings properly. Do not include literal newlines in string values.

Extract these fields:
- name: Full name of the candidate
- email: Email address (null if not found)
- phone: Phone number (null if not found)
- location: Current location/city (null if not found)
- summary: A 2-3 sentence professional summary (single line, no newlines)
- years_of_experience: Estimated total years of professional experience (number or null)
- education: Array of education entries [{degree, field, institution, year}]
- skills: Array of technical/hard skills (programming languages, tools, frameworks, methodologies)
- soft_skills: Array of soft skills mentioned or implied
- languages: Array of spoken languages
- work_experience: Array of work experiences [{title, company, duration, responsibilities: []}] - keep responsibilities concise
- certifications: Array of certifications or courses
- desired_role: What type of role they seem to be looking for (infer from experience)
- desired_salary: Salary expectations if mentioned, otherwise null

Be thorough in extracting skills - look for technologies, tools, and methodologies mentioned throughout the CV.

Output format:
{
    "name": "string",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null",
    "summary": "string",
    "years_of_experience": number or null,
    "education": [{"degree": "string", "field": "string", "institution": "string", "year": "string or null"}],
    "skills": ["string"],
    "soft_skills": ["string"],
    "languages": ["string"],
    "work_experience": [{"title": "string", "company": "string", "duration": "string", "responsibilities": ["string"]}],
    "certifications": ["string"],
    "desired_role": "string or null",
    "desired_salary": {"min": number, "max": number, "currency": "string"} or null
}

CV Text:
"""
        full_prompt = f"{prompt}\n\n{cv_text}"
        response = self.model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        # Clean up response
        response_text = self._clean_json_response(response_text)
        
        try:
            data = json.loads(response_text)
            return CVProfile(**data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing CV response: {e}")
            print(f"Raw response: {response_text[:1000]}...")
            
            # Try a more aggressive fix - use ast.literal_eval as fallback after fixing
            try:
                # Try to fix truncated JSON by adding missing brackets
                if response_text.count('{') > response_text.count('}'):
                    response_text += '}' * (response_text.count('{') - response_text.count('}'))
                if response_text.count('[') > response_text.count(']'):
                    response_text += ']' * (response_text.count('[') - response_text.count(']'))
                data = json.loads(response_text)
                return CVProfile(**data)
            except:
                pass
            
            raise ValueError(f"Failed to parse CV: {e}")


class JobMatcher:
    """Match CVs to jobs using Gemini."""
    
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-001",  # Fast model for matching
        project_id: str = "ai-deniers-486907",
        location: str = "us-central1",
    ):
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel(
            model_name=model_name,
            generation_config=GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
            )
        )
    
    def match_cv_to_jobs(
        self,
        cv_profile: CVProfile,
        jobs: list[dict],
        applied_job_id: Optional[str] = None,
        top_n: int = 10
    ) -> list[JobMatch]:
        """Match a CV profile against multiple jobs and return top N matches."""
        
        prompt = f"""You are an expert HR recruiter. Analyze how well this candidate matches each job posting.

CANDIDATE PROFILE:
- Name: {cv_profile.name}
- Summary: {cv_profile.summary}
- Years of Experience: {cv_profile.years_of_experience or 'Unknown'}
- Location: {cv_profile.location or 'Unknown'}
- Technical Skills: {', '.join(cv_profile.skills)}
- Soft Skills: {', '.join(cv_profile.soft_skills)}
- Languages: {', '.join(cv_profile.languages)}
- Education: {json.dumps(cv_profile.education)}
- Work Experience: {json.dumps(cv_profile.work_experience)}
- Certifications: {', '.join(cv_profile.certifications)}

{"IMPORTANT: The candidate has APPLIED for job ID: " + applied_job_id + ". Make sure to include this job in the results and flag it." if applied_job_id else ""}

For each job, calculate:
1. match_score (0-100): Overall match considering skills, experience, and fit
2. skill_match (0-100): How well technical skills align
3. experience_match (0-100): How well experience level matches
4. matching_skills: List of candidate skills that match the job
5. missing_skills: Important skills the candidate lacks for this job
6. reasoning: Brief explanation of the match (2-3 sentences)

Output MUST be valid JSON only - an array of job matches sorted by match_score descending.
Return the top {top_n} matches.

Output format:
[
    {{
        "job_id": "string",
        "job_title": "string",
        "location": {{"city": "string", "country": "string", "work_model": "string"}},
        "match_score": number,
        "skill_match": number,
        "experience_match": number,
        "matching_skills": ["string"],
        "missing_skills": ["string"],
        "reasoning": "string",
        "is_applied_job": boolean
    }}
]

JOB POSTINGS:
"""
        # Add job data
        jobs_text = "\n\n---\n\n".join([
            f"Job ID: {job.get('job_id')}\n"
            f"Title: {job.get('job_title')}\n"
            f"Location: {json.dumps(job.get('location', {}))}\n"
            f"Description: {job.get('description', 'N/A')}\n"
            f"Required Skills: {', '.join(job.get('skills', []))}\n"
            f"Soft Skills: {', '.join(job.get('soft_skills', []))}\n"
            f"Tasks: {', '.join(job.get('tasks', []))}"
            for job in jobs
        ])
        
        full_prompt = f"{prompt}\n\n{jobs_text}"
        response = self.model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        # Clean up response
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            response_text = "\n".join(lines)
        
        try:
            matches_data = json.loads(response_text)
            return [JobMatch(**match) for match in matches_data]
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing matches: {e}")
            print(f"Raw response: {response_text[:500]}...")
            return []


class CVJobMatchingPipeline:
    """Complete pipeline for CV to job matching."""
    
    def __init__(
        self,
        mongo_connection: str = "mongodb://localhost:27017",
        db_name: str = "smart_hr",
        cv_parser_model: str = "gemini-2.5-pro",
        matcher_model: str = "gemini-2.0-flash-001",
        use_files: bool = False,
        jobs_directory: str = "jobs_extracted",
    ):
        if use_files:
            self.db = FileJobStore(jobs_directory)
        else:
            self.db = JobDatabase(mongo_connection, db_name)
        self.cv_parser = CVParser(model_name=cv_parser_model)
        self.matcher = JobMatcher(model_name=matcher_model)
    
    def import_jobs(self, jobs_directory: str) -> int:
        """Import extracted jobs into MongoDB."""
        return self.db.import_from_directory(jobs_directory)
    
    def process_application(
        self,
        cv_text: str,
        applied_job_id: str,
        top_n: int = 10,
        search_limit: int = 100
    ) -> dict:
        """
        Process a job application.
        
        Args:
            cv_text: The CV/resume text
            applied_job_id: The ID of the job the candidate applied to
            top_n: Number of top matching jobs to return
            search_limit: Max jobs to consider for matching
        
        Returns:
            Dictionary with CV profile, applied job match, and alternative jobs
        """
        # Step 1: Parse the CV
        print("Parsing CV...")
        cv_profile = self.cv_parser.parse_cv(cv_text)
        print(f"Extracted profile for: {cv_profile.name}")
        print(f"Skills found: {len(cv_profile.skills)}")
        
        # Step 2: Get the applied job
        applied_job = self.db.get_job(applied_job_id)
        if not applied_job:
            raise ValueError(f"Applied job not found: {applied_job_id}")
        
        # Step 3: Find candidate jobs based on skills
        print("Searching for matching jobs...")
        candidate_jobs = self.db.search_jobs_by_skills(cv_profile.skills, limit=search_limit)
        
        # Make sure applied job is included
        if applied_job not in candidate_jobs:
            candidate_jobs.insert(0, applied_job)
        
        print(f"Found {len(candidate_jobs)} candidate jobs")
        
        # Step 4: Match CV to jobs
        print("Matching CV to jobs...")
        matches = self.matcher.match_cv_to_jobs(
            cv_profile=cv_profile,
            jobs=candidate_jobs,
            applied_job_id=applied_job_id,
            top_n=top_n
        )
        
        # Separate applied job from alternatives
        applied_match = next((m for m in matches if m.is_applied_job), None)
        alternative_matches = [m for m in matches if not m.is_applied_job]
        
        return {
            "cv_profile": asdict(cv_profile),
            "applied_job": {
                "job_id": applied_job_id,
                "job_title": applied_job.get("job_title"),
                "match": asdict(applied_match) if applied_match else None
            },
            "alternative_jobs": [asdict(m) for m in alternative_matches],
            "total_jobs_analyzed": len(candidate_jobs)
        }


def main():
    """CLI for the CV matching pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CV to Job Matching Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Import jobs command
    import_parser = subparsers.add_parser("import", help="Import jobs into MongoDB")
    import_parser.add_argument(
        "-i", "--input",
        default=str(Path(__file__).parent / "jobs_extracted"),
        help="Directory containing extracted job JSON files"
    )
    import_parser.add_argument(
        "--mongo",
        default="mongodb://localhost:27017",
        help="MongoDB connection string"
    )
    
    # Match CV command
    match_parser = subparsers.add_parser("match", help="Match a CV to jobs")
    match_parser.add_argument(
        "-c", "--cv",
        required=True,
        help="Path to CV file (text or PDF)"
    )
    match_parser.add_argument(
        "-j", "--job",
        required=True,
        help="Applied job ID"
    )
    match_parser.add_argument(
        "-n", "--top-n",
        type=int,
        default=10,
        help="Number of top matches to return"
    )
    match_parser.add_argument(
        "-o", "--output",
        help="Output file for results (JSON)"
    )
    match_parser.add_argument(
        "--mongo",
        default="mongodb://localhost:27017",
        help="MongoDB connection string"
    )
    match_parser.add_argument(
        "--files",
        action="store_true",
        help="Use file-based job store instead of MongoDB"
    )
    match_parser.add_argument(
        "-i", "--jobs-dir",
        default="jobs_extracted",
        help="Directory with extracted jobs (when using --files)"
    )
    
    args = parser.parse_args()
    
    if args.command == "import":
        print("=" * 60)
        print("Importing Jobs to MongoDB")
        print("=" * 60)
        
        db = JobDatabase(args.mongo)
        imported = db.import_from_directory(args.input)
        print(f"Imported {imported} jobs")
        
    elif args.command == "match":
        print("=" * 60)
        print("CV to Job Matching")
        print("=" * 60)
        
        # Read CV file
        cv_path = Path(args.cv)
        if not cv_path.exists():
            print(f"CV file not found: {cv_path}")
            return
        
        # Handle PDF and text files
        if cv_path.suffix.lower() == ".pdf":
            print(f"Extracting text from PDF: {cv_path}")
            cv_text = extract_text_from_pdf(str(cv_path))
        else:
            with open(cv_path, "r", encoding="utf-8") as f:
                cv_text = f.read()
        
        # Initialize pipeline
        pipeline = CVJobMatchingPipeline(
            mongo_connection=args.mongo,
            use_files=args.files,
            jobs_directory=args.jobs_dir
        )
        
        # Process application
        result = pipeline.process_application(
            cv_text=cv_text,
            applied_job_id=args.job,
            top_n=args.top_n
        )
        
        # Output results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        print(f"\nCandidate: {result['cv_profile']['name']}")
        print(f"Skills: {', '.join(result['cv_profile']['skills'][:10])}...")
        
        print(f"\n--- Applied Job ---")
        if result['applied_job']['match']:
            match = result['applied_job']['match']
            print(f"Job: {match['job_title']}")
            print(f"Match Score: {match['match_score']}/100")
            print(f"Skill Match: {match['skill_match']}/100")
            print(f"Reasoning: {match['reasoning']}")
        
        print(f"\n--- Top {args.top_n} Alternative Jobs ---")
        for i, match in enumerate(result['alternative_jobs'][:args.top_n], 1):
            print(f"\n{i}. {match['job_title']} (Score: {match['match_score']}/100)")
            print(f"   Location: {match['location'].get('city')}, {match['location'].get('country')}")
            print(f"   Reasoning: {match['reasoning']}")
        
        # Save to file if requested
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {args.output}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
