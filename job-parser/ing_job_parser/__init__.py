"""
ING Careers Job Parser
A Python package to scrape and parse job listings from ING Careers website.
"""

from .parser import INGJobParser
from .models import Job

__version__ = "1.0.0"
__all__ = ["INGJobParser", "Job"]
