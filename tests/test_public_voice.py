"""Tests for the public-voice civic lane (P6).

Covers: anonymous story submit/list, the elevation-gated review-and-respond
API for voice posts, tool requests, and stories, and the gate itself.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.admin_elevation import ELEVATION_COOKIE_NAME, issue_elevation_cookie
from app.main import app


def _elev_client():
    """AsyncClient carrying a valid admin elevation cookie."""
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={ELEVATION_COOKIE_NAME: issue_elevation_cookie("GUADMIN001")},
    )


class TestStorySubmit:
    @pytest.mark.asyncio
    async def test_story_submit_ok(self, client):
        response = await client.post(
            "/api/story",
            json={
                "subject": "repairs",
                "title": "The winter the heat stayed off",
                "body": "Three months of emails. Space heaters. It resolved without court.",
                "outcome": "avoided_court",
                "jurisdiction": "mn",
            },
        )
        assert response.status_code == 200
        assert response.json()["received"] is True

    @pytest.mark.asyncio
    async def test_story_rejects_bad_subject(self, client):
        response = await client.post(
            "/api/story",
            json={"subject": "my landlord bob", "title": "t", "body": "b"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_story_rejects_empty_body(self, client):
        response = await client.post(
            "/api/story",
            json={"subject": "rent", "title": "t", "body": "   "},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_story_rejects_bad_jurisdiction(self, client):
        response = await client.post(
            "/api/story",
            json={"subject": "rent", "title": "t", "body": "x", "jurisdiction": "Minnesota"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_stories_list_empty(self, client):
        response = await client.get("/api/stories")
        assert response.status_code == 200
        data = response.json()
        assert data["stories"] == []
        assert data["awaiting_review"] == 0


class TestReviewGate:
    @pytest.mark.asyncio
    async def test_pending_requires_elevation(self, client):
        response = await client.get("/admin/api/public-forms/pending")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_review_post_requires_elevation(self, client):
        response = await client.post(
            "/admin/api/public-forms/voice-posts/abc",
            json={"action": "publish"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pending_with_elevation(self):
        async with _elev_client() as client:
            response = await client.get("/admin/api/public-forms/pending")
        assert response.status_code == 200
        data = response.json()
        assert "voice_posts" in data
        assert "tool_requests" in data
        assert "stories" in data
        assert "published" in data


class TestVoicePostReviewFlow:
    @pytest.mark.asyncio
    async def test_submit_answer_publish(self):
        # Anonymous submit
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            response = await anon.post(
                "/api/voice-post",
                json={"kind": "question", "message": "Does the bill cover late fees?"},
            )
            assert response.status_code == 200

        # Review lane sees it pending
        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            assert len(pending["voice_posts"]) == 1
            post_id = pending["voice_posts"][0]["id"]

            # Answer + publish
            response = await admin.post(
                f"/admin/api/public-forms/voice-posts/{post_id}",
                json={
                    "action": "answer",
                    "response_text": "The draft covers fees in section 4.",
                    "responder_label": "Semptify",
                },
            )
            assert response.status_code == 200

        # Public list now shows it with the answer
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            posts = (await anon.get("/api/voice-posts")).json()["posts"]
            assert len(posts) == 1
            assert posts[0]["response"] == "The draft covers fees in section 4."
            assert posts[0]["responder"] == "Semptify"
            assert posts[0]["status"] == "answered"

    @pytest.mark.asyncio
    async def test_decline_keeps_off_board(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            await anon.post(
                "/api/voice-post",
                json={"kind": "opinion", "message": "My landlord is named Steve and lives at 5 Oak St"},
            )

        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            post_id = pending["voice_posts"][0]["id"]
            response = await admin.post(
                f"/admin/api/public-forms/voice-posts/{post_id}",
                json={"action": "decline"},
            )
            assert response.status_code == 200

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            posts = (await anon.get("/api/voice-posts")).json()["posts"]
            assert posts == []

    @pytest.mark.asyncio
    async def test_answer_requires_text(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            await anon.post(
                "/api/voice-post",
                json={"kind": "question", "message": "q"},
            )
        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            post_id = pending["voice_posts"][0]["id"]
            response = await admin.post(
                f"/admin/api/public-forms/voice-posts/{post_id}",
                json={"action": "answer"},
            )
            assert response.status_code == 422


class TestVoicePostFlag:
    """Reader flag/report control — feeds the same review queue."""

    @pytest.fixture(autouse=True)
    def _reset_rate_limiter(self):
        """Fresh limiter window per test — the shared in-memory slowapi
        storage would otherwise bleed hits across tests in one process."""
        from app.core.rate_limit import limiter

        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "reset"):
            storage.reset()
        yield

    async def _publish_post(self) -> str:
        """Seed one published board post directly — the submit and publish
        endpoints are covered elsewhere; seeding keeps the flag tests off
        the shared /api/voice-post rate limiter."""
        import uuid

        from app.core.database import get_db_session
        from app.models.models import VoicePost

        post_id = str(uuid.uuid4())
        async with get_db_session() as db:
            db.add(
                VoicePost(
                    id=post_id,
                    kind="opinion",
                    post_text="The bill should go further on deposits.",
                    status="published",
                    is_published=True,
                )
            )
        return post_id

    async def _pending_post_id(self) -> str:
        """Seed one still-unpublished post and return its id."""
        import uuid

        from app.core.database import get_db_session
        from app.models.models import VoicePost

        post_id = str(uuid.uuid4())
        async with get_db_session() as db:
            db.add(
                VoicePost(
                    id=post_id,
                    kind="question",
                    post_text="Unpublished post",
                )
            )
        return post_id

    @pytest.mark.asyncio
    async def test_flag_published_post(self):
        post_id = await self._publish_post()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            response = await anon.post(
                f"/api/voice-posts/{post_id}/flag",
                json={"reason": "spam"},
            )
            assert response.status_code == 200
            assert response.json()["flagged"] is True

        # The flag lands in the same review queue with reason detail.
        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            flagged = [p for p in pending["voice_posts"] if p["id"] == post_id]
            assert len(flagged) == 1
            assert flagged[0]["flag_count"] == 1
            assert flagged[0]["flag_reasons"] == {"spam": 1}
            assert flagged[0]["is_published"] is True

        # Flagging does not pull the post off the board — review does.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            posts = (await anon.get("/api/voice-posts")).json()["posts"]
            assert [p["id"] for p in posts] == [post_id]

    @pytest.mark.asyncio
    async def test_flag_counts_and_reasons_accumulate(self):
        post_id = await self._publish_post()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            for reason in ("spam", "other", "spam"):
                response = await anon.post(
                    f"/api/voice-posts/{post_id}/flag",
                    json={"reason": reason},
                )
                assert response.status_code == 200

        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            flagged = [p for p in pending["voice_posts"] if p["id"] == post_id]
            assert flagged[0]["flag_count"] == 3
            assert flagged[0]["flag_reasons"] == {"spam": 2, "other": 1}

    @pytest.mark.asyncio
    async def test_flag_unpublished_post_404(self):
        post_id = await self._pending_post_id()

        # Flagging a post that isn't on the board yet — or one that
        # doesn't exist — both 404 without leaking which is which.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            response = await anon.post(
                f"/api/voice-posts/{post_id}/flag",
                json={"reason": "spam"},
            )
            assert response.status_code == 404
            response = await anon.post(
                "/api/voice-posts/nonexistent-id/flag",
                json={"reason": "spam"},
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_flag_rejects_bad_reason(self):
        post_id = await self._publish_post()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            response = await anon.post(
                f"/api/voice-posts/{post_id}/flag",
                json={"reason": "because i said so"},
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_dismiss_clears_flags_keeps_post(self):
        post_id = await self._publish_post()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            await anon.post(f"/api/voice-posts/{post_id}/flag", json={"reason": "hate"})

        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            assert any(p["id"] == post_id for p in pending["voice_posts"])
            response = await admin.post(
                f"/admin/api/public-forms/voice-posts/{post_id}",
                json={"action": "dismiss"},
            )
            assert response.status_code == 200

            # Flag resolved — post drops back out of the review queue…
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            assert all(p["id"] != post_id for p in pending["voice_posts"])

        # …but stays published on the board.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            posts = (await anon.get("/api/voice-posts")).json()["posts"]
            assert [p["id"] for p in posts] == [post_id]
            assert posts[0]["status"] == "published"

    @pytest.mark.asyncio
    async def test_review_action_clears_flags(self):
        post_id = await self._publish_post()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            await anon.post(f"/api/voice-posts/{post_id}/flag", json={"reason": "threat"})

        async with _elev_client() as admin:
            await admin.post(
                f"/admin/api/public-forms/voice-posts/{post_id}",
                json={"action": "unpublish"},
            )
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            row = [p for p in pending["voice_posts"] if p["id"] == post_id]
            assert len(row) == 1  # unpublished, so still in the queue…
            assert row[0]["flag_count"] == 0  # …but the flag is resolved


class TestToolRequestReviewFlow:
    @pytest.mark.asyncio
    async def test_submit_answer_publish(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            response = await anon.post(
                "/api/tool-request",
                json={"message": "A checklist for move-out photos"},
            )
            assert response.status_code == 200

        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            assert len(pending["tool_requests"]) == 1
            req_id = pending["tool_requests"][0]["id"]

            response = await admin.post(
                f"/admin/api/public-forms/tool-requests/{req_id}",
                json={"action": "answer", "response_text": "On the list — the move-out guide covers this."},
            )
            assert response.status_code == 200

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            reqs = (await anon.get("/api/tool-requests")).json()["requests"]
            assert len(reqs) == 1
            assert reqs[0]["response"].startswith("On the list")


class TestStoryReviewFlow:
    @pytest.mark.asyncio
    async def test_submit_moderate_publish(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            response = await anon.post(
                "/api/story",
                json={
                    "subject": "deposit",
                    "title": "The deposit that never came back",
                    "body": "Moved out in May. Heard nothing until August.",
                    "jurisdiction": "WI",
                },
            )
            assert response.status_code == 200

        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            assert len(pending["stories"]) == 1
            story_id = pending["stories"][0]["id"]

            # Publish with an anonymizing title edit
            response = await admin.post(
                f"/admin/api/public-forms/stories/{story_id}",
                json={"action": "publish", "title": "A deposit that never came back"},
            )
            assert response.status_code == 200

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            stories = (await anon.get("/api/stories")).json()["stories"]
            assert len(stories) == 1
            assert stories[0]["title"] == "A deposit that never came back"
            assert stories[0]["jurisdiction"] == "WI"

    @pytest.mark.asyncio
    async def test_unpublish_pulls_story(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            await anon.post(
                "/api/story",
                json={"subject": "other", "title": "t", "body": "b"},
            )
        async with _elev_client() as admin:
            pending = (await admin.get("/admin/api/public-forms/pending")).json()
            story_id = pending["stories"][0]["id"]
            await admin.post(
                f"/admin/api/public-forms/stories/{story_id}",
                json={"action": "publish"},
            )
            await admin.post(
                f"/admin/api/public-forms/stories/{story_id}",
                json={"action": "unpublish"},
            )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
            stories = (await anon.get("/api/stories")).json()["stories"]
            assert stories == []

    @pytest.mark.asyncio
    async def test_missing_story_404(self):
        async with _elev_client() as admin:
            response = await admin.post(
                "/admin/api/public-forms/stories/99999",
                json={"action": "publish"},
            )
            assert response.status_code == 404
