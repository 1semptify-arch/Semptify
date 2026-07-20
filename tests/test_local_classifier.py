"""Smoke tests for the local document classifier."""

from app.services.local_classifier import predict


def test_empty_unknown():
    """No filename and no content should return unknown."""
    assert predict(None, "") == "unknown"
    assert predict(b"", "") == "unknown"


def test_filename_only_classifications():
    """Classifier can label documents from filenames alone."""
    assert predict(b"", "lease_agreement.pdf") == "lease"
    assert predict(b"", "notice_to_quit.pdf") == "notice"
    assert predict(b"", "repair_photo.jpg") == "photo"
    assert predict(b"", "january_rent_receipt.pdf") == "invoice"
    assert predict(b"", "landlord_email.txt") == "communication"
    assert predict(b"", "evidence_packet.pdf") == "evidence"


def test_random_filename_unknown():
    """Random filenames with no content should return unknown."""
    assert predict(b"", "document.pdf") == "unknown"
    assert predict(b"", "scan_001.pdf") == "unknown"


def test_content_classifications():
    """Classifier can label documents from content keywords."""
    assert predict(b"This is a lease agreement between landlord and tenant.", "doc.pdf") == "lease"
    assert predict(b"Notice to vacate the premises within 30 days.", "doc.pdf") == "notice"
    assert predict(b"Repair request: the roof is leaking and there is mold.", "doc.pdf") == "evidence"
    assert predict(b"Invoice number 123 - amount due $1,200.", "doc.pdf") == "invoice"
    assert predict(b"Dear landlord, Sincerely, tenant.", "doc.pdf") == "communication"


def test_photo_label_from_filename():
    """Image extensions and photo keywords map to photo."""
    assert predict(b"\x89PNG\r\n\x1a\n", "kitchen_mold.png") == "photo"
    assert predict(b"", "screenshot_damage.jpg") == "photo"
