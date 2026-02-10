# run.py
from graph import build_graph, new_state

if __name__ == "__main__":
    app = build_graph()

    state = new_state(
        ticket_id="TCK-2001",
        subject="Production is down after last update",
        content="Our app is returning 500 errors for all users. We deployed 30 minutes ago. Need help ASAP.",
        customer_tier="enterprise",
    )

    final_state = app.invoke(state)

    print("\n--- FINAL OUTPUT ---")
    for k in ["category", "category_confidence", "urgency_level", "route_to", "handler_level"]:
        print(f"{k}: {final_state.get(k)}")

    print("\n--- ROUTING REASON ---")
    print(final_state.get("routing_reason"))

    print("\n--- EVENTS ---")
    for e in final_state.get("events", []):
        print(f"[{e['step']}] {e['message']} -> {e['data']}")
