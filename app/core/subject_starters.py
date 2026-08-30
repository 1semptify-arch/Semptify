"""Concrete subject starters for AI-assist and home surfaces.

These are plain-language, tenant-crisis prompts that help someone who is
stressed find the right starting point without having to know the right
words first. They are facts about a tenant's situation, not legal advice.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectStarter:
    """One clickable subject starter."""

    text: str
    href: str


# Pillar routes are not yet in the SSOT navigation registry, so these use the
# same hardcoded /gui/* paths that the rest of the GUI is currently using.
# When the SSOT registration pass lands, this list should be updated to use
# navigation.get_stage(...).path.
def get_subject_starters() -> list[SubjectStarter]:
    """Return the canonical list of subject starter chips."""
    return [
        SubjectStarter("My landlord isn't making repairs", "/gui/act"),
        SubjectStarter("I got an eviction notice", "/gui/act"),
        SubjectStarter("My security deposit wasn't returned", "/gui/act"),
        SubjectStarter("My landlord entered without notice", "/gui/record"),
        SubjectStarter("I have a question about rent increases", "/law-library"),
        SubjectStarter("I'm being retaliated against", "/gui/act"),
        SubjectStarter("I need to break my lease", "/law-library"),
        SubjectStarter("What are my rights as a tenant?", "/law-library"),
        SubjectStarter("How do I document a problem?", "/gui/record"),
    ]


def get_subject_starter_texts() -> list[str]:
    """Convenience helper for non-HTML consumers."""
    return [s.text for s in get_subject_starters()]
