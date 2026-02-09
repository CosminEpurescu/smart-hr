# 🦁 ING Smart HR - AI-Powered Talent Matching

An AI-powered CV-to-job matching platform built for ING recruitment. Features intelligent skill matching, multi-factor scoring, and AI-generated interview preparation.

## 🌟 Features

### CV Job Matcher
- 🎯 **AI-Powered Matching** - Uses Google Gemini AI to understand CVs and jobs deeply
- 📊 **Multi-Factor Scoring** - Skills (35%), Experience (25%), Location (15%), Language (15%), Salary (10%)
- 🔄 **Alternative Job Suggestions** - Finds better-fitting roles the candidate might have missed
- 📄 **PDF & TXT Support** - Drag-and-drop CV upload with automatic text extraction

### Interview Preparation
- 🎤 **AI-Generated Questions** - Technical, behavioral, skill-gap, and career-fit questions
- ✅ **Suggested Answers** - Ideal responses based on the candidate's profile
- 💰 **Salary Negotiation Tips** - Talking points and market context
- 🚩 **Green/Red Flags** - What to look for in candidate responses

### Analytics Dashboard
- 📈 **Score Distribution** - Track match quality across all searches
- 🛠️ **Skill Frequency** - See most common skills in candidate pool
- 📋 **Recent Searches** - History of CV analyses

---

## 🚀 Quick Start (For Humans)

### Prerequisites
- Python 3.11+ (or use `uv` package manager)
- Google Cloud credentials with Vertex AI access

### Step 1: Install Dependencies

```bash
cd job-parser
uv sync  # or: pip install -r requirements.txt
```

### Step 2: Set Up Google Cloud Credentials

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
```

### Step 3: Start the Web App

```bash
cd job-parser
uv run python web_app.py
# or: python web_app.py
```

Open **http://localhost:5001** in your browser.

### Step 4: Use the App
1. **Upload a CV** (PDF or TXT) using drag-and-drop
2. **Select a job** from the dropdown
3. **(Optional)** Enter salary budget range
4. Click **"🦁 Analyze Match"**
5. Go to **"🎤 Interview Prep"** tab → Click **"Generate Interview Questions"**

---

## 🤖 Quick Start (For AI Agents)

### Environment Setup

```bash
# Navigate to the project
cd /Users/your-user/Documents/projects/hackathon/day1/smart-hr/job-parser

# Set credentials (REQUIRED)
export GOOGLE_APPLICATION_CREDENTIALS=/Users/your-user/Downloads/ai-deniers-486907-d7a6d05195f3.json

# Install dependencies
uv sync

# Start the web server (background)
uv run python web_app.py &
# Server runs on http://localhost:5001
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/api/jobs` | GET | List all available jobs |
| `/api/match` | POST | Match a CV to jobs |
| `/api/interview-questions` | POST | Generate interview questions |
| `/api/analytics` | GET | Get analytics data |

### API Usage Examples

```bash
# Get all jobs
curl http://localhost:5001/api/jobs

# Match a CV (form-data)
curl -X POST http://localhost:5001/api/match \
  -F "cv_file=@/path/to/cv.pdf" \
  -F "job_id=20976441152" \
  -F "top_n=5" \
  -F "salary_min=50000" \
  -F "salary_max=80000"

# Generate interview questions (JSON)
curl -X POST http://localhost:5001/api/interview-questions \
  -H "Content-Type: application/json" \
  -d '{"cv_profile": {...}, "applied_job": {...}, "alternative_jobs": [...]}'
```

### Programmatic Usage (Python)

```python
from cv_matcher import CVJobMatchingPipeline, FileJobStore

# Initialize pipeline
pipeline = CVJobMatchingPipeline(
    use_files=True,
    jobs_directory="jobs_extracted"
)

# Process a CV
result = pipeline.process_application(
    cv_text="John Doe\nSoftware Engineer\nSkills: Python, Java...",
    applied_job_id="20976441152",
    top_n=5
)

print(f"Candidate: {result['cv_profile']['name']}")
print(f"Applied Job Score: {result['applied_job']['match']['match_score']}")
```

### Key Files

| File | Purpose |
|------|---------|
| `web_app.py` | Flask web server (port 5001) |
| `cv_matcher.py` | Core CV parsing and matching logic |
| `jobs_extracted/` | Pre-processed job data (790 jobs) |
| `jobs_detailed/` | Original job data with URLs |
| `templates/index.html` | Web UI template |

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to GCP credentials JSON |
| Port | 5001 | Flask server port |
| Model | `gemini-2.0-flash-001` | Vertex AI model for matching |
| Project | `ai-deniers-486907` | GCP Project ID |
| Location | `us-central1` | Vertex AI region |

---

## 📋 Job Parser (Original Functionality)

A Python tool to scrape and parse job listings from the [ING Careers website](https://careers.ing.com/en/search-jobs).

### Job Parser Features

- 📋 Parse all job listings from ING Careers
- 🔍 Search and filter jobs by country, city, expertise, or keyword
- 📄 Fetch full job details including description, requirements, and benefits
- 💾 Export to JSON, CSV, or Excel formats
- 📊 Convert to pandas DataFrame for analysis
- ⏱️ Built-in rate limiting to be respectful to the server

### Command Line Usage

```bash
# Get all job listings (basic info)
python main.py --output jobs.json

# Get jobs with full details (slower, fetches each job page)
python main.py --output jobs.json --details

# Limit to first 5 pages
python main.py --output jobs.json --max-pages 5

# Export to CSV
python main.py --output jobs.csv

# Export to Excel
python main.py --output jobs.xlsx

# Search for specific jobs
python main.py --output developers.json --keyword "developer"

# Filter by country
python main.py --output poland_jobs.json --country Poland

# Combine filters
python main.py --output warsaw_tech.json --city Warsaw --keyword "engineer"
```

### Python API Usage

```python
from ing_job_parser import INGJobParser
from ing_job_parser.exporter import JobExporter

# Initialize parser
parser = INGJobParser(delay=1.0)  # 1 second delay between requests

# Get total number of jobs
total = parser.get_total_jobs()
print(f"Total jobs: {total}")

# Get all job listings (basic info)
jobs = parser.get_all_job_listings(max_pages=5)

# Get jobs with full details
detailed_jobs = parser.get_all_jobs_with_details(max_pages=3, max_jobs=10)

# Search for specific jobs
python_jobs = parser.search_jobs(keyword="Python", country="Netherlands")

# Export to various formats
JobExporter.to_json(jobs, "jobs.json")
JobExporter.to_csv(jobs, "jobs.csv")
JobExporter.to_excel(jobs, "jobs.xlsx")

# Convert to pandas DataFrame
df = JobExporter.to_dataframe(jobs)
print(df.head())
```

## Job Data Structure

Each job includes the following fields:

| Field | Description |
|-------|-------------|
| `job_id` | Unique job identifier |
| `title` | Job title |
| `url` | Full URL to job posting |
| `city` | City location |
| `country` | Country |
| `locations` | List of all locations |
| `expertise` | Job category/expertise area |
| `experience_level` | Professional, Starter/Graduate, Student |
| `ing_entity` | ING Bank or ING Hubs |
| `job_type` | Full time / Part time |
| `posted_date` | Date posted |
| `description` | Full job description (with --details) |
| `requirements` | Job requirements (with --details) |
| `benefits` | Benefits offered (with --details) |
| `apply_url` | Direct application URL |
| `contact_email` | Recruiter contact email |
| `scraped_at` | Timestamp when scraped |

## Command Line Options

| Option | Description |
|--------|-------------|
| `--output, -o` | Output file path (default: jobs.json) |
| `--format, -f` | Output format: json, csv, excel (auto-detected from extension) |
| `--details, -d` | Fetch full details for each job |
| `--max-pages` | Maximum number of pages to scrape |
| `--max-jobs` | Maximum number of jobs to process |
| `--delay` | Delay between requests in seconds (default: 1.0) |
| `--keyword, -k` | Search keyword to filter jobs |
| `--country` | Filter by country |
| `--city` | Filter by city |
| `--quiet, -q` | Suppress progress output |

## Examples

See [example.py](example.py) for more detailed usage examples.

```bash
python example.py
```

## Rate Limiting

The parser includes a configurable delay between requests (default: 1 second) to be respectful to ING's servers. You can adjust this:

```python
# Faster (be careful!)
parser = INGJobParser(delay=0.5)

# Slower (more conservative)
parser = INGJobParser(delay=2.0)
```

## Project Structure

```
job-parser/
├── ing_job_parser/
│   ├── __init__.py
│   ├── models.py      # Job data model
│   ├── parser.py      # Main parser logic
│   └── exporter.py    # Export utilities
├── main.py            # CLI entry point
├── example.py         # Usage examples
├── requirements.txt   # Dependencies
└── README.md
```

## Dependencies

- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `lxml` - Fast HTML parser
- `pandas` - Data manipulation and export
- `tqdm` - Progress bars
## Running the Project

### Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Basic job scraping (sequential) - gets all job listings
python main.py --output jobs.json

# 3. With full details (sequential, slower)
python main.py --output jobs.json --details

# 4. Limit pages for testing
python main.py --output jobs.json --max-pages 5
```

### Parallel Processing (Recommended for Large-Scale Scraping)

The `parse_job_details.py` script provides **parallel scraping** using ThreadPoolExecutor:

```bash
# Step 1: Get basic job listings first
python main.py --output jobs.json

# Step 2: Parse details in parallel (10 workers by default)
python parse_job_details.py --input jobs.json --output-dir jobs_detailed

# Step 3: Customize parallelism
python parse_job_details.py --input jobs.json --output-dir jobs_detailed --workers 20

# Resume interrupted processing (skip already processed jobs)
python parse_job_details.py --input jobs.json --output-dir jobs_detailed --resume

# Limit number of jobs to process
python parse_job_details.py --input jobs.json --output-dir jobs_detailed --limit 100
```

### Parallel Processing Options

| Option | Description |
|--------|-------------|
| `--input, -i` | Input JSON file with job listings (default: jobs.json) |
| `--output-dir, -o` | Output directory for individual job files (default: jobs_detailed) |
| `--workers, -w` | Number of parallel workers (default: 10) |
| `--limit` | Limit number of jobs to process |
| `--resume` | Skip already processed jobs |
| `--delay` | Delay between requests (ignored in parallel mode) |

### Common Workflows

```bash
# Full workflow: scrape all jobs with parallel detail fetching
python main.py --output jobs.json && python parse_job_details.py -i jobs.json -o jobs_detailed -w 10

# Filter jobs first, then get details
python main.py --output poland_jobs.json --country Poland
python parse_job_details.py -i poland_jobs.json -o poland_detailed -w 5

# Export to different formats
python main.py --output jobs.csv   # CSV format
python main.py --output jobs.xlsx  # Excel format
```
## License

MIT License

---

## 📁 Full Project Structure

```
job-parser/
├── web_app.py              # 🌐 Flask web server (main entry point)
├── cv_matcher.py           # 🧠 CV parsing & job matching logic
├── main.py                 # CLI for job scraping
├── parse_job_details.py    # Parallel job detail fetcher
├── pyproject.toml          # Project dependencies (uv)
├── requirements.txt        # Dependencies (pip)
├── templates/
│   └── index.html          # Web UI (ING-branded)
├── jobs_extracted/         # 790 processed job files
│   └── *_extracted.json
├── jobs_detailed/          # Original job data with URLs
│   └── *.json
└── ing_job_parser/         # Job scraping library
    ├── __init__.py
    ├── models.py
    ├── parser.py
    └── exporter.py
```

---

## 🔧 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `GOOGLE_APPLICATION_CREDENTIALS not set` | Export the env variable with path to your credentials JSON |
| `ModuleNotFoundError` | Run `uv sync` or `pip install -r requirements.txt` |
| Port 5001 already in use | Kill existing process: `pkill -f "python.*web_app"` |
| CV text extraction fails | Ensure PDF is text-based, not scanned |

### For AI Agents

```bash
# Full restart command (kill + start)
pkill -f "python.*web_app" 2>/dev/null; \
cd /Users/your-user/Documents/projects/hackathon/day1/smart-hr/job-parser && \
export GOOGLE_APPLICATION_CREDENTIALS=/Users/your-user/Downloads/ai-deniers-486907-d7a6d05195f3.json && \
.venv/bin/python web_app.py
```

---

## 🏆 Hackathon MVP

**Built in 24 hours** for the ING AI Hackathon 2026.

**Team:** AI Deniers

**Tech Stack:**
- 🐍 Python 3.14 + Flask
- 🤖 Google Vertex AI (Gemini 2.0 Flash)
- 🎨 ING Netherlands Branding
- 📊 Chart.js for Analytics


---

*🦁 ING Smart HR — Where talent meets opportunity, intelligently.*
