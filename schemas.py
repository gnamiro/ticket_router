from pydantic import BaseModel, Field
from typing import Literal


# Let's define the Categories, Routes, HandlerLevels, Urgency lvls
Category = Literal["billing", "technical", "feature_request", "account_management", "other"]
Urgency = Literal["low", "medium", "high", "critical"]
HandlerLevel = Literal["support", "specialist", "senior_engineer"]
Route = Literal["billing_queue", "tech_support_queue", "product_queue", "account_queue", "triage_queue"]


class ClassificationOut(BaseModel):
    category: Category = Field(..., description="The category of the ticket")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence 0..1")
    reason: str = Field(..., description="Explanation of the classification decision")

class UrgencyOut(BaseModel):
    urgency_level: Urgency
    urgency_score: float = Field(..., ge=0.0, le=1.0, description="0..1, higher means more urgent")
    reason: str
    
class RoutingOut(BaseModel):
    route_to: Route = Field(..., description="The route for the ticket")
    handler_level: HandlerLevel = Field(..., description="The handler level for the ticket")
    reason: str = Field(..., description="Explanation of the routing decision")