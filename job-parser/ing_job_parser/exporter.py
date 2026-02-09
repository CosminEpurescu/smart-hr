"""
Export utilities for job data.
"""

import json
import csv
from typing import List
from pathlib import Path

import pandas as pd

from .models import Job


class JobExporter:
    """Export jobs to various formats."""
    
    @staticmethod
    def to_json(jobs: List[Job], filepath: str, indent: int = 2) -> None:
        """
        Export jobs to JSON file.
        
        Args:
            jobs: List of Job objects
            filepath: Output file path
            indent: JSON indentation
        """
        data = [job.to_dict() for job in jobs]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        print(f"Exported {len(jobs)} jobs to {filepath}")
    
    @staticmethod
    def to_csv(jobs: List[Job], filepath: str) -> None:
        """
        Export jobs to CSV file.
        
        Args:
            jobs: List of Job objects
            filepath: Output file path
        """
        if not jobs:
            print("No jobs to export")
            return
        
        data = [job.to_dict() for job in jobs]
        
        # Flatten lists in the data
        for d in data:
            if "locations" in d and isinstance(d["locations"], list):
                d["locations"] = "; ".join(d["locations"])
        
        fieldnames = list(data[0].keys())
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"Exported {len(jobs)} jobs to {filepath}")
    
    @staticmethod
    def to_excel(jobs: List[Job], filepath: str) -> None:
        """
        Export jobs to Excel file.
        
        Args:
            jobs: List of Job objects
            filepath: Output file path
        """
        if not jobs:
            print("No jobs to export")
            return
        
        data = [job.to_dict() for job in jobs]
        
        # Flatten lists in the data
        for d in data:
            if "locations" in d and isinstance(d["locations"], list):
                d["locations"] = "; ".join(d["locations"])
        
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine="openpyxl")
        print(f"Exported {len(jobs)} jobs to {filepath}")
    
    @staticmethod
    def to_dataframe(jobs: List[Job]) -> pd.DataFrame:
        """
        Convert jobs to pandas DataFrame.
        
        Args:
            jobs: List of Job objects
            
        Returns:
            pandas DataFrame
        """
        data = [job.to_dict() for job in jobs]
        return pd.DataFrame(data)
