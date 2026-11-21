"""Co-view session tests (legal-ui matrix G6.1-G6.7).

Covers the REST contract: create/join/state/revoke/end/log and token
rules (wrong-session, expired, dead-after-end, revoked-cannot-rejoin).
WebSocket sync is verified live (see task handoff) — the ws channel is
exercised end-to-end in the manual verification for this task.
"""

import time

import pytest


def _signed(role: str) -> str:
    from app.core.user_id import generate_user_id
    from app.core.cookie_auth import sign_user_id
    return sign_user_id(generate_user_id("google_drive", role))


def _cookie(uid: str) -> dict:
    return {"semptify_uid": uid}


async def test_coview_session_lifecycle(client):
    tenant = _signed("tenant")
    legal = _signed("legal")
    legal_raw = legal.split(".")[0]

    # G6.1 — either side may propose; create returns a short-lived join token
    r = await client.post("/api/coview/sessions", json={"doc_ref": "doc.pdf"},
                          cookies=_cookie(tenant))
    assert r.status_code == 200
    sid = r.json()["session_id"]
    token = r.json()["join_token"]

    # Guest joins with token (revived pro-role user)
    r = await client.post("/api/coview/join", json={"session_id": sid, "token": token},
                          cookies=_cookie(legal))
    assert r.status_code == 200
    people = r.json()["session"]["participants"]
    assert {p["role"] for p in people} == {"tenant", "legal"}  # participants visible

    # Bad token / wrong session rejected
    r = await client.post("/api/coview/join",
                          json={"session_id": sid, "token": token[:-4] + "beef"},
                          cookies=_cookie(legal))
    assert r.status_code == 403
    r = await client.post("/api/coview/join",
                          json={"session_id": "cv_other", "token": token},
                          cookies=_cookie(legal))
    assert r.status_code in (403, 404)

    # G6.4 — tenant (initiator) revokes the legal guest
    r = await client.post(f"/api/coview/sessions/{sid}/participants/{legal_raw}/revoke",
                          cookies=_cookie(tenant))
    assert r.status_code == 200
    # Revoked user cannot rejoin even with a fresh token
    r = await client.post(f"/api/coview/sessions/{sid}/invite", cookies=_cookie(tenant))
    tok2 = r.json()["join_token"]
    r = await client.post("/api/coview/join", json={"session_id": sid, "token": tok2},
                          cookies=_cookie(legal))
    assert r.status_code == 403

    # Guest cannot end; host can (G6.3)
    r = await client.post(f"/api/coview/sessions/{sid}/end", cookies=_cookie(legal))
    assert r.status_code == 403
    r = await client.post(f"/api/coview/sessions/{sid}/end", cookies=_cookie(tenant))
    assert r.status_code == 200
    # G6.3 — join token dead immediately after end
    r = await client.post("/api/coview/join", json={"session_id": sid, "token": tok2},
                          cookies=_cookie(legal))
    assert r.status_code == 404

    # G6.6 — session log: who/when/which doc, never content
    r = await client.get(f"/api/coview/sessions/{sid}/log", cookies=_cookie(tenant))
    assert r.status_code == 200
    events = [e["event"] for e in r.json()["events"]]
    assert "session_open" in events and "join" in events
    assert "revoke" in events and "session_end" in events
    for e in r.json()["events"]:
        assert "text" not in e and "content" not in e


def test_coview_token_expiry():
    from app.modules.coview.router import _mint_token, _check_token
    tok = _mint_token("cv_x", "guest", ttl_s=-1)  # already expired
    with pytest.raises(Exception):
        _check_token("cv_x", tok)
