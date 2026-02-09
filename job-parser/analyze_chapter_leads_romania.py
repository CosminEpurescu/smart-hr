#!/usr/bin/env python3
"""
Chapter Lead Romania Analyzer
Analyzes Chapter Lead positions in Romania and creates visualizations
to help candidates evaluate opportunities.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import Counter
import math

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    import numpy as np
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["uv", "pip", "install", "matplotlib", "numpy"])
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    import numpy as np


@dataclass
class ChapterLeadJob:
    """Parsed Chapter Lead job with computed scores."""
    job_id: str
    title: str
    url: str
    expertise: str
    city: str
    work_model: str
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_currency: Optional[str]
    has_benefits: bool
    num_requirements: int
    description_length: int
    contact_email: Optional[str]
    posted_date: Optional[str]
    
    # Computed scores (0-100)
    salary_score: float = 0.0
    flexibility_score: float = 0.0
    clarity_score: float = 0.0
    accessibility_score: float = 0.0
    overall_score: float = 0.0


def load_all_jobs(jobs_dir: str = "jobs_detailed") -> List[Dict]:
    """Load all job JSON files from directory."""
    jobs_path = Path(jobs_dir)
    jobs = []
    
    for json_file in jobs_path.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                jobs.append(json.load(f))
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return jobs


def is_chapter_lead_romania(job: Dict) -> bool:
    """Check if job is a Chapter Lead position in Romania."""
    title = (job.get("title") or "").lower()
    country = (job.get("location_country") or "").lower()
    full_desc = (job.get("full_description") or "").lower()
    
    # Must be in Romania
    is_romania = "romania" in country or "romania" in full_desc[:500]
    
    # Must be Chapter Lead
    is_chapter_lead = "chapter lead" in title or "chapter lead" in full_desc[:200]
    
    return is_romania and is_chapter_lead


def extract_expertise_area(job: Dict) -> str:
    """Extract the expertise/domain from the job."""
    title = job.get("title", "")
    expertise = job.get("expertise", "")
    
    # Try to extract specific area from title
    title_lower = title.lower()
    
    if "data scien" in title_lower:
        return "Data Science"
    elif "engineer" in title_lower or "engineering" in expertise.lower():
        return "Engineering"
    elif "analytics" in title_lower:
        return "Analytics"
    elif "security" in title_lower:
        return "Security"
    elif "devops" in title_lower or "platform" in title_lower:
        return "DevOps/Platform"
    elif "qa" in title_lower or "quality" in title_lower:
        return "Quality Assurance"
    elif "frontend" in title_lower or "front-end" in title_lower:
        return "Frontend"
    elif "backend" in title_lower or "back-end" in title_lower:
        return "Backend"
    elif "mobile" in title_lower:
        return "Mobile"
    elif expertise:
        return expertise
    else:
        return "Other"


def compute_scores(job: ChapterLeadJob, all_jobs: List[ChapterLeadJob]) -> None:
    """Compute candidate-relevant scores for a job."""
    
    # 1. Salary Score (0-100) - based on disclosed salary info
    if job.salary_max and job.salary_max > 0:
        # Normalize against max salary in dataset
        max_salary = max((j.salary_max for j in all_jobs if j.salary_max), default=1)
        job.salary_score = min(100, (job.salary_max / max_salary) * 100)
    else:
        # Penalize for not disclosing salary
        job.salary_score = 30  # Some credit for posting the job
    
    # 2. Flexibility Score (0-100) - work model preference
    work_model = job.work_model.lower() if job.work_model else ""
    if "remote" in work_model:
        job.flexibility_score = 100
    elif "hybrid" in work_model:
        job.flexibility_score = 75
    elif "office" in work_model or "on-site" in work_model:
        job.flexibility_score = 40
    else:
        job.flexibility_score = 50  # Unknown
    
    # 3. Clarity Score (0-100) - how well-described the job is
    clarity_points = 0
    
    # Has detailed description
    if job.description_length > 2000:
        clarity_points += 30
    elif job.description_length > 1000:
        clarity_points += 20
    elif job.description_length > 500:
        clarity_points += 10
    
    # Has clear requirements
    if job.num_requirements >= 5:
        clarity_points += 25
    elif job.num_requirements >= 3:
        clarity_points += 15
    elif job.num_requirements > 0:
        clarity_points += 10
    
    # Has salary info
    if job.salary_min or job.salary_max:
        clarity_points += 25
    
    # Has contact info
    if job.contact_email:
        clarity_points += 20
    
    job.clarity_score = min(100, clarity_points)
    
    # 4. Accessibility Score (0-100) - ease of application
    access_points = 50  # Base score
    
    # Has direct contact
    if job.contact_email:
        access_points += 25
    
    # Has benefits listed
    if job.has_benefits:
        access_points += 15
    
    # Recent posting (if date available)
    if job.posted_date:
        access_points += 10
    
    job.accessibility_score = min(100, access_points)
    
    # 5. Overall Score - weighted average
    job.overall_score = (
        job.salary_score * 0.30 +
        job.flexibility_score * 0.25 +
        job.clarity_score * 0.25 +
        job.accessibility_score * 0.20
    )


def parse_chapter_lead_job(job: Dict) -> ChapterLeadJob:
    """Parse a job dict into a ChapterLeadJob with computed metrics."""
    description = job.get("full_description", "") or ""
    requirements = job.get("requirements", []) or []
    benefits = job.get("benefits", []) or []
    
    return ChapterLeadJob(
        job_id=job.get("job_id", ""),
        title=job.get("title", "Unknown"),
        url=job.get("url", ""),
        expertise=extract_expertise_area(job),
        city=job.get("location_city", "Unknown"),
        work_model=job.get("work_model", "Unknown") or "Unknown",
        salary_min=job.get("salary_min"),
        salary_max=job.get("salary_max"),
        salary_currency=job.get("salary_currency"),
        has_benefits=len(benefits) > 0 or "offer" in description.lower(),
        num_requirements=len(requirements),
        description_length=len(description),
        contact_email=job.get("contact_email"),
        posted_date=job.get("posted_date"),
    )


def create_visualization(jobs: List[ChapterLeadJob], output_file: str = "chapter_leads_romania.png"):
    """Create a comprehensive visualization for Chapter Lead positions."""
    
    # Set up the figure with a nice style
    plt.style.use('seaborn-v0_8-darkgrid')
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("ING Chapter Lead Positions in Romania\nCandidate Opportunity Analysis", 
                 fontsize=16, fontweight='bold', y=0.98)
    
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)
    
    # Color palette - ING orange theme
    colors = ['#FF6200', '#FF8C00', '#FFA500', '#FFB347', '#FFCC80', '#FFE0B2']
    
    # 1. Overall Scores Radar Chart (top-left, spanning 2 cols)
    ax1 = fig.add_subplot(gs[0, :2], projection='polar')
    
    categories = ['Salary\nTransparency', 'Work\nFlexibility', 'Job\nClarity', 'Accessibility']
    num_vars = len(categories)
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]  # Complete the circle
    
    # Plot each job
    for i, job in enumerate(jobs[:6]):  # Top 6 by overall score
        values = [job.salary_score, job.flexibility_score, job.clarity_score, job.accessibility_score]
        values += values[:1]
        
        short_title = job.title[:30] + "..." if len(job.title) > 30 else job.title
        ax1.plot(angles, values, 'o-', linewidth=2, label=short_title, alpha=0.7)
        ax1.fill(angles, values, alpha=0.1)
    
    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(categories, size=9)
    ax1.set_ylim(0, 100)
    ax1.set_title("Top 6 Positions - Score Comparison", fontsize=11, fontweight='bold', pad=20)
    ax1.legend(loc='upper right', bbox_to_anchor=(1.4, 1.0), fontsize=7)
    
    # 2. Expertise Distribution (top-right)
    ax2 = fig.add_subplot(gs[0, 2])
    
    expertise_counts = Counter(job.expertise for job in jobs)
    labels = list(expertise_counts.keys())
    sizes = list(expertise_counts.values())
    
    wedges, texts, autotexts = ax2.pie(sizes, labels=labels, autopct='%1.0f%%', 
                                        colors=colors[:len(labels)],
                                        explode=[0.05] * len(labels))
    ax2.set_title("By Expertise Area", fontsize=11, fontweight='bold')
    
    # 3. Work Model Distribution (middle-left)
    ax3 = fig.add_subplot(gs[1, 0])
    
    work_models = Counter(job.work_model for job in jobs)
    model_labels = list(work_models.keys())
    model_counts = list(work_models.values())
    
    bars = ax3.barh(model_labels, model_counts, color=colors[:len(model_labels)])
    ax3.set_xlabel("Number of Positions")
    ax3.set_title("Work Model", fontsize=11, fontweight='bold')
    
    for bar, count in zip(bars, model_counts):
        ax3.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                 str(count), va='center', fontsize=10)
    
    # 4. City Distribution (middle-center)
    ax4 = fig.add_subplot(gs[1, 1])
    
    cities = Counter(job.city for job in jobs)
    city_labels = list(cities.keys())
    city_counts = list(cities.values())
    
    bars = ax4.bar(city_labels, city_counts, color='#FF6200')
    ax4.set_ylabel("Number of Positions")
    ax4.set_title("By City", fontsize=11, fontweight='bold')
    ax4.tick_params(axis='x', rotation=45)
    
    for bar, count in zip(bars, city_counts):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                 str(count), ha='center', fontsize=10)
    
    # 5. Overall Score Ranking (middle-right)
    ax5 = fig.add_subplot(gs[1, 2])
    
    sorted_jobs = sorted(jobs, key=lambda x: x.overall_score, reverse=True)
    top_jobs = sorted_jobs[:8]
    
    y_pos = np.arange(len(top_jobs))
    scores = [j.overall_score for j in top_jobs]
    short_titles = [j.title[:25] + "..." if len(j.title) > 25 else j.title for j in top_jobs]
    
    bars = ax5.barh(y_pos, scores, color='#FF6200', alpha=0.8)
    ax5.set_yticks(y_pos)
    ax5.set_yticklabels(short_titles, fontsize=8)
    ax5.set_xlabel("Overall Score")
    ax5.set_xlim(0, 100)
    ax5.set_title("Top Ranked Positions", fontsize=11, fontweight='bold')
    ax5.invert_yaxis()
    
    for bar, score in zip(bars, scores):
        ax5.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                 f'{score:.0f}', va='center', fontsize=9)
    
    # 6. Score Breakdown Table (bottom, spanning full width)
    ax6 = fig.add_subplot(gs[2, :])
    ax6.axis('off')
    
    # Create table data
    table_data = []
    for job in sorted_jobs[:10]:
        short_title = job.title[:40] + "..." if len(job.title) > 40 else job.title
        salary_info = f"€{job.salary_max:,.0f}" if job.salary_max else "Not disclosed"
        table_data.append([
            short_title,
            job.city,
            job.work_model,
            salary_info,
            f"{job.overall_score:.0f}"
        ])
    
    columns = ['Position', 'City', 'Work Model', 'Max Salary', 'Score']
    
    table = ax6.table(
        cellText=table_data,
        colLabels=columns,
        cellLoc='left',
        loc='center',
        colColours=['#FF6200'] * len(columns),
        cellColours=[['#FFF5EB'] * len(columns) for _ in range(len(table_data))]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    # Style header
    for i in range(len(columns)):
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    ax6.set_title("Top 10 Positions - Detailed Breakdown", fontsize=11, fontweight='bold', pad=20)
    
    # Add footer with methodology
    fig.text(0.5, 0.02, 
             "Score Methodology: Salary (30%) + Flexibility (25%) + Clarity (25%) + Accessibility (20%)",
             ha='center', fontsize=9, style='italic', alpha=0.7)
    
    # Save the figure
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"\n✅ Visualization saved to: {output_file}")
    
    # Also show it
    plt.show()


def print_summary(jobs: List[ChapterLeadJob]):
    """Print a text summary of the analysis."""
    print("\n" + "="*70)
    print("🦁 ING CHAPTER LEAD POSITIONS IN ROMANIA - ANALYSIS SUMMARY")
    print("="*70)
    
    print(f"\n📊 Total Chapter Lead positions found: {len(jobs)}")
    
    # By city
    cities = Counter(job.city for job in jobs)
    print(f"\n📍 By City:")
    for city, count in cities.most_common():
        print(f"   • {city}: {count} positions")
    
    # By expertise
    expertise = Counter(job.expertise for job in jobs)
    print(f"\n💼 By Expertise Area:")
    for exp, count in expertise.most_common():
        print(f"   • {exp}: {count} positions")
    
    # By work model
    work_models = Counter(job.work_model for job in jobs)
    print(f"\n🏠 By Work Model:")
    for model, count in work_models.most_common():
        print(f"   • {model}: {count} positions")
    
    # Top recommendations
    sorted_jobs = sorted(jobs, key=lambda x: x.overall_score, reverse=True)
    print(f"\n⭐ TOP 5 RECOMMENDED POSITIONS:")
    print("-"*70)
    
    for i, job in enumerate(sorted_jobs[:5], 1):
        print(f"\n{i}. {job.title}")
        print(f"   📍 {job.city} | 🏠 {job.work_model}")
        salary = f"€{job.salary_max:,.0f}" if job.salary_max else "Not disclosed"
        print(f"   💰 Salary: {salary}")
        print(f"   📊 Overall Score: {job.overall_score:.1f}/100")
        print(f"      • Salary Transparency: {job.salary_score:.0f}")
        print(f"      • Work Flexibility: {job.flexibility_score:.0f}")
        print(f"      • Job Clarity: {job.clarity_score:.0f}")
        print(f"      • Accessibility: {job.accessibility_score:.0f}")
    
    print("\n" + "="*70)


def main():
    """Main function to analyze Chapter Lead positions in Romania."""
    print("🔍 Loading job data...")
    
    # Load all jobs
    all_raw_jobs = load_all_jobs("jobs_detailed")
    print(f"   Loaded {len(all_raw_jobs)} total jobs")
    
    # Filter for Chapter Lead positions in Romania
    chapter_lead_jobs_raw = [job for job in all_raw_jobs if is_chapter_lead_romania(job)]
    print(f"   Found {len(chapter_lead_jobs_raw)} Chapter Lead positions in Romania")
    
    if not chapter_lead_jobs_raw:
        print("❌ No Chapter Lead positions found in Romania!")
        return
    
    # Parse and compute scores
    print("\n📊 Computing candidate scores...")
    chapter_lead_jobs = [parse_chapter_lead_job(job) for job in chapter_lead_jobs_raw]
    
    # Compute scores (need all jobs for normalization)
    for job in chapter_lead_jobs:
        compute_scores(job, chapter_lead_jobs)
    
    # Print summary
    print_summary(chapter_lead_jobs)
    
    # Create visualization
    print("\n🎨 Creating visualization...")
    create_visualization(chapter_lead_jobs)


if __name__ == "__main__":
    main()
