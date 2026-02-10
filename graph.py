from __future__ import annotations


from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from schemas import ClassificationOut, UrgencyOut, RoutingOut
import json
import re
from pydantic import ValidationError

from policy import should_review





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
    customer_tier: Optional[str]
    created_at: str

    # Classification
    category: str
    category_confidence: float
    category_explanation: Optional[str]

    # Routing
    route: str
    handler_level: str
    routing_explanation: Optional[str]

    # Urgency
    urgency: str
    urgency_confidence: float
    urgency_explanation: Optional[str]

 
    events: List[TicketEvent]
    errors: List[str]


def add_event(
        state: TicketState,
        step: str,
        message: str, 
        data: Dict[str, Any] | None = None) -> None:
    if "events" not in state:
        state["events"]= []
    state["events"].append({
        "ts": datetime.now().isoformat(),
        "step": step,
        "message": message,
        "data": data or {},
    })

def build_llm(model_name: str = "llama3.2:3b") -> ChatOllama:
    return ChatOllama(model=model_name, temperature=0.1)


# Node 1: Classifier
def classifier_node(state: TicketState) -> TicketState:
    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You classify SaaS support tickets into: billing, technical, feature_request, account_management, other. "
         "Return a structured JSON output."),
         ("human",
          "Subject: {subject}\n\nTicket:\n{content}\n\nCustomer tier: {customer_tier}")
    ])
    chain = prompt | llm.with_structured_output(ClassificationOut)
    out: ClassificationOut = chain.invoke({
        "subject": state.get("subject", ""),
        "content": state.get("content", ""),
        "customer_tier": state.get("customer_tier", "unknown"),
    })

    state["category"] = out.category
    state["category_confidence"] = out.confidence
    state["category_reason"] = out.reason

    add_event(state, "classifier", "Classified ticket", out.model_dump())

    return state

# Node 2: Urgency
def _extract_json(text: str) -> str:
    # grab the first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text

def urgency_node(state: TicketState) -> TicketState:
    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "Return ONLY valid JSON with EXACT keys.\n"
        "Example format (follow exactly):\n"
        "{{\"urgency_level\":\"low|medium|high|critical\","
        "\"urgency_score\":0.0,"
        "\"reason\":\"...\"}}\n"
        "Rules:\n"
        "- Do NOT add extra keys\n"
        "- urgency_score MUST be a float between 0 and 1\n"),
        ("human",
        "Subject: {subject}\n\n"
        "Ticket:\n{content}\n\n"
        "Category: {category}\n"
        "Customer tier: {customer_tier}\n")
    ])
    # First attempt: structured output (if it works)
    try:
        chain = prompt | llm.with_structured_output(UrgencyOut)
        out: UrgencyOut = chain.invoke({
            "subject": state.get("subject", ""),
            "content": state.get("content", ""),
            "category": state.get("category", "other"),
            "customer_tier": state.get("customer_tier", "unknown"),
        })
        state["urgency_level"] = out.urgency_level
        state["urgency_score"] = float(out.urgency_score)
        state["urgency_reason"] = out.reason
        add_event(state, "urgency", "Assessed urgency (structured)", out.model_dump())
        return state
    except Exception as e:
        add_event(state, "urgency", "Structured parsing failed; attempting JSON repair", {"error": str(e)})

    # Second attempt: raw JSON + repair mapping
    msg = (prompt | llm).invoke({
        "subject": state.get("subject", ""),
        "content": state.get("content", ""),
        "category": state.get("category", "other"),
        "customer_tier": state.get("customer_tier", "unknown"),
    })
    raw = msg.content.strip()
    raw_json = _extract_json(raw)

    try:
        data = json.loads(raw_json)

        # repair common key mistakes
        if "urgency_level" not in data and "urgency" in data:
            data["urgency_level"] = data.pop("urgency")

        # repair confidence/score key typos
        if "urgency_score" not in data:
            for k in list(data.keys()):
                if "condif" in k or "confid" in k or "score" in k:
                    data["urgency_score"] = data[k]
                    break

        # clamp score into 0..1 if model returns 1..10 or 0..100
        if "urgency_score" in data:
            s = float(data["urgency_score"])
            # if it looks like 1..10
            if s > 1 and s <= 10:
                s = s / 10.0
            # if it looks like 0..100
            if s > 10:
                s = min(s / 100.0, 1.0)
            data["urgency_score"] = max(0.0, min(1.0, s))

        out = UrgencyOut(**data)

        state["urgency_level"] = out.urgency_level
        state["urgency_score"] = float(out.urgency_score)
        state["urgency_reason"] = out.reason
        add_event(state, "urgency", "Assessed urgency (repaired)", {"raw": raw, "parsed": out.model_dump()})
        return state

    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        # final fallback: safe defaults + human review
        state["urgency_level"] = "high" if "down" in state.get("content", "").lower() else "medium"
        state["urgency_score"] = 0.8 if state["urgency_level"] == "high" else 0.5
        state["urgency_reason"] = f"Fallback due to parsing failure: {e}"
        state["errors"].append(str(e))
        add_event(state, "urgency", "Fallback urgency applied", {"raw": raw, "error": str(e)})
        return state


