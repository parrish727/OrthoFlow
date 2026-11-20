"""Simulated behavior is for the demo practice only."""
import uuid

from app.core.demo import DEMO_PRACTICE_ID, is_demo_practice
from app.seeds import demo_flow


def test_demo_practice_identity():
    assert is_demo_practice(DEMO_PRACTICE_ID)
    assert is_demo_practice(str(DEMO_PRACTICE_ID))
    assert not is_demo_practice(uuid.uuid4())
    assert not is_demo_practice("")


def test_seed_uses_the_same_demo_id():
    assert demo_flow.DEMO_PRACTICE_ID == DEMO_PRACTICE_ID
