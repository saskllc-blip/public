"""Fictional jobs used by the read-only pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MockJob:
    job_id: str
    title: str
    company: str
    location: str
    description_summary: str
    description_full: str
    pipeline_stage: str
    posted_date: str
    salary_range: str


_STAGES = ("Open", "Under Review", "Interview Scheduled", "Offer Extended")
MOCK_JOBS = [
    MockJob(
        f"job-{index:03}", title, f"Fictional Employer {index}", location,
        "Review a fictional property workflow and coordinate clear follow-up.",
        "This demonstration role documents outcomes and supports human review. The demo does not collect applications or transmit personal information.",
        _STAGES[index - 1], f"{index + 1} days ago", salary,
    )
    for index, (title, location, salary) in enumerate((
        ("Resident Experience Coordinator", "Remote", "$52,000–$64,000"),
        ("Property Operations Analyst", "Sacramento, CA", "$68,000–$82,000"),
        ("Leasing Process Specialist", "Hybrid", "$61,000–$75,000"),
        ("Facilities Program Manager", "Portland, OR", "$88,000–$108,000"),
    ), start=1)
]

