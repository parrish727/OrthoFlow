"""The one demo practice (DEMO — Brightsmile Orthodontics) shown to prospects.

Simulated behavior (fake payer responses, simulated claim adjudication, demo auto-replies,
mock clearinghouse results) is allowed for this practice only. Every real customer practice gets
real behavior or a clear "not available yet" message, never fabricated data.
"""
import uuid

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")


def is_demo_practice(practice_id) -> bool:
    return str(practice_id) == str(DEMO_PRACTICE_ID)
