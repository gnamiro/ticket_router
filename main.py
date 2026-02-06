from state import new_state

if __name__ == "__main__":
    s = new_state(
        ticket_id="TCK-1001",
        subject="Charged twice this month",
        content="Hi, I see two charges on my credit card for January. Please fix ASAP.",
        customer_tier="pro",
        channel="email",
    )
    print(s)
