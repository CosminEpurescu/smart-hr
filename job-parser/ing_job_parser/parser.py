"""
Main parser module for ING Careers website.
"""

import re
import time
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from .models import Job

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class INGJobParser:
    """Parser for ING Careers job listings."""
    
    BASE_URL = "https://careers.ing.com"
    SEARCH_URL = f"{BASE_URL}/en/search-jobs"
    
    # Headers to mimic a browser
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    def __init__(self, delay: float = 0.3, timeout: int = 30):
        """
        Initialize the parser.
        
        Args:
            delay: Delay between requests in seconds (be respectful to the server)
            timeout: Request timeout in seconds
        """
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """
        Make an HTTP request and return parsed HTML.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if request failed
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def get_total_jobs(self) -> int:
        """
        Get the total number of jobs available.
        
        Returns:
            Total number of jobs
        """
        soup = self._make_request(self.SEARCH_URL)
        if not soup:
            return 0
        
        # Look for text like "We have 793 jobs for you"
        for h2 in soup.find_all("h2"):
            text = h2.get_text(strip=True)
            match = re.search(r"We have (\d+) jobs", text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _extract_job_id_from_url(self, url: str) -> str:
        """Extract job ID from URL."""
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-1]
        return url
    
    def get_job_listings(self, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Job]:
        """
        Get job listings from a specific page.
        
        Args:
            page: Page number (1-indexed)
            filters: Optional filters (not fully implemented yet)
            
        Returns:
            List of Job objects
        """
        url = f"{self.SEARCH_URL}?p={page}"
        
        soup = self._make_request(url)
        if not soup:
            return []
        
        return self._parse_jobs_from_soup(soup)
    
    def _parse_jobs_from_soup(self, soup: BeautifulSoup) -> List[Job]:
        """Parse jobs from a BeautifulSoup object."""
        jobs = []
        seen_ids = set()
        
        # Find all job links
        job_links = soup.find_all("a", href=re.compile(r"/en/job/[^/]+/[^/]+/\d+/\d+"))
        
        for link in job_links:
            href = link.get("href", "")
            if not href or "/en/job/" not in href:
                continue
            
            url = urljoin(self.BASE_URL, href)
            job_id = self._extract_job_id_from_url(url)
            
            # Skip duplicates
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            
            # Get title from the link
            title = link.get_text(strip=True)
            if not title or title in ["Show job", "View job", "Apply now", ""]:
                continue
            
            # Find the parent container for additional info
            parent = link.find_parent(["li", "div", "article", "section"])
            
            city = None
            country = None
            locations = []
            locations_raw = None
            expertise = None
            experience_level = None
            ing_entity = None
            
            if parent:
                text_content = parent.get_text(separator=" ", strip=True)
                
                # Extract multiple locations (format: "Polska, Katowice; Polska, Warszawa;")
                # Look for semicolon-separated location patterns
                locations_match = re.search(r'([A-Za-zżółćęśąźńŻÓŁĆĘŚĄŹŃ]+,\s*[A-Za-zżółćęśąźńŻÓŁĆĘŚĄŹŃ-]+;\s*)+', text_content)
                if locations_match:
                    locations_raw = locations_match.group(0).strip()
                    # Parse individual locations
                    for loc in locations_raw.split(';'):
                        loc = loc.strip()
                        if loc and ',' in loc:
                            locations.append(loc)
                
                # Also look for spans/elements that might contain location info
                location_spans = parent.find_all(['span', 'div'], class_=re.compile(r'location|place|city', re.I))
                for span in location_spans:
                    loc_text = span.get_text(strip=True)
                    if loc_text and loc_text not in locations:
                        if ';' in loc_text:
                            for loc in loc_text.split(';'):
                                loc = loc.strip()
                                if loc:
                                    locations.append(loc)
                        elif loc_text:
                            locations.append(loc_text)
                
                # Extract city
                city_patterns = [
                    "Warsaw", "Amsterdam", "Brussels", "Berlin", "Madrid", "Paris", 
                    "Milan", "London", "Singapore", "Sydney", "Budapest", "Prague", 
                    "Bucharest", "Luxembourg", "Dublin", "Frankfurt", "Barcelona", 
                    "Rotterdam", "Utrecht", "Katowice", "Krakow", "Poznan", "Wroclaw", 
                    "Lodz", "Manila", "Makati", "Cluj-Napoca", "Eindhoven", "Leuven",
                    "New York", "Houston", "Zurich", "Hong Kong", "Seoul", "Taipei",
                    "Warszawa", "Kraków", "Poznań", "Wrocław", "Łódź"
                ]
                for city_name in city_patterns:
                    if city_name.lower() in text_content.lower():
                        city = city_name
                        break
                
                # Extract country
                country_patterns = [
                    ("Poland", "Poland"), ("Polska", "Poland"), ("Netherlands", "Netherlands"), 
                    ("Belgium", "Belgium"), ("Germany", "Germany"),
                    ("Spain", "Spain"), ("France", "France"), ("Italy", "Italy"),
                    ("United Kingdom", "United Kingdom"), ("UK", "United Kingdom"),
                    ("Singapore", "Singapore"), ("Australia", "Australia"),
                    ("Romania", "Romania"), ("Philippines", "Philippines"),
                    ("Hungary", "Hungary"), ("Czechia", "Czechia"),
                    ("Luxembourg", "Luxembourg"), ("Ireland", "Ireland"),
                    ("Hong Kong", "Hong Kong SAR"), ("Slovakia", "Slovakia"),
                    ("South Korea", "South Korea"), ("Switzerland", "Switzerland"),
                    ("Taiwan", "Taiwan"), ("Turkiye", "Turkiye"), ("Turkey", "Turkiye"),
                    ("United States", "United States"), ("USA", "United States")
                ]
                for pattern, country_name in country_patterns:
                    if pattern.lower() in text_content.lower():
                        country = country_name
                        break
                
                # Extract expertise
                expertise_keywords = [
                    "Tech", "HR", "Finance", "Risk Management", "Compliance", 
                    "Data Science", "Data Analysis", "Data Management",
                    "Client & Business Services", "Customer Experience", 
                    "Audit", "Legal", "Sales", "Marketing", "Operations",
                    "IT Engineering", "IT Architecture", "Security",
                    "Business Management", "Communications", "Treasury"
                ]
                for kw in expertise_keywords:
                    if kw.lower() in text_content.lower():
                        expertise = kw
                        break
                
                # Extract experience level
                if "Professional" in text_content:
                    experience_level = "Professional"
                elif "Starter" in text_content or "Graduate" in text_content:
                    experience_level = "Starter / Graduate"
                elif "Student" in text_content:
                    experience_level = "Student"
                
                # Extract ING entity
                if "ING Hubs" in text_content:
                    ing_entity = "ING Hubs"
                elif "ING Bank" in text_content:
                    ing_entity = "ING Bank"
            
            jobs.append(Job(
                job_id=job_id,
                title=title,
                url=url,
                city=city,
                country=country,
                locations=locations,
                locations_raw=locations_raw,
                expertise=expertise,
                experience_level=experience_level,
                ing_entity=ing_entity,
            ))
        
        return jobs
    
    def get_all_job_listings(self, max_pages: Optional[int] = None, show_progress: bool = True) -> List[Job]:
        """
        Get all job listings from all pages.
        
        Args:
            max_pages: Maximum number of pages to scrape (None for all)
            show_progress: Show progress bar
            
        Returns:
            List of all Job objects
        """
        all_jobs = []
        seen_ids = set()
        
        # Get total count first
        total_jobs = self.get_total_jobs()
        logger.info(f"Total jobs available: {total_jobs}")
        
        if total_jobs == 0:
            # Try to scrape anyway - sometimes the count is not detected
            total_jobs = 1000
            logger.info("Could not detect job count, will scrape until no new jobs found")
        
        # Estimate pages (15 jobs per page based on testing)
        jobs_per_page = 15
        estimated_pages = (total_jobs // jobs_per_page) + 1
        
        if max_pages:
            estimated_pages = min(estimated_pages, max_pages)
        
        logger.info(f"Fetching up to {estimated_pages} pages...")
        
        # Create progress bar
        pages_range = range(1, estimated_pages + 1)
        if show_progress:
            pages_range = tqdm(pages_range, desc="Fetching job listings", unit="page")
        
        for page in pages_range:
            jobs = self.get_job_listings(page=page)
            if not jobs:
                logger.info(f"No more jobs found after page {page - 1}")
                break
            
            all_jobs.extend(jobs)
        
        # Remove duplicates based on job_id
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                unique_jobs.append(job)
        
        logger.info(f"Found {len(unique_jobs)} unique jobs")
        return unique_jobs
    
    def get_job_details(self, job: Job) -> Job:
        """
        Fetch full details for a job from its detail page.
        
        Args:
            job: Job object with URL
            
        Returns:
            Job object with full details
        """
        soup = self._make_request(job.url)
        if not soup:
            return job
        
        try:
            # Extract full job description
            content_sections = []
            
            # Look for main content area
            main_content = soup.select_one("main, .job-description, .job-details, article")
            if main_content:
                sections = main_content.find_all(["h2", "h3"])
                for section in sections:
                    section_title = section.get_text(strip=True)
                    section_content = []
                    
                    for sibling in section.find_next_siblings():
                        if sibling.name in ["h2", "h3"]:
                            break
                        text = sibling.get_text(strip=True)
                        if text:
                            section_content.append(text)
                    
                    if section_content:
                        content_sections.append(f"## {section_title}\n" + "\n".join(section_content))
                
                job.full_content = "\n\n".join(content_sections)
            
            # Extract specific sections
            desc_section = soup.find(["h2", "h3"], string=re.compile(r"about|description|stanowisku|position|tasks|responsibilities", re.IGNORECASE))
            if desc_section:
                desc_content = []
                for sibling in desc_section.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    desc_content.append(sibling.get_text(strip=True))
                job.description = "\n".join(desc_content)
            
            # Requirements
            req_section = soup.find(["h2", "h3"], string=re.compile(r"requirements|qualifications|oczekiwania|expect|profile", re.IGNORECASE))
            if req_section:
                req_content = []
                for sibling in req_section.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    req_content.append(sibling.get_text(strip=True))
                job.requirements = "\n".join(req_content)
            
            # Benefits
            benefits_section = soup.find(["h2", "h3"], string=re.compile(r"benefits|offer|oferujemy|we offer", re.IGNORECASE))
            if benefits_section:
                benefits_content = []
                for sibling in benefits_section.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    benefits_content.append(sibling.get_text(strip=True))
                job.benefits = "\n".join(benefits_content)
            
            # Apply URL
            apply_link = soup.find("a", href=re.compile(r"application|apply", re.IGNORECASE))
            if apply_link:
                job.apply_url = apply_link.get("href")
            
            # Contact email
            email_link = soup.find("a", href=re.compile(r"mailto:"))
            if email_link:
                href = email_link.get("href", "")
                if "mailto:" in href:
                    job.contact_email = href.replace("mailto:", "").split("?")[0]
            
            # Posted date
            date_text = soup.find(string=re.compile(r"\d{2}/\d{2}/\d{4}"))
            if date_text:
                job.posted_date = date_text.strip()
            
            # Update location info if missing
            if not job.city or not job.country:
                location_text = soup.get_text()
                if not job.city:
                    city_match = re.search(r"(Warsaw|Amsterdam|Brussels|Berlin|Madrid|Paris|Milan|London|Singapore|Sydney|Budapest|Prague|Bucharest|Luxembourg|Dublin|Frankfurt|Barcelona|Rotterdam|Utrecht|Katowice|Krakow|Poznan|Wroclaw|Lodz)", location_text, re.IGNORECASE)
                    if city_match:
                        job.city = city_match.group(1)
                
                if not job.country:
                    country_match = re.search(r"(Poland|Netherlands|Belgium|Germany|Spain|France|Italy|United Kingdom|Singapore|Australia|Romania)", location_text, re.IGNORECASE)
                    if country_match:
                        job.country = country_match.group(1)
            
        except Exception as e:
            logger.error(f"Failed to parse job details for {job.url}: {e}")
        
        return job
    
    def get_all_jobs_with_details(self, max_pages: Optional[int] = None, max_jobs: Optional[int] = None, show_progress: bool = True) -> List[Job]:
        """
        Get all jobs with full details.
        
        Args:
            max_pages: Maximum number of listing pages to scrape
            max_jobs: Maximum number of jobs to fetch details for
            show_progress: Show progress bar
            
        Returns:
            List of Job objects with full details
        """
        jobs = self.get_all_job_listings(max_pages=max_pages, show_progress=show_progress)
        
        if max_jobs:
            jobs = jobs[:max_jobs]
        
        logger.info(f"Fetching details for {len(jobs)} jobs...")
        
        if show_progress:
            jobs_iter = tqdm(jobs, desc="Fetching job details", unit="job")
        else:
            jobs_iter = jobs
        
        detailed_jobs = []
        for job in jobs_iter:
            detailed_job = self.get_job_details(job)
            detailed_jobs.append(detailed_job)
        
        return detailed_jobs
    
    def search_jobs(self, 
                   country: Optional[str] = None,
                   city: Optional[str] = None,
                   expertise: Optional[str] = None,
                   keyword: Optional[str] = None,
                   max_pages: Optional[int] = None) -> List[Job]:
        """
        Search for jobs with filters.
        
        Args:
            country: Filter by country
            city: Filter by city
            expertise: Filter by expertise area
            keyword: Search keyword
            max_pages: Maximum pages to fetch
            
        Returns:
            List of matching Job objects
        """
        # Get all jobs first
        all_jobs = self.get_all_job_listings(max_pages=max_pages, show_progress=True)
        
        # Filter locally
        filtered_jobs = all_jobs
        
        if keyword:
            keyword_lower = keyword.lower()
            filtered_jobs = [j for j in filtered_jobs if keyword_lower in j.title.lower()]
        
        if country:
            country_lower = country.lower()
            filtered_jobs = [j for j in filtered_jobs if j.country and country_lower in j.country.lower()]
        
        if city:
            city_lower = city.lower()
            filtered_jobs = [j for j in filtered_jobs if j.city and city_lower in j.city.lower()]
        
        if expertise:
            expertise_lower = expertise.lower()
            filtered_jobs = [j for j in filtered_jobs if j.expertise and expertise_lower in j.expertise.lower()]
        
        return filtered_jobs
