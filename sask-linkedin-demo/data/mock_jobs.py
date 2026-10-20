"""Mock job listings for job pipeline tab."""

from dataclasses import dataclass


@dataclass
class MockJob:
    """Mock job listing."""
    job_id: str
    title: str
    company: str
    location: str
    description_summary: str
    description_full: str
    pipeline_stage: str
    posted_date: str
    salary_range: str


# Mock jobs (3-5)
MOCK_JOBS = [
    MockJob(
        job_id="job_001",
        title="Senior Property Manager",
        company="SASK LLC",
        location="Austin, TX",
        description_summary=(
            "Lead property management operations for a portfolio of 50+ residential "
            "and commercial properties."
        ),
        description_full=(
            "We're hiring a Senior Property Manager to oversee our growing portfolio. "
            "Responsibilities include:\n\n"
            "• Tenant screening and lease negotiation\n"
            "• Maintenance coordination and vendor management\n"
            "• Rent collection and accounting\n"
            "• Property inspections and compliance\n"
            "• Emergency response and crisis management\n"
            "• Tenant relations and conflict resolution\n\n"
            "We're looking for someone with 5+ years of experience in residential or "
            "commercial property management, strong communication skills, comfort with "
            "property management software, and ability to work independently and as part "
            "of a distributed team. Competitive salary, health insurance, and professional "
            "development budget included."
        ),
        pipeline_stage="Open",
        posted_date="5 days ago",
        salary_range="$65k–$85k",
    ),
    MockJob(
        job_id="job_002",
        title="Property Compliance Specialist",
        company="SASK LLC",
        location="Remote",
        description_summary=(
            "Ensure all properties meet fair housing, building code, and regulatory "
            "compliance standards."
        ),
        description_full=(
            "SASK LLC is seeking a Property Compliance Specialist to work with our "
            "growing portfolio and ensure all properties meet current regulations.\n\n"
            "Key responsibilities:\n"
            "• Monitor fair housing compliance across all properties\n"
            "• Manage building code and permit compliance\n"
            "• Audit tenant documentation and lease agreements\n"
            "• Prepare compliance reports for stakeholders\n"
            "• Coordinate with legal counsel on complex issues\n"
            "• Training property managers on new regulations\n\n"
            "Required: 3+ years in real estate compliance or legal. Excellent attention to "
            "detail and understanding of federal/state/local regulations. This is a remote "
            "position with flexible hours."
        ),
        pipeline_stage="Under Review",
        posted_date="10 days ago",
        salary_range="$55k–$72k",
    ),
    MockJob(
        job_id="job_003",
        title="Full Stack Developer (Property Tech)",
        company="SASK LLC",
        location="Austin, TX",
        description_summary=(
            "Build and maintain full-stack features for our property management platform "
            "serving 100+ customers."
        ),
        description_full=(
            "SASK LLC is growing our engineering team! We're looking for a Full Stack "
            "Developer to help build the next generation of property management tools.\n\n"
            "What you'll do:\n"
            "• Design and implement backend APIs (Python, Django/FastAPI)\n"
            "• Build responsive frontend features (React, TypeScript)\n"
            "• Optimize database queries and application performance\n"
            "• Write tests and maintain code quality standards\n"
            "• Collaborate with product and design teams\n"
            "• Participate in code review and technical discussions\n\n"
            "Required: 3+ years full-stack development, proficiency in Python and "
            "JavaScript/TypeScript, experience with relational databases. Nice-to-have: "
            "real estate software experience, experience with Streamlit."
        ),
        pipeline_stage="Interview Scheduled",
        posted_date="7 days ago",
        salary_range="$90k–$130k",
    ),
    MockJob(
        job_id="job_004",
        title="Maintenance Coordinator",
        company="SASK LLC",
        location="Austin, TX",
        description_summary=(
            "Coordinate preventive and emergency maintenance across SASK LLC's growing "
            "property portfolio."
        ),
        description_full=(
            "Join SASK LLC's maintenance team as a Maintenance Coordinator!\n\n"
            "In this role, you'll:\n"
            "• Schedule routine and preventive maintenance visits\n"
            "• Track maintenance requests and work orders\n"
            "• Manage vendor relationships and quality standards\n"
            "• Coordinate emergency repairs and same-day response\n"
            "• Budget forecasting for maintenance expenses\n"
            "• Tenant communication about maintenance activities\n\n"
            "Requirements: 2+ years maintenance coordination experience, excellent "
            "organizational skills, ability to prioritize competing requests, and "
            "comfort with maintenance software. Background in construction or facilities "
            "management is valuable."
        ),
        pipeline_stage="Offer Extended",
        posted_date="12 days ago",
        salary_range="$45k–$58k",
    ),
    MockJob(
        job_id="job_005",
        title="Marketing Manager",
        company="SASK LLC",
        location="Austin, TX",
        description_summary=(
            "Lead marketing initiatives to grow SASK LLC's customer base and brand "
            "awareness in the property management space."
        ),
        description_full=(
            "SASK LLC is looking for a Marketing Manager to accelerate customer "
            "acquisition and brand growth.\n\n"
            "Your focus:\n"
            "• Develop and execute marketing campaigns targeting property managers\n"
            "• Content creation (blogs, case studies, webinars)\n"
            "• Manage social media and LinkedIn presence\n"
            "• Customer acquisition funnel optimization\n"
            "• Partnership and integration marketing\n"
            "• Analytics and ROI reporting\n\n"
            "Ideal candidate has 4+ years B2B SaaS marketing experience, deep knowledge "
            "of the property management industry, strong writing skills, and experience "
            "with marketing automation platforms."
        ),
        pipeline_stage="Open",
        posted_date="3 days ago",
        salary_range="$60k–$80k",
    ),
]
