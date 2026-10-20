"""Fictional LinkedIn-style posts; no record comes from LinkedIn or a customer."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class MockComment:
    commenter_name: str
    comment_body: str
    comment_timestamp: str
    ai_reply_draft: str


@dataclass(frozen=True)
class MockPost:
    post_id: str
    author_name: str
    author_title: str
    author_company: str
    post_date: str
    post_body: str
    likes: int
    comments: int
    shares: int
    ai_reply_draft: str
    comments_list: List[MockComment] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.post_id


def _post(index: int) -> MockPost:
    topics = (
        "clear maintenance ownership", "predictable resident updates",
        "decision-oriented dashboards", "consistent leasing workflows",
        "plain-language portals", "preventive maintenance planning",
    )
    topic = topics[index - 1]
    return MockPost(
        f"trend-{index:03}", f"Demo Author {index}", "Property Operations Lead",
        f"Fictional Company {index}", f"{index} day(s) ago",
        f"A fictional pilot team is exploring {topic}. The team documents each step, keeps a person responsible for decisions, and measures whether the workflow gives residents useful information without relying on private records.",
        80 + index * 17, 5 + index, 2 + index,
        f"The emphasis on {topic} is useful. Clear ownership and human review make this demonstration approach easier to understand and evaluate.",
    )


def _my_post(index: int) -> MockPost:
    comments = [
        MockComment(
            f"Sample Commenter {index}-{number}",
            "This fictional workflow makes the review boundary easy to understand.",
            f"{number} day(s) ago",
            "Thank you. The pilot keeps a human responsible for every final decision.",
        )
        for number in (1, 2)
    ]
    return MockPost(
        f"mine-{index:03}", "Alex Morgan", "Demo Product Lead", "SASK LLC",
        f"{index + 1} days ago",
        "This public pilot uses deterministic fictional examples, visible disclosures, and human review. It demonstrates a narrow engagement workflow without connecting to LinkedIn, customer records, or a paid model.",
        65 + index * 13, len(comments), 3 + index,
        "Thanks for the thoughtful response. Clear demo boundaries are part of the product design.",
        comments,
    )


TRENDING_POSTS = [_post(index) for index in range(1, 7)]
MY_POSTS = [_my_post(index) for index in range(1, 5)]

