from __future__ import annotations

from typing import TypedDict, Literal, Optional, List, Dict, Any
from datetime import datetime


# Let's define the Categories, Routes, HandlerLevels, Urgency lvls
CATEGORY = Literal["billing", "technical", "feature_request", "account_management", "other"]
ROUTE = Literal["billing_queue", "tech_support_queue", "product_queue", "account_queue", "triage_queue"]
HANDLER_LEVEL = Literal["support", "specialist", "senior_engineer"]
URGENCY = Literal["low", "medium", "high", "critical"]


class TicketEvent(TypedDict):
    ts: str
    step: str
    message: str
    data: Dict[str, Any]

class TicketState(TypedDict, total=False):
    ticket_id: str
    subject: str
    content: str
    consumer_id: Optional[str]
    customer_tier: Optional[Literal["free", "premium", "enterprise"]]
    channel: Optional[Literal["email", "chat", "web", "api"]]
    created_at: str
    updated_at: str
    attachments: Optional[List[str]]
    tags: Optional[List[str]]

    # Classification
    category: CATEGORY
    category_confidence: float
    category_explanation: Optional[str]

    # Routing
    route: ROUTE
    handler_level: HANDLER_LEVEL
    routing_explanation: Optional[str]

    # Urgency
    urgency: URGENCY
    urgency_confidence: float
    urgency_explanation: Optional[str]

 
    events: List[TicketEvent]
    errors: List[str]


def new_state(
        *,
        ticket_id: str,
        subject: str,
        content: str,
        custormer_id: str|None =None,
        customer_tier: str|None =None,
        channel: str|None = None,
) -> TicketState:
    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "content": content,
        "consumer_id": custormer_id,
        "customer_tier": customer_tier,
        "channel": channel,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "events": [],
        "errors": [],
    }