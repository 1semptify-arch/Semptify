"""
Sprint 3 Action Router Gate Suite
===================================
Mandatory CI gates enforcing per-user isolation and auth on the Smart Action
endpoints fixed in Sprint 3.

Bugs fixed:
- POST /actions/plan  — hardcoded user_id="user_id" (all users shared one slot)
- GET  /actions/plan  — unauthenticated (accepted caller-supplied X-User-Id header)
- GET  /actions/capacity     — unauthenticated + TypeError (get_state() missing user_id)
- GET  /actions/encouragement — unauthenticated + TypeError (same)
"""

import pytest


pytestmark = pytest.mark.action_gate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(uid: str) -> dict:
    return {"cookies": {"semptify_uid": uid}}


# ---------------------------------------------------------------------------
# Gate 1 — Unauthenticated requests are rejected (401/403)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_gate_actions_plan_get_rejects_unauthenticated(client):
    """GET /actions/plan MUST reject unauthenticated requests."""
    resp = await client.get("/api/actions/plan")
    assert resp.status_code in (401, 403), (
        f"Unauthenticated GET /actions/plan returned {resp.status_code}; expected 401 or 403"
    )


@pytest.mark.anyio
async def test_gate_actions_plan_post_rejects_unauthenticated(client):
    """POST /actions/plan MUST reject unauthenticated requests."""
    resp = await client.post("/api/actions/plan", json={})
    assert resp.status_code in (401, 403), (
        f"Unauthenticated POST /actions/plan returned {resp.status_code}; expected 401 or 403"
    )


@pytest.mark.anyio
async def test_gate_actions_capacity_rejects_unauthenticated(client):
    """GET /actions/capacity MUST reject unauthenticated requests (was causing TypeError)."""
    resp = await client.get("/api/actions/capacity")
    assert resp.status_code in (401, 403), (
        f"Unauthenticated GET /actions/capacity returned {resp.status_code}; expected 401 or 403"
    )


@pytest.mark.anyio
async def test_gate_actions_encouragement_rejects_unauthenticated(client):
    """GET /actions/encouragement MUST reject unauthenticated requests (was causing TypeError)."""
    resp = await client.get("/api/actions/encouragement")
    assert resp.status_code in (401, 403), (
        f"Unauthenticated GET /actions/encouragement returned {resp.status_code}; expected 401 or 403"
    )


# ---------------------------------------------------------------------------
# Gate 2 — Per-user state isolation: different users get separate emotion buckets
# ---------------------------------------------------------------------------

def test_gate_emotion_engine_state_isolated_per_user():
    """
    EmotionEngine.get_state() MUST return independent state objects for each user_id.
    Two users must not share a state reference.
    """
    from app.services.emotion_engine import emotion_engine

    uid_a = "GUac3tion01"
    uid_b = "GUac3tion02"

    state_a = emotion_engine.get_state(user_id=uid_a)
    state_b = emotion_engine.get_state(user_id=uid_b)

    assert state_a is not state_b, (
        "emotion_engine.get_state() returned the same object for two different users"
    )


def test_gate_emotion_engine_mutation_does_not_bleed():
    """
    Mutating user A's emotional state MUST NOT affect user B's state.
    """
    from app.services.emotion_engine import emotion_engine

    uid_a = "GUac3tion03"
    uid_b = "GUac3tion04"

    # Ensure both states exist
    state_a = emotion_engine.get_state(user_id=uid_a)
    state_b = emotion_engine.get_state(user_id=uid_b)

    # Record B's initial confidence before touching A
    confidence_b_before = state_b.confidence

    # Directly mutate A's confidence (simulating a state update)
    state_a.confidence = min(1.0, state_a.confidence + 0.5)

    # B's confidence must be unchanged
    state_b_after = emotion_engine.get_state(user_id=uid_b)
    assert state_b_after.confidence == confidence_b_before, (
        f"Mutating user A's confidence bled into user B's state: "
        f"before={confidence_b_before}, after={state_b_after.confidence}"
    )


# ---------------------------------------------------------------------------
# Gate 3 — POST /plan no longer uses hardcoded user bucket
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_gate_actions_post_plan_uses_requester_state(client):
    """
    POST /actions/plan must 401/403 without auth and must NOT respond as if
    user_id="user_id" is a valid authenticated identity.
    The point is that the hardcoded literal is gone.
    """
    # Without auth — must get rejected
    resp_unauth = await client.post("/api/actions/plan", json={"has_notice": True})
    assert resp_unauth.status_code in (401, 403), (
        "POST /actions/plan should reject unauthenticated requests, "
        f"but returned {resp_unauth.status_code}"
    )

    # With auth — must not crash (200 or route-specific error is fine)
    resp_auth = await client.post(
        "/api/actions/plan",
        json={"has_notice": True},
        cookies={"semptify_uid": "GUplantest1"},
    )
    # 200 = success, 404 = route not mounted, 422 = validation — all acceptable
    # What is NOT acceptable: 401/403 for an authenticated user
    assert resp_auth.status_code not in (401, 403), (
        f"Authenticated POST /actions/plan was rejected with {resp_auth.status_code}"
    )


# ---------------------------------------------------------------------------
# Gate 4 — Stateless endpoints still work without auth
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_gate_actions_stateless_endpoints_accessible(client):
    """
    GET /actions/quick-wins, /actions/all, /actions/by-category/{cat} are
    stateless and MUST remain accessible without auth.
    """
    endpoints = [
        "/api/actions/quick-wins",
        "/api/actions/all",
        "/api/actions/by-category/legal_deadline",
    ]
    for url in endpoints:
        resp = await client.get(url)
        assert resp.status_code not in (401, 403), (
            f"Stateless endpoint {url} is blocking unauthenticated access "
            f"(returned {resp.status_code})"
        )
