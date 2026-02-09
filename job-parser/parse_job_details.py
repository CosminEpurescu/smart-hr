#!/usr/bin/env python3
"""
Detailed Job Parser - Fetches full details from each job page and saves to individual files.
Supports parallel processing for faster scraping.
"""

import json
import re
import time
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DetailedJob:
    """Complete job details from a job posting page."""
    
    # Basic identifiers
    job_id: str
    title: str
    url: str
    
    # Reference/posting info
    reference_number: Optional[str] = None
    posted_date: Optional[str] = None
    
    # Classification
    expertise: Optional[str] = None
    experience_level: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Part-time
    ing_entity: Optional[str] = None  # ING Bank, ING Hubs
    
    # Location
    location_primary: Optional[str] = None  # City, Country
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    location_details: Optional[str] = None  # Additional location info
    location_address: Optional[str] = None  # Street address if available
    
    # Compensation
    salary_range: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None  # monthly, yearly
    
    # Employment details
    employment_type: Optional[str] = None  # Contract type
    work_model: Optional[str] = None  # Hybrid, Remote, Office
    
    # Content sections
    about_position: Optional[str] = None
    about_team: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    nice_to_have: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    about_company: Optional[str] = None
    
    # Full raw content (for reference)
    full_description: Optional[str] = None
    
    # Application info
    apply_url: Optional[str] = None
    
    # Contact info
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Metadata
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    language: Optional[str] = None  # Detected language (en, pl, nl, etc.)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class DetailedJobParser:
    """Parser for extracting full details from ING job pages."""
    
    BASE_URL = "https://careers.ing.com"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Section header patterns (multilingual)
    SECTION_PATTERNS = {
        "about_position": [
            r"o stanowisku", r"about the position", r"about this role", r"the role",
            r"position overview", r"job description", r"over de functie"
        ],
        "about_team": [
            r"o zespole", r"about the team", r"the team", r"your team", r"our team",
            r"over het team"
        ],
        "responsibilities": [
            r"twoje zadania", r"your tasks", r"responsibilities", r"what you.?ll do",
            r"roles and responsibilities", r"key responsibilities", r"your responsibilities",
            r"wat ga je doen", r"taken"
        ],
        "requirements": [
            r"nasze oczekiwania", r"requirements", r"qualifications", r"what we.?re looking for",
            r"how to succeed", r"your profile", r"wat vragen wij", r"profiel"
        ],
        "nice_to_have": [
            r"mile widziane", r"nice to have", r"preferred", r"bonus points",
            r"what.?s nice to have", r"mooi meegenomen"
        ],
        "benefits": [
            r"to oferujemy", r"what we offer", r"benefits", r"rewards and benefits",
            r"our offer", r"wat bieden wij", r"arbeidsvoorwaarden"
        ],
        "about_company": [
            r"o nas", r"about us", r"about ing", r"over ing", r"over ons"
        ],
    }
    
    def __init__(self, delay: float = 0.5, timeout: int = 30):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._lock = threading.Lock()
    
    def _get_session(self) -> requests.Session:
        """Get a thread-local session for parallel requests."""
        # Create a new session per thread for thread safety
        local = threading.local()
        if not hasattr(local, 'session'):
            local.session = requests.Session()
            local.session.headers.update(self.HEADERS)
        return local.session
    
    def _make_request(self, url: str, use_shared_session: bool = True) -> Optional[BeautifulSoup]:
        """Make HTTP request and return parsed HTML."""
        try:
            # Use new session for each request in parallel mode
            session = requests.Session()
            session.headers.update(self.HEADERS)
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def _extract_text_list(self, element: Tag) -> List[str]:
        """Extract list items from an element."""
        items = []
        
        # Try to find list items
        list_items = element.find_all("li")
        if list_items:
            for li in list_items:
                text = li.get_text(strip=True)
                if text:
                    # Clean up bullet points
                    text = re.sub(r"^[•\-\*\d\.]+\s*", "", text)
                    items.append(text)
        else:
            # Try to split by bullet points or newlines
            text = element.get_text(separator="\n", strip=True)
            for line in text.split("\n"):
                line = line.strip()
                line = re.sub(r"^[•\-\*\d\.]+\s*", "", line)
                if line and len(line) > 3:
                    items.append(line)
        
        return items
    
    def _find_section_content(self, soup: BeautifulSoup, section_name: str) -> Optional[Tag]:
        """Find content for a named section."""
        patterns = self.SECTION_PATTERNS.get(section_name, [])
        
        for pattern in patterns:
            # Look for headers matching the pattern
            for tag in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
                text = tag.get_text(strip=True).lower()
                if re.search(pattern, text, re.IGNORECASE):
                    # Get the next sibling or parent's next content
                    content = tag.find_next_sibling()
                    if content:
                        return content
                    
                    # Try parent
                    parent = tag.parent
                    if parent:
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            return next_elem
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """Detect language based on common words."""
        text_lower = text.lower()
        
        # Polish indicators
        polish_words = ["stanowisku", "zadania", "oczekiwania", "oferujemy", "umowa", "praca"]
        if any(word in text_lower for word in polish_words):
            return "pl"
        
        # Dutch indicators
        dutch_words = ["functie", "taken", "vragen", "bieden", "arbeidsvoorwaarden"]
        if any(word in text_lower for word in dutch_words):
            return "nl"
        
        # German indicators
        german_words = ["aufgaben", "anforderungen", "angebot", "arbeitsort"]
        if any(word in text_lower for word in german_words):
            return "de"
        
        return "en"
    
    def _extract_salary(self, text: str) -> Dict[str, Any]:
        """Extract salary information from text."""
        result = {
            "salary_range": None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
            "salary_period": None,
        }
        
        # Pattern for salary like €7.499,31 - €11.925,90
        salary_pattern = r"([€$£])\s*([\d.,]+)\s*[-–]\s*([€$£])?\s*([\d.,]+)"
        match = re.search(salary_pattern, text)
        
        if match:
            currency_symbol = match.group(1)
            min_val = match.group(2).replace(".", "").replace(",", ".")
            max_val = match.group(4).replace(".", "").replace(",", ".")
            
            result["salary_range"] = match.group(0)
            result["salary_currency"] = {"€": "EUR", "$": "USD", "£": "GBP"}.get(currency_symbol, currency_symbol)
            
            try:
                result["salary_min"] = float(min_val)
                result["salary_max"] = float(max_val)
                # Assume monthly if values are in thousands
                result["salary_period"] = "monthly" if result["salary_max"] < 50000 else "yearly"
            except ValueError:
                pass
        
        return result
    
    def _extract_job_id_from_url(self, url: str) -> str:
        """Extract job ID from URL."""
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else ""
    
    def parse_job_page(self, url: str, basic_info: Optional[Dict] = None) -> Optional[DetailedJob]:
        """
        Parse a job detail page and extract all available information.
        
        Args:
            url: Job page URL
            basic_info: Optional basic info from listing (job_id, title, etc.)
        """
        soup = self._make_request(url)
        if not soup:
            return None
        
        job_id = basic_info.get("job_id") if basic_info else self._extract_job_id_from_url(url)
        
        # Initialize job with basic info
        job = DetailedJob(
            job_id=job_id,
            title="",
            url=url,
        )
        
        # Copy basic info if provided
        if basic_info:
            job.job_id = basic_info.get("job_id", job_id)
        
        try:
            # Extract title from h1
            title_elem = soup.find("h1")
            if title_elem:
                job.title = title_elem.get_text(strip=True)
            
            # Get full page text for analysis
            page_text = soup.get_text(separator="\n", strip=True)
            
            # Detect language
            job.language = self._detect_language(page_text)
            
            # Extract metadata from the job info section
            # Look for patterns like "REQ-10102975", "04-02-2026", etc.
            
            # Reference number
            ref_patterns = [
                r"(REQ-\d+)",
                r"([A-Z]{2,}_\d+)",
                r"(\d{7,})"
            ]
            for pattern in ref_patterns:
                match = re.search(pattern, page_text)
                if match:
                    job.reference_number = match.group(1)
                    break
            
            # Posted date - look for date patterns
            date_patterns = [
                r"(\d{2}[-/]\d{2}[-/]\d{4})",
                r"(\d{2}/\d{2}/\d{4})",
            ]
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    job.posted_date = match.group(1)
                    break
            
            # Extract salary
            salary_info = self._extract_salary(page_text)
            job.salary_range = salary_info["salary_range"]
            job.salary_min = salary_info["salary_min"]
            job.salary_max = salary_info["salary_max"]
            job.salary_currency = salary_info["salary_currency"]
            job.salary_period = salary_info["salary_period"]
            
            # Extract location
            location_patterns = [
                r"(Warsaw|Amsterdam|Brussels|Berlin|Madrid|Paris|Milan|London|Singapore|Sydney|Budapest|Prague|Bucharest|Luxembourg|Dublin|Frankfurt|Barcelona|Rotterdam|Utrecht|Katowice|Krakow|Poznan|Wroclaw|Lodz|Manila|Makati|Cluj-Napoca|Eindhoven|Leuven|New York|Houston|Zurich),?\s*(Poland|Netherlands|Belgium|Germany|Spain|France|Italy|United Kingdom|UK|Singapore|Australia|Romania|Philippines|Hungary|Czechia|Luxembourg|Ireland|Hong Kong|Slovakia|South Korea|Switzerland|Taiwan|Turkiye|Turkey|United States)?",
            ]
            for pattern in location_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    job.location_city = match.group(1)
                    job.location_country = match.group(2) if match.group(2) else None
                    job.location_primary = f"{job.location_city}, {job.location_country}" if job.location_country else job.location_city
                    break
            
            # Look for additional location details
            location_detail_match = re.search(r"(Polska,\s*[^;]+;|[A-Z][a-z]+,\s*[A-Z][a-z]+;)", page_text)
            if location_detail_match:
                job.location_details = location_detail_match.group(1)
            
            # Address
            address_match = re.search(r"(ul\.\s+[^,\n]+|street\s+[^,\n]+)", page_text, re.IGNORECASE)
            if address_match:
                job.location_address = address_match.group(1)
            
            # Expertise/Category
            expertise_keywords = [
                "IT Engineering", "Tech", "HR", "Finance", "Risk Management", "Compliance",
                "Data Science", "Data Analysis", "Data Management", "Client & Business Services",
                "Customer Experience", "Audit", "Legal", "Sales", "Marketing", "Operations",
                "IT Architecture", "Security", "Business Management", "Communications",
                "Treasury", "Customer Journey"
            ]
            for kw in expertise_keywords:
                if kw.lower() in page_text.lower():
                    job.expertise = kw
                    break
            
            # ING Entity
            if "ING Hubs" in page_text:
                job.ing_entity = "ING Hubs"
            elif "ING Bank" in page_text:
                job.ing_entity = "ING Bank"
            
            # Employment type
            if "umowa o pracę" in page_text.lower():
                job.employment_type = "Employment contract"
            elif "employment contract" in page_text.lower():
                job.employment_type = "Employment contract"
            elif "b2b" in page_text.lower():
                job.employment_type = "B2B"
            elif "internship" in page_text.lower() and "not mandatory" not in page_text.lower():
                job.employment_type = "Internship"
            elif "staż" in page_text.lower():
                job.employment_type = "Internship"
            else:
                job.employment_type = "Full-time"  # Default
            
            # Work model
            if "hybrid" in page_text.lower() or "hybrydow" in page_text.lower():
                job.work_model = "Hybrid"
            elif "remote" in page_text.lower() or "zdaln" in page_text.lower():
                job.work_model = "Remote"
            elif "on-site" in page_text.lower() or "office" in page_text.lower():
                job.work_model = "On-site"
            
            # Extract main content sections using h3 headers (main structure)
            all_h3 = soup.find_all("h3")
            
            for h3 in all_h3:
                header_text = h3.get_text(strip=True).lower()
                
                # Collect content after this header until next h3 or h2
                content_parts = []
                next_elem = h3.find_next_sibling()
                
                while next_elem:
                    if next_elem.name in ["h2", "h3"]:
                        break
                    
                    if next_elem.name == "ul":
                        items = [li.get_text(strip=True) for li in next_elem.find_all("li")]
                        content_parts.extend(items)
                    elif next_elem.name in ["p", "div"]:
                        text = next_elem.get_text(strip=True)
                        if text and len(text) > 5:
                            content_parts.append(text)
                    
                    next_elem = next_elem.find_next_sibling()
                
                # Map to job fields based on header
                if any(p in header_text for p in ["o stanowisku", "about the position", "about this role", "the role"]):
                    job.about_position = "\n".join(content_parts)
                elif any(p in header_text for p in ["o zespole", "about the team", "the team"]):
                    job.about_team = "\n".join(content_parts)
                elif any(p in header_text for p in ["twoje zadania", "your tasks", "responsibilities", "roles and responsibilities"]):
                    job.responsibilities = content_parts
                elif any(p in header_text for p in ["nasze oczekiwania", "requirements", "how to succeed", "qualifications"]):
                    job.requirements = content_parts
                elif any(p in header_text for p in ["mile widziane", "nice to have", "preferred"]):
                    job.nice_to_have = content_parts
                elif any(p in header_text for p in ["to oferujemy", "what we offer", "rewards and benefits", "benefits"]):
                    job.benefits = content_parts
                elif any(p in header_text for p in ["o nas", "about us", "about ing"]):
                    job.about_company = "\n".join(content_parts)
            
            # If sections are empty, try to extract from main job description text
            main_content = soup.find("main") or soup.find("article") or soup.body
            if main_content:
                # Get the main description text (excluding headers, nav, footer)
                desc_text = []
                for p in main_content.find_all(["p", "li"]):
                    # Skip navigation and footer elements
                    if p.find_parent(["nav", "footer", "header"]):
                        continue
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        desc_text.append(text)
                
                job.full_description = "\n".join(desc_text[:50])  # First 50 paragraphs
            
            # Extract apply URL
            apply_link = soup.find("a", href=re.compile(r"apply|application", re.IGNORECASE))
            if apply_link:
                job.apply_url = apply_link.get("href")
            
            # Extract contact info
            contact_section = soup.find(string=re.compile(r"Questions\?|Contact|Ask", re.IGNORECASE))
            if contact_section:
                parent = contact_section.find_parent()
                if parent:
                    # Look for name
                    text = parent.get_text()
                    name_match = re.search(r"Just ask\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
                    if name_match:
                        job.contact_name = name_match.group(1)
                    
                    # Look for email
                    email_link = parent.find("a", href=re.compile(r"mailto:"))
                    if email_link:
                        href = email_link.get("href", "")
                        job.contact_email = href.replace("mailto:", "").split("?")[0]
            
            # If no contact found, search more broadly
            if not job.contact_email:
                email_links = soup.find_all("a", href=re.compile(r"mailto:"))
                for link in email_links:
                    href = link.get("href", "")
                    email = href.replace("mailto:", "").split("?")[0]
                    if "@ing" in email:
                        job.contact_email = email
                        break
            
        except Exception as e:
            logger.error(f"Error parsing job page {url}: {e}")
            return None
        
        return job


def load_jobs_from_json(filepath: str) -> List[Dict]:
    """Load job listings from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(name: str) -> str:
    """Create a safe filename from job title."""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = name[:100]  # Limit length
    return name


def main():
    """Main function to parse all jobs and save to individual files."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse detailed job information from ING Careers")
    parser.add_argument("--input", "-i", default="jobs.json", help="Input JSON file with job listings")
    parser.add_argument("--output-dir", "-o", default="jobs_detailed", help="Output directory for individual job files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds) - ignored in parallel mode")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of jobs to process")
    parser.add_argument("--resume", action="store_true", help="Skip already processed jobs")
    parser.add_argument("--workers", "-w", type=int, default=10, help="Number of parallel workers (default: 10)")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load jobs
    logger.info(f"Loading jobs from {args.input}")
    jobs = load_jobs_from_json(args.input)
    logger.info(f"Loaded {len(jobs)} jobs")
    
    if args.limit:
        jobs = jobs[:args.limit]
        logger.info(f"Limited to {len(jobs)} jobs")
    
    # Filter out already processed jobs if resume mode
    jobs_to_process = []
    skipped = 0
    for job_info in jobs:
        job_id = job_info.get("job_id", "unknown")
        title = job_info.get("title", "unknown")
        filename = f"{job_id}_{sanitize_filename(title)}.json"
        filepath = output_dir / filename
        
        if args.resume and filepath.exists():
            skipped += 1
        else:
            jobs_to_process.append((job_info, filepath))
    
    if skipped > 0:
        logger.info(f"Skipping {skipped} already processed jobs (resume mode)")
    
    logger.info(f"Processing {len(jobs_to_process)} jobs with {args.workers} parallel workers")
    
    # Initialize parser
    job_parser = DetailedJobParser(delay=args.delay)
    
    # Thread-safe counters
    successful = 0
    failed = 0
    lock = threading.Lock()
    
    def process_job(job_data: Tuple[Dict, Path]) -> bool:
        """Process a single job - thread worker function."""
        job_info, filepath = job_data
        url = job_info.get("url")
        job_id = job_info.get("job_id", "unknown")
        
        if not url:
            logger.warning(f"No URL for job {job_id}")
            return False
        
        try:
            # Parse the job page
            detailed_job = job_parser.parse_job_page(url, basic_info=job_info)
            
            if detailed_job:
                # Save to individual file
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(detailed_job.to_json())
                return True
            else:
                logger.warning(f"Failed to parse job: {url}")
                return False
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            return False
    
    # Process jobs in parallel with progress bar
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all jobs
        futures = {executor.submit(process_job, job_data): job_data for job_data in jobs_to_process}
        
        # Process results as they complete
        with tqdm(total=len(jobs_to_process), desc="Parsing job details") as pbar:
            for future in as_completed(futures):
                result = future.result()
                with lock:
                    if result:
                        successful += 1
                    else:
                        failed += 1
                pbar.update(1)
    
    # Summary
    logger.info(f"\nProcessing complete!")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Skipped: {skipped}")
    logger.info(f"  Output directory: {output_dir}")


if __name__ == "__main__":
    main()
