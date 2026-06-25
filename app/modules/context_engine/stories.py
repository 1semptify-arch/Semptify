"""Context Engine stories — tenant story submission + moderation.

Story frame: `avoided_court` is the hero — documentation is the win.
Stories are anonymized + moderated before publishing.
"""

from typing import List, Optional

from sqlalchemy import select, and_

from app.core.database import get_db_session
from app.core.utc import utc_now
from app.modules.context_engine.models import TenantStory


VALID_OUTCOMES = {"avoided_court", "won_court", "settled", "lost_court", "ongoing"}


async def submit_story(
    subject: str,
    title: str,
    body: str,
    jurisdiction: str = "MN",
    outcome: str = "avoided_court",
    submitted_by: Optional[str] = None,
) -> TenantStory:
    """Submit a new tenant story for moderation. Anonymized by default."""
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of: {', '.join(sorted(VALID_OUTCOMES))}")
    story = TenantStory(
        subject=subject,
        jurisdiction=jurisdiction,
        title=title,
        body=body,
        outcome=outcome,
        is_anonymized=True,
        is_moderated=False,
        is_published=False,
        submitted_by=submitted_by,
    )
    async with get_db_session() as db:
        db.add(story)
        await db.commit()
        await db.refresh(story)
    return story


async def moderate_story(
    story_id: int,
    moderated_by: str,
    publish: bool,
    title: Optional[str] = None,
    body: Optional[str] = None,
) -> TenantStory:
    """Moderate a story — optionally edit, then mark moderated + publish/unpublish."""
    async with get_db_session() as db:
        result = await db.execute(
            select(TenantStory).where(TenantStory.id == story_id)
        )
        story = result.scalars().first()
        if not story:
            raise FileNotFoundError(f"Story {story_id} not found")
        if title is not None:
            story.title = title
        if body is not None:
            story.body = body
        story.is_moderated = True
        story.is_published = publish
        story.moderated_by = moderated_by
        story.moderated_at = utc_now().replace(tzinfo=None)
        await db.commit()
        await db.refresh(story)
        return story


async def get_published_stories(
    subject: Optional[str] = None,
    jurisdiction: str = "MN",
    limit: int = 10,
) -> List[TenantStory]:
    """Get published, moderated stories for a subject."""
    async with get_db_session() as db:
        conditions = [
            TenantStory.is_published.is_(True),
            TenantStory.is_moderated.is_(True),
            TenantStory.jurisdiction == jurisdiction,
        ]
        if subject:
            conditions.append(TenantStory.subject == subject)
        stmt = select(TenantStory).where(and_(*conditions)).order_by(
            TenantStory.moderated_at.desc()
        ).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_pending_stories(limit: int = 50) -> List[TenantStory]:
    """Get stories pending moderation."""
    async with get_db_session() as db:
        stmt = select(TenantStory).where(
            TenantStory.is_moderated.is_(False)
        ).order_by(TenantStory.created_at.asc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_story(story_id: int) -> Optional[TenantStory]:
    async with get_db_session() as db:
        result = await db.execute(
            select(TenantStory).where(TenantStory.id == story_id)
        )
        return result.scalars().first()
