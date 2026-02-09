"""
Data models for job listings.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class Job:
    """Represents a job listing from ING Careers."""
    
    # Basic information
    job_id: str
    title: str
    url: str
    
    # Location
    city: Optional[str] = None
    country: Optional[str] = None
    locations: List[str] = field(default_factory=list)
    locations_raw: Optional[str] = None  # Raw locations string from listing (e.g., "Polska, Katowice; Polska, Warszawa;")
    
    # Job details
    expertise: Optional[str] = None
    experience_level: Optional[str] = None
    ing_entity: Optional[str] = None
    job_type: Optional[str] = None
    
    # Dates
    posted_date: Optional[str] = None
    
    # Full description (from job detail page)
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    full_content: Optional[str] = None
    
    # Application
    apply_url: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Metadata
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert job to dictionary."""
        return asdict(self)
    
    def __str__(self) -> str:
        return f"Job({self.title} - {self.city}, {self.country})"
    
    def __repr__(self) -> str:
        return self.__str__()
