"""Mock LinkedIn posts and comments for demo."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class MockComment:
    """Mock comment on a post."""
    commenter_name: str
    comment_body: str
    comment_timestamp: str
    ai_reply_draft: str


@dataclass
class TrendingPost:
    """Mock trending post."""
    author_name: str
    author_title: str
    author_company: str
    post_date: str
    post_body: str
    likes: int
    comments: int
    shares: int
    ai_reply_draft: str
    post_id: str = ""
    comments_list: List[MockComment] = field(default_factory=list)


# Trending posts (5-8)
TRENDING_POSTS = [
    TrendingPost(
        post_id="trending_001",
        author_name="Sarah Chen",
        author_title="Property Manager",
        author_company="Urban Rentals",
        post_date="2 days ago",
        post_body=(
            "Thought leadership on property management automation. AI is transforming "
            "how we screen tenants, coordinate maintenance, and manage finances. The key "
            "is ensuring data privacy and maintaining human oversight at every step. "
            "What's your experience with AI in property management? Have you seen measurable "
            "improvements in efficiency?"
        ),
        likes=145,
        comments=23,
        shares=8,
        ai_reply_draft=(
            "Great post, Sarah! We've seen similar benefits at SASK LLC. Automating tenant "
            "screening has reduced our turnaround time from 10 days to 3 days, while maintaining "
            "rigorous compliance standards. The human-in-the-loop approach is essential—AI handles "
            "initial filtering, but property managers make the final decision."
        ),
    ),
    TrendingPost(
        post_id="trending_002",
        author_name="James Rodriguez",
        author_title="Real Estate Investor",
        author_company="Rodriguez Capital",
        post_date="4 days ago",
        post_body=(
            "Portfolio diversification across residential, commercial, and mixed-use properties "
            "continues to be the winning strategy in volatile markets. Our team focuses on identifying "
            "undervalued assets and maximizing operational efficiency through technology-enabled "
            "property management. Looking forward to sharing insights at the upcoming REI conference."
        ),
        likes=89,
        comments=12,
        shares=6,
        ai_reply_draft=(
            "James, appreciate your insights on portfolio management. At SASK LLC, we've found that "
            "diversification combined with data-driven decision-making significantly improves ROI. "
            "Our dashboard provides real-time visibility into occupancy, maintenance costs, and tenant "
            "satisfaction across all properties."
        ),
    ),
    TrendingPost(
        post_id="trending_003",
        author_name="Michelle Torres",
        author_title="Compliance Officer",
        author_company="PropTech Solutions",
        post_date="5 days ago",
        post_body=(
            "Navigating the evolving landscape of fair housing regulations and data privacy laws is "
            "critical for property managers and tech companies. Our latest webinar covered Fair Housing "
            "Act updates, CCPA implications, and best practices for tenant data protection. Compliance "
            "isn't just legal—it's foundational to trust."
        ),
        likes=167,
        comments=31,
        shares=18,
        ai_reply_draft=(
            "Thank you for highlighting these important compliance topics, Michelle. At SASK LLC, we "
            "take compliance seriously—every tenant interaction is audited, every data point is encrypted, "
            "and our processes align with latest fair housing guidelines. Would love to discuss your "
            "approach to data governance."
        ),
    ),
    TrendingPost(
        post_id="trending_004",
        author_name="David Kim",
        author_title="Facilities Manager",
        author_company="Metro Properties",
        post_date="6 days ago",
        post_body=(
            "Preventive maintenance is the difference between profitability and crisis management. "
            "Implementing IoT sensors and predictive analytics on our portfolio has reduced emergency "
            "repairs by 40% and extended asset lifespan significantly. Technology investment in "
            "maintenance pays dividends quickly."
        ),
        likes=203,
        comments=45,
        shares=22,
        ai_reply_draft=(
            "Excellent insights on preventive maintenance, David. SASK LLC integrates maintenance "
            "scheduling with occupancy patterns to optimize both cost and tenant satisfaction. Our "
            "system flags issues before they become emergencies."
        ),
    ),
    TrendingPost(
        post_id="trending_005",
        author_name="Lisa Anderson",
        author_title="Financial Analyst",
        author_company="Capital Markets Group",
        post_date="7 days ago",
        post_body=(
            "Market outlook for commercial real estate in Q4: interest rates remain elevated, but certain "
            "subsectors show strong fundamentals. Mixed-use developments in urban cores continue to attract "
            "capital. Investors should focus on cash flow stability and tenant diversification. "
            "The winners will be those who adapt quickly to changing conditions."
        ),
        likes=112,
        comments=18,
        shares=9,
        ai_reply_draft=(
            "Lisa, your market analysis resonates. At SASK LLC, we're seeing strong demand for well-managed "
            "mixed-use properties in urban corridors. Our data shows tenant retention is highest when "
            "buildings are actively managed with tenant satisfaction as a key metric."
        ),
    ),
    TrendingPost(
        post_id="trending_006",
        author_name="Robert Smith",
        author_title="VP Operations",
        author_company="Stellar Homes",
        post_date="8 days ago",
        post_body=(
            "Scaling operations across 200+ properties requires robust systems, clear communication, and "
            "empowered regional teams. Centralized oversight with local autonomy is our management philosophy. "
            "Each property has unique character; one-size-fits-all policies don't work in real estate."
        ),
        likes=78,
        comments=14,
        shares=5,
        ai_reply_draft=(
            "Absolutely right about balancing centralized control with local autonomy, Robert. SASK LLC's "
            "dashboard provides consistent visibility while regional teams retain flexibility on tenant relations "
            "and maintenance decisions."
        ),
    ),
    TrendingPost(
        post_id="trending_007",
        author_name="Amanda Foster",
        author_title="Sustainability Director",
        author_company="GreenLiving Collective",
        post_date="9 days ago",
        post_body=(
            "Sustainable property management is no longer a nice-to-have—it's a market differentiator. Buildings "
            "with strong environmental ratings attract premium tenants and command higher rents. Energy efficiency, "
            "water conservation, and waste reduction are proven ROI drivers."
        ),
        likes=156,
        comments=27,
        shares=13,
        ai_reply_draft=(
            "Amanda, sustainability initiatives align perfectly with tenant expectations. SASK LLC properties "
            "prioritize energy efficiency and waste reduction. Our analytics track these metrics and correlate them "
            "with tenant satisfaction scores."
        ),
    ),
]

# My posts (4-6) - with comments
MY_POSTS = [
    TrendingPost(
        post_id="mypost_001",
        author_name="Alex Martinez",
        author_title="Director of Operations",
        author_company="SASK LLC",
        post_date="5 days ago",
        post_body=(
            "Today we launched a new dashboard for portfolio managers. Real-time occupancy, financials, and "
            "maintenance alerts in one place. This is the result of 6 months of user research and iteration. "
            "Excited to share learnings soon!"
        ),
        likes=287,
        comments=31,
        shares=15,
        ai_reply_draft="Thanks for the update!",
        comments_list=[
            MockComment(
                commenter_name="Priya Patel",
                comment_body="This dashboard looks fantastic! How does it handle multi-property views?",
                comment_timestamp="4 days ago",
                ai_reply_draft=(
                    "Great question, Priya! The dashboard aggregates metrics across all properties in real-time. "
                    "You can drill down to individual properties or compare across regions."
                )
            ),
            MockComment(
                commenter_name="Marcus Thompson",
                comment_body="Is this available for smaller portfolios (5-10 properties)?",
                comment_timestamp="3 days ago",
                ai_reply_draft=(
                    "Absolutely! The dashboard scales from small portfolios to enterprise deployments. Pricing is "
                    "per-property, making it accessible for all portfolio sizes."
                )
            ),
            MockComment(
                commenter_name="Elena Vasquez",
                comment_body="How is data security handled for sensitive financial information?",
                comment_timestamp="2 days ago",
                ai_reply_draft=(
                    "Security is paramount. All data is encrypted in transit and at rest. We comply with CCPA, HIPAA "
                    "standards, and conduct regular third-party security audits."
                )
            ),
        ],
    ),
    TrendingPost(
        post_id="mypost_002",
        author_name="Alex Martinez",
        author_title="Director of Operations",
        author_company="SASK LLC",
        post_date="10 days ago",
        post_body=(
            "Excited to announce SASK LLC is now ISO 27001 certified! Data security and privacy are core to our "
            "mission. This certification reflects our commitment to protecting property manager and tenant information."
        ),
        likes=198,
        comments=22,
        shares=11,
        ai_reply_draft=(
            "Congratulations on the ISO 27001 certification! This is a significant achievement that demonstrates "
            "SASK LLC's commitment to data security and privacy. Tenant data protection is critical in property management. "
            "Would love to hear more about your implementation process and how it's improved your security posture."
        ),
        comments_list=[
            MockComment(
                commenter_name="John Park",
                comment_body="Congratulations! What was the biggest challenge in achieving certification?",
                comment_timestamp="9 days ago",
                ai_reply_draft=(
                    "The biggest challenge was ensuring consistent security practices across all systems while "
                    "maintaining user experience. We invested in automated compliance tooling."
                )
            ),
            MockComment(
                commenter_name="Sophia Nguyen",
                comment_body="Does this include SOC 2 Type II compliance as well?",
                comment_timestamp="8 days ago",
                ai_reply_draft=(
                    "SOC 2 Type II is on our roadmap for next year. ISO 27001 is the foundation—SOC 2 Type II builds "
                    "on that with additional audit requirements."
                )
            ),
        ],
    ),
    TrendingPost(
        post_id="mypost_003",
        author_name="Alex Martinez",
        author_title="Director of Operations",
        author_company="SASK LLC",
        post_date="15 days ago",
        post_body=(
            "Celebrating 100+ customers on SASK LLC's platform! From small independent investors to institutional "
            "portfolios, our community spans diverse property types and geographies. Thank you to every customer for "
            "their trust and feedback."
        ),
        likes=421,
        comments=58,
        shares=34,
        ai_reply_draft=(
            "This is an incredible milestone! Reaching 100+ customers shows the real value of your platform. "
            "The diversity of your customer base—from small investors to large institutional portfolios—speaks to the "
            "scalability and flexibility of your solution. Congratulations to the entire team!"
        ),
        comments_list=[
            MockComment(
                commenter_name="Grace Lee",
                comment_body="That's amazing growth! What's the average portfolio size of your customers?",
                comment_timestamp="14 days ago",
                ai_reply_draft=(
                    "Our customer base ranges from 2-property mom-and-pop operations to 500+ property institutional "
                    "portfolios. The platform scales beautifully across this range."
                )
            ),
            MockComment(
                commenter_name="Tom Blackwell",
                comment_body="Which property type has shown the highest adoption?",
                comment_timestamp="13 days ago",
                ai_reply_draft=(
                    "Multifamily residential leads adoption, but we're seeing strong growth in mixed-use and "
                    "commercial segments."
                )
            ),
        ],
    ),
    TrendingPost(
        post_id="mypost_004",
        author_name="Alex Martinez",
        author_title="Director of Operations",
        author_company="SASK LLC",
        post_date="20 days ago",
        post_body=(
            "Property managers spend 30% of time on administrative tasks. Our latest feature—automated lease "
            "compliance tracking—eliminates manual checklist maintenance. One less thing to worry about."
        ),
        likes=156,
        comments=19,
        shares=8,
        ai_reply_draft=(
            "This is a game-changer for property managers! Reducing administrative overhead by automating lease "
            "compliance tracking frees up time for higher-value activities like tenant relationships and property improvement. "
            "Excited to see how this feature evolves!"
        ),
        comments_list=[
            MockComment(
                commenter_name="Rachel Brown",
                comment_body="Does it support multiple lease types (fixed-term, month-to-month, commercial)?",
                comment_timestamp="19 days ago",
                ai_reply_draft=(
                    "Yes! The system supports all common lease types and can be customized for unusual arrangements."
                )
            ),
            MockComment(
                commenter_name="William Chen",
                comment_body="Does it integrate with accounting software?",
                comment_timestamp="18 days ago",
                ai_reply_draft=(
                    "Integration with QuickBooks and Xero is available. Native integration with other accounting "
                    "platforms coming soon."
                )
            ),
        ],
    ),
]
