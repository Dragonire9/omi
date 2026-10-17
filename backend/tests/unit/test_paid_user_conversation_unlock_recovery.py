from __future__ import annotations

import pytest
from fastapi import HTTPException

from database import conversations as conversations_db, users as users_db
from models.users import PlanType, Subscription, SubscriptionStatus
from routers import conversations as routes

UID = "test-user-unlock-recovery"
CONV_LOCKED_1 = "conv-locked-1"
CONV_LOCKED_2 = "conv-locked-2"
CONV_UNLOCKED = "conv-unlocked-3"


def _setup_mock_db(monkeypatch, *, is_paid: bool = False):
    mock_conversations = {
        CONV_LOCKED_1: {
            "id": CONV_LOCKED_1,
            "is_locked": True,
            "deleted": False,
            "structured": {"title": "Historical Meeting", "overview": "Overview 1"},
        },
        CONV_LOCKED_2: {
            "id": CONV_LOCKED_2,
            "is_locked": True,
            "deleted": False,
            "structured": {"title": "Older Strategy", "overview": "Overview 2"},
        },
        CONV_UNLOCKED: {
            "id": CONV_UNLOCKED,
            "is_locked": False,
            "deleted": False,
            "structured": {"title": "Active Call", "overview": "Overview 3"},
        },
    }

    def mock_get_conversation(uid, conversation_id, **kwargs):
        return mock_conversations.get(conversation_id)

    updated_conversations = {}

    def mock_update_conversation(uid, conversation_id, patch):
        if conversation_id in mock_conversations:
            mock_conversations[conversation_id].update(patch)
            updated_conversations[conversation_id] = patch

    plan = PlanType.unlimited if is_paid else PlanType.basic
    mock_subscription = Subscription(
        plan=plan,
        status=SubscriptionStatus.active,
        billing_cycle="monthly",
        current_period_end=None,
    )

    monkeypatch.setattr(routes.conversations_db, "get_conversation", mock_get_conversation)
    monkeypatch.setattr(routes.conversations_db, "update_conversation", mock_update_conversation)
    monkeypatch.setattr(routes.conversations_db, "is_soft_deleted", lambda c: False)
    monkeypatch.setattr(routes.conversations_db, "is_visible_conversation", lambda c, **k: True)
    monkeypatch.setattr(routes.users_db, "get_user_valid_subscription", lambda uid, **k: mock_subscription)
    monkeypatch.setattr(conversations_db, "get_conversation", mock_get_conversation)
    monkeypatch.setattr(conversations_db, "update_conversation", mock_update_conversation)
    monkeypatch.setattr(users_db, "get_user_valid_subscription", lambda uid, **k: mock_subscription)

    return mock_conversations, updated_conversations


def test_free_user_accessing_locked_conversation_raises_402(monkeypatch):
    _setup_mock_db(monkeypatch, is_paid=False)

    with pytest.raises(HTTPException) as exc_info:
        routes._get_valid_conversation_by_id(UID, CONV_LOCKED_1)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail == "A paid plan is required to access this conversation."


def test_paid_user_accessing_locked_conversation_heals_and_returns_conversation(monkeypatch):
    mock_conversations, updated = _setup_mock_db(monkeypatch, is_paid=True)

    result = routes._get_valid_conversation_by_id(UID, CONV_LOCKED_1)
    assert result["id"] == CONV_LOCKED_1
    assert result["is_locked"] is False
    assert updated.get(CONV_LOCKED_1) == {"is_locked": False}
    assert mock_conversations[CONV_LOCKED_1]["is_locked"] is False


def test_paid_user_listing_conversations_heals_locked_rows(monkeypatch):
    mock_conversations, updated = _setup_mock_db(monkeypatch, is_paid=True)
    rows = [dict(mock_conversations[CONV_LOCKED_1]), dict(mock_conversations[CONV_UNLOCKED])]

    routes._heal_locked_conversations_if_paid(UID, rows)
    assert rows[0]["is_locked"] is False
    assert rows[1]["is_locked"] is False
    assert updated.get(CONV_LOCKED_1) == {"is_locked": False}


def test_free_user_listing_conversations_leaves_locked_rows_intact(monkeypatch):
    mock_conversations, updated = _setup_mock_db(monkeypatch, is_paid=False)
    rows = [dict(mock_conversations[CONV_LOCKED_1])]

    routes._heal_locked_conversations_if_paid(UID, rows)
    assert rows[0]["is_locked"] is True
    assert CONV_LOCKED_1 not in updated


def test_heal_locked_conversations_for_paid_subscriber(monkeypatch):
    mock_conversations, updated = _setup_mock_db(monkeypatch, is_paid=True)
    rows = [dict(mock_conversations[CONV_LOCKED_1])]

    routes._heal_locked_conversations_if_paid(UID, rows)
    assert rows[0]["is_locked"] is False
    assert updated.get(CONV_LOCKED_1) == {"is_locked": False}


def test_heal_locked_conversations_ignored_for_free_subscriber(monkeypatch):
    mock_conversations, updated = _setup_mock_db(monkeypatch, is_paid=False)
    rows = [dict(mock_conversations[CONV_LOCKED_1])]

    routes._heal_locked_conversations_if_paid(UID, rows)
    assert rows[0]["is_locked"] is True
    assert CONV_LOCKED_1 not in updated
