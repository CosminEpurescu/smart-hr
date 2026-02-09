#!/usr/bin/env python3
"""
Main script to run the ING Job Parser.
"""

import argparse
import sys
from pathlib import Path

from ing_job_parser import INGJobParser
from ing_job_parser.exporter import JobExporter


def main():
    parser = argparse.ArgumentParser(
        description="Parse job listings from ING Careers website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all job listings (basic info only)
  python main.py --output jobs.json

  # Get jobs with full details (slower)
  python main.py --output jobs.json --details

  # Limit to first 5 pages
  python main.py --output jobs.json --max-pages 5

  # Export to CSV
  python main.py --output jobs.csv --format csv

  # Search for specific jobs
  python main.py --output jobs.json --keyword "developer"

  # Filter by country
  python main.py --output jobs.json --country Poland
        """
    )
    
    parser.add_argument(
        "--output", "-o",
        default="jobs.json",
        help="Output file path (default: jobs.json)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "excel"],
        default=None,
        help="Output format (auto-detected from file extension if not specified)"
    )
    
    parser.add_argument(
        "--details", "-d",
        action="store_true",
        help="Fetch full details for each job (slower)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to scrape"
    )
    
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=None,
        help="Maximum number of jobs to process"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        default=None,
        help="Search keyword to filter jobs"
    )
    
    parser.add_argument(
        "--country",
        type=str,
        default=None,
        help="Filter by country"
    )
    
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Filter by city"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output"
    )
    
    args = parser.parse_args()
    
    # Determine output format
    output_path = Path(args.output)
    if args.format:
        output_format = args.format
    else:
        ext = output_path.suffix.lower()
        if ext == ".csv":
            output_format = "csv"
        elif ext in [".xlsx", ".xls"]:
            output_format = "excel"
        else:
            output_format = "json"
    
    print(f"ING Careers Job Parser")
    print(f"=" * 50)
    
    # Initialize parser
    job_parser = INGJobParser(delay=args.delay)
    
    # Get total jobs count
    total_jobs = job_parser.get_total_jobs()
    print(f"Total jobs available: {total_jobs}")
    
    # Fetch jobs
    if args.keyword or args.country or args.city:
        print(f"\nSearching with filters...")
        jobs = job_parser.search_jobs(
            country=args.country,
            city=args.city,
            keyword=args.keyword,
            max_pages=args.max_pages
        )
    elif args.details:
        print(f"\nFetching all jobs with full details...")
        jobs = job_parser.get_all_jobs_with_details(
            max_pages=args.max_pages,
            max_jobs=args.max_jobs,
            show_progress=not args.quiet
        )
    else:
        print(f"\nFetching job listings...")
        jobs = job_parser.get_all_job_listings(
            max_pages=args.max_pages,
            show_progress=not args.quiet
        )
    
    if args.max_jobs and len(jobs) > args.max_jobs:
        jobs = jobs[:args.max_jobs]
    
    print(f"\nFound {len(jobs)} jobs")
    
    # Export
    if output_format == "csv":
        JobExporter.to_csv(jobs, str(output_path))
    elif output_format == "excel":
        JobExporter.to_excel(jobs, str(output_path))
    else:
        JobExporter.to_json(jobs, str(output_path))
    
    print(f"\nDone! Jobs exported to {output_path}")
    
    # Print sample
    if jobs and not args.quiet:
        print(f"\nSample jobs:")
        for job in jobs[:3]:
            print(f"  - {job.title} ({job.city}, {job.country})")
            print(f"    URL: {job.url}")


if __name__ == "__main__":
    main()