# Node 3: Router
def router_node(state: TicketState) -> TicketState:
    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
            "You route SaaS support tickets. Use category + urgency to decide the queue and handler level.\n"
            "Allowed route_to: billing_queue, tech_support_queue, product_queue, account_queue, triage_queue\n"
            "Allowed handler_level: support, specialist, senior_engineer\n\n"
            "Rules:\n"
            "- billing -> billing_queue\n"
            "- account_management -> account_queue\n"
            "- feature_request -> product_queue\n"
            "- technical -> tech_support_queue\n"
            "- if uncertain -> triage_queue\n"
            "- technical + (high|critical) -> senior_engineer\n\n"
            "Return ONLY valid JSON with EXACT keys.\n"
            "Example format:\n"
            "{{\"route_to\":\"triage_queue\",\"handler_level\":\"specialist\",\"reason\":\"...\"}}\n"
            "No extra keys."),
        ("human",
            "Subject: {subject}\n\n"
            "Ticket:\n{content}\n\n"
            "Category: {category} (conf={conf})\n"
            "Urgency: {urgency} (score={score})\n"
            "Customer tier: {customer_tier}\n")
    ])

    chain = prompt | llm.with_structured_output(RoutingOut)
    out: RoutingOut = chain.invoke({
        "subject": state.get("subject", ""),
        "content": state.get("content", ""),
        "category": state.get("category", "other"),
        "conf": state.get("category_confidence", 0.0),
        "urgency": state.get("urgency_level", "medium"),
        "score": state.get("urgency_score", 0.5),
        "customer_tier": state.get("customer_tier", "unknown"),
    })

    state["route_to"] = out.route_to
    state["handler_level"] = out.handler_level
    state["routing_reason"] = out.reason

    add_event(state, "router", "Routed ticket", out.model_dump())
    return state


# Human review node (if needed based on policy)
def human_review_node(state: TicketState) -> TicketState:
    state["needs_review"] = True
    state["review_reason"] = state.get("review_reason", "Low confidence / uncertain output")
    state["route_to"] = "triage_queue"
    state["handler_level"] = "specialist"
    state["routing_reason"] = f"Pending human review: {state['review_reason']}"
    add_event(state, "human_review", "Routed to triage pending human review", {})
    return state

CONF_MIN = 0.7

def after_classify(state: TicketState) -> str:
    conf = float(state.get("category_confidence", 0.0))
    if conf < CONF_MIN:
        state["review_reason"] = f"Low category confidence ({conf:.2f} < {CONF_MIN:.2f})"
        return "human_review"
    return "urgency"

def after_urgency(state: TicketState) -> str:
    score = float(state.get("urgency_score", 0.0))
    if score < 0.2 and "down" in state.get("content","").lower():
        state["review_reason"] = "Urgency seems inconsistent with ticket text"
        return "human_review"
    return "route"


def build_graph():
    g = StateGraph(TicketState)

    g.add_node("classify", classifier_node)
    g.add_node("human_review", human_review_node)
    g.add_node("urgency", urgency_node)
    g.add_node("route", router_node)

    g.add_edge(START, "classify")

    # Conditional: after classify -> either human_review OR urgency
    g.add_conditional_edges(
        "classify",
        after_classify,
        {
            "human_review": "human_review",
            "urgency": "urgency",
        },
    )

    # If human review is needed, stop (or you can continue to route triage explicitly)
    g.add_edge("human_review", END)

    g.add_conditional_edges("urgency", after_urgency, {"human_review":"human_review", "route":"route"})


    # Normal path
    g.add_edge("urgency", "route")
    g.add_edge("route", END)

    return g.compile()

def new_state(
        *,
        ticket_id: str,
        subject: str,
        content: str,
        customer_tier: str = "free",
) -> TicketState:
    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "content": content,
        "customer_tier": customer_tier,
        "created_at": datetime.now().isoformat(),
        "events": [],
        "errors": [],
    }


def review_gate(state: TicketState) -> str:
    needs, reason = should_review(state)
    state["needs_review"] = needs
    state["review_reason"] = reason
    add_event(state, "gate", "Review gate evaluated", {"needs_review": needs, "reason": reason})
    return "human_review" if needs else "route"

def human_review_node(state: TicketState) -> TicketState:
    """
    Production version:
      - create a review task in your ticketing system (Jira/Zendesk)
      - store task id in state
      - stop processing until human responds
    For now:
      - mark as pending review and route to triage
    """
    state["route_to"] = "triage_queue"
    state["handler_level"] = "specialist"
    state["routing_reason"] = f"Pending human review: {state.get('review_reason','')}"
    add_event(state, "human_review", "Routed to triage pending human review", {})
    return state
