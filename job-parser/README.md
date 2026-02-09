# ING Careers Job Parser

A Python tool to scrape and parse job listings from the [ING Careers website](https://careers.ing.com/en/search-jobs).

## Features

- 📋 Parse all job listings from ING Careers
- 🔍 Search and filter jobs by country, city, expertise, or keyword
- 📄 Fetch full job details including description, requirements, and benefits
- 💾 Export to JSON, CSV, or Excel formats
- 📊 Convert to pandas DataFrame for analysis
- ⏱️ Built-in rate limiting to be respectful to the server

## Installation

1. Clone or download this project
2. Install dependencies:

```bash
cd job-parser
pip install -r requirements.txt
```

## Quick Start

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

# Parse first 5 pages of listings (each page has ~20 jobs)
python main.py --output jobs.json --max-pages 5

# Parse ALL listings (no page limit)
python main.py --output jobs.json --max-pages 0

# Fetch details for all jobs with 10 parallel workers
python parse_job_details.py -i jobs.json -o jobs_detailed -w 10

# Fetch details with 20 parallel workers (faster)
python parse_job_details.py -i jobs.json -o jobs_detailed -w 20

# Full workflow: scrape all listings + fetch all details
python main.py --output jobs.json --max-pages 0 && python parse_job_details.py -i jobs.json -o jobs_detailed -w 15

# Limit to specific number of jobs for testing
python main.py --output jobs.json --max-pages 2  # ~40 jobs
python parse_job_details.py -i jobs.json -o jobs_detailed -w 10
