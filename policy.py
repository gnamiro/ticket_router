CATEGORY_CONF_MIN = 0.70

# When to require human review
def should_review(state) -> tuple[bool, str]:
    conf = state.get("category_confidence", 0.0)
    urgency = state.get("urgency_level", "medium")
    tier = state.get("customer_tier", "free")

    if conf < CATEGORY_CONF_MIN:
        return True, f"Low category confidence ({conf:.2f})"

    # Extra safety: critical/high urgency + important customers
    if urgency in ("high", "critical") and tier in ("pro", "enterprise"):
        return True, f"High urgency ({urgency}) for {tier} customer"

    return False, ""
