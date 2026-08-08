"""
Tests for the Semantic Context Engine (Deep OCR Pass 2).

Acceptance: a test document produces correctly labeled, confidence-scored
date objects with trigger phrases.
"""

from app.services.semantic_context_engine import SemanticContextEngine


class TestSemanticContextEngine:
    """Test the rule-based/regex semantic date classifier."""

    def test_extract_returns_labeled_confidence_scored_dates(self):
        """
        Given OCR text with several date mentions and a document-type hint,
        the engine returns a list of SemanticDateResult objects containing
        raw_text, ISO date, semantic_label, trigger_phrase, and confidence.
        """
        text = (
            "NOTICE TO QUIT\n"
            "The lease was signed on 03/15/2024.\n"
            "It is effective as of April 1, 2024.\n"
            "You must vacate the premises no later than May 31, 2024.\n"
            "The notice was issued on 2024-03-10."
        )
        engine = SemanticContextEngine()
        results = engine.extract(text, doc_type="eviction_notice")

        assert isinstance(results, list)
        assert len(results) == 4

        by_label = {r.semantic_label: r for r in results}

        assert "signed" in by_label
        signed = by_label["signed"]
        assert signed.raw_text == "03/15/2024"
        assert signed.date == "2024-03-15"
        assert signed.trigger_phrase == "signed on"
        assert signed.confidence >= 0.5
        assert signed.confidence <= 1.0

        assert "effective" in by_label
        effective = by_label["effective"]
        assert effective.raw_text == "April 1, 2024"
        assert effective.date == "2024-04-01"
        assert effective.trigger_phrase == "effective as of"
        assert effective.confidence >= 0.5

        assert "deadline" in by_label
        deadline = by_label["deadline"]
        assert deadline.raw_text == "May 31, 2024"
        assert deadline.date == "2024-05-31"
        assert deadline.trigger_phrase == "no later than"
        assert deadline.confidence >= 0.5

        assert "issued" in by_label
        issued = by_label["issued"]
        assert issued.raw_text == "2024-03-10"
        assert issued.date == "2024-03-10"
        assert issued.trigger_phrase == "issued on"
        assert issued.confidence >= 0.5

    def test_extract_empty_and_whitespace_returns_empty_list(self):
        """Empty or whitespace text yields no results."""
        engine = SemanticContextEngine()
        assert engine.extract("") == []
        assert engine.extract("   ") == []

    def test_extract_unlabeled_date_returns_mentioned_fallback(self):
        """A date with no domain trigger still returns a low-confidence result."""
        text = "We met on 2024-06-15 and discussed the lease."
        engine = SemanticContextEngine()
        results = engine.extract(text)

        assert len(results) == 1
        result = results[0]
        assert result.raw_text == "2024-06-15"
        assert result.date == "2024-06-15"
        assert result.semantic_label == "mentioned"
        assert result.confidence >= 0.0
