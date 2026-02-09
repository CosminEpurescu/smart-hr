#!/usr/bin/env python3
"""
Example usage of the ING Job Parser.
"""

from ing_job_parser import INGJobParser, Job
from ing_job_parser.exporter import JobExporter


def example_basic_usage():
    """Basic usage example."""
    print("=" * 60)
    print("Basic Usage Example")
    print("=" * 60)
    
    # Initialize parser
    parser = INGJobParser(delay=1.0)
    
    # Get total number of jobs
    total = parser.get_total_jobs()
    print(f"\nTotal jobs available on ING Careers: {total}")
    
    # Get first page of job listings
    jobs = parser.get_job_listings(page=1)
    print(f"Jobs on first page: {len(jobs)}")
    
    # Print first 5 jobs
    print("\nFirst 5 jobs:")
    for job in jobs[:5]:
        print(f"  - {job.title}")
        print(f"    Location: {job.city}, {job.country}")
        print(f"    URL: {job.url}")
        print()


def example_get_all_jobs():
    """Get all jobs (limited to 3 pages for demo)."""
    print("=" * 60)
    print("Get All Jobs Example (limited to 3 pages)")
    print("=" * 60)
    
    parser = INGJobParser(delay=0.5)
    
    # Get jobs from first 3 pages
    jobs = parser.get_all_job_listings(max_pages=3, show_progress=True)
    print(f"\nTotal jobs fetched: {len(jobs)}")
    
    # Export to JSON
    JobExporter.to_json(jobs, "sample_jobs.json")
    
    return jobs


def example_get_job_details():
    """Get full details for specific jobs."""
    print("=" * 60)
    print("Get Job Details Example")
    print("=" * 60)
    
    parser = INGJobParser(delay=1.0)
    
    # Get first page of jobs
    jobs = parser.get_job_listings(page=1)
    
    if jobs:
        # Get details for first job
        print(f"\nFetching details for: {jobs[0].title}")
        detailed_job = parser.get_job_details(jobs[0])
        
        print(f"\nJob Details:")
        print(f"  Title: {detailed_job.title}")
        print(f"  Location: {detailed_job.city}, {detailed_job.country}")
        print(f"  Posted: {detailed_job.posted_date}")
        print(f"  Entity: {detailed_job.ing_entity}")
        print(f"  Apply URL: {detailed_job.apply_url}")
        print(f"  Contact: {detailed_job.contact_email}")
        
        if detailed_job.description:
            print(f"\nDescription preview:")
            print(f"  {detailed_job.description[:300]}...")
        
        if detailed_job.requirements:
            print(f"\nRequirements preview:")
            print(f"  {detailed_job.requirements[:300]}...")


def example_search_jobs():
    """Search for jobs with filters."""
    print("=" * 60)
    print("Search Jobs Example")
    print("=" * 60)
    
    parser = INGJobParser(delay=0.5)
    
    # Search for developer jobs
    print("\nSearching for 'Developer' jobs...")
    dev_jobs = parser.search_jobs(keyword="Developer", max_pages=2)
    print(f"Found {len(dev_jobs)} developer jobs")
    
    for job in dev_jobs[:5]:
        print(f"  - {job.title} ({job.city})")


def example_export_formats():
    """Export jobs to different formats."""
    print("=" * 60)
    print("Export Formats Example")
    print("=" * 60)
    
    parser = INGJobParser(delay=0.5)
    
    # Get some jobs
    jobs = parser.get_job_listings(page=1)
    
    if jobs:
        # Export to different formats
        print("\nExporting to different formats...")
        
        JobExporter.to_json(jobs, "jobs_sample.json")
        JobExporter.to_csv(jobs, "jobs_sample.csv")
        
        # Convert to DataFrame for analysis
        df = JobExporter.to_dataframe(jobs)
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # Sample analysis
        if 'country' in df.columns:
            print(f"\nJobs by country:")
            print(df['country'].value_counts().head())


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("ING Job Parser - Examples")
    print("=" * 60 + "\n")
    
    # Run basic example
    example_basic_usage()
    
    # Uncomment to run other examples:
    # example_get_all_jobs()
    # example_get_job_details()
    # example_search_jobs()
    # example_export_formats()


if __name__ == "__main__":
    main()
