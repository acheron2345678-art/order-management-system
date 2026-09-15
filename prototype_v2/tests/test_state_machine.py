from app.models import OrderStatus
from app.services.order_service import ALLOWED_TRANSITIONS


def test_happy_path_transitions():
    assert OrderStatus.CONFIRMED in ALLOWED_TRANSITIONS[OrderStatus.PENDING]
    assert OrderStatus.PREPARING in ALLOWED_TRANSITIONS[OrderStatus.CONFIRMED]
    assert OrderStatus.OUT_FOR_DELIVERY in ALLOWED_TRANSITIONS[OrderStatus.PREPARING]
    assert OrderStatus.DELIVERED in ALLOWED_TRANSITIONS[OrderStatus.OUT_FOR_DELIVERY]


def test_terminal_states_are_closed():
    assert ALLOWED_TRANSITIONS[OrderStatus.DELIVERED] == set()
    assert ALLOWED_TRANSITIONS[OrderStatus.CANCELLED] == set()
