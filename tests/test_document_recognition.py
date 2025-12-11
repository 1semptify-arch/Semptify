"""
Test suite for the advanced document recognition engine.
Tests multi-layered analysis: structural, contextual, keyword, entity extraction, and reasoning.
"""

import pytest
from app.services.document_recognition import (
    recognize_document,
    DocumentRecognitionEngine,
    DocumentType,
    DocumentCategory,
    RecognitionResult,
)


class TestDocumentRecognitionEngine:
    """Test the document recognition engine."""
    
    @pytest.fixture
    def engine(self):
        return DocumentRecognitionEngine()
    
    # === COURT DOCUMENT TESTS ===
    
    def test_recognize_summons(self):
        """Test recognition of court summons."""
        text = """
        STATE OF MINNESOTA                    DISTRICT COURT
        COUNTY OF HENNEPIN                    FOURTH JUDICIAL DISTRICT
        
        ABC Property Management LLC,
            Plaintiff,                        Case No: 27-CV-25-3456
        vs.
        John Smith,
            Defendant.
        
                                SUMMONS
        
        You are hereby summoned and required to serve upon Plaintiff's attorney 
        an Answer to the Complaint within twenty (20) days.
        
        If you fail to do so, judgment by default will be taken against you.
        
        This is an Unlawful Detainer Action seeking recovery of premises.
        
        NOTICE: You must respond by January 15, 2025.
        
        Dated: December 28, 2024
        """
        
        result = recognize_document(text, "summons.pdf")
        
        assert result.doc_type == DocumentType.SUMMONS
        assert result.category == DocumentCategory.COURT
        assert result.confidence > 0.5
        assert "summons" in result.title.lower()
        assert len(result.case_numbers) > 0
        assert result.case_numbers[0].value == "27-CV-25-3456"
    
    def test_recognize_judgment(self):
        """Test recognition of court judgment."""
        text = """
        STATE OF MINNESOTA                    DISTRICT COURT
        COUNTY OF RAMSEY                      Case No: 62-CV-25-1234
        
        Gold Star Apartments LLC,
            Plaintiff,
        vs.
        Sarah Thompson,
            Defendant.
        
                                JUDGMENT
        
        IT IS HEREBY ORDERED AND ADJUDGED that:
        
        1. Judgment is entered for Plaintiff.
        2. Defendant shall pay $4,850.00.
        3. A Writ of Restitution may issue.
        
        Dated: January 10, 2025
        """
        
        result = recognize_document(text, "judgment.pdf")
        
        assert result.doc_type == DocumentType.JUDGMENT
        assert result.category == DocumentCategory.COURT
        assert result.confidence > 0.5
        assert "judgment" in result.title.lower()
        assert result.urgency_level in ("high", "critical")
    
    def test_recognize_writ(self):
        """Test recognition of writ of restitution."""
        text = """
        WRIT OF RESTITUTION
        
        Case No: 27-CV-25-9999
        
        To the Sheriff of Hennepin County:
        
        You are hereby commanded to remove the defendant from the premises
        located at 123 Main Street, Minneapolis, MN.
        
        Execute this writ within 14 days.
        """
        
        result = recognize_document(text, "writ.pdf")
        
        assert result.doc_type == DocumentType.WRIT
        assert result.category == DocumentCategory.COURT
        assert result.urgency_level == "critical"
    
    # === LANDLORD DOCUMENT TESTS ===
    
    def test_recognize_lease(self):
        """Test recognition of lease agreement."""
        text = """
        RESIDENTIAL LEASE AGREEMENT
        
        This Lease Agreement is entered into by and between:
        
        LANDLORD: ABC Properties Inc.
        TENANT: John Doe
        
        PROPERTY ADDRESS: 123 Oak Street, Minneapolis, MN
        
        TERM OF LEASE: 12 months beginning June 1, 2024
        MONTHLY RENT: $1,500.00
        SECURITY DEPOSIT: $1,500.00
        
        LATE FEE: $75.00 if rent not received by the 5th.
        """
        
        result = recognize_document(text, "lease.pdf")
        
        assert result.doc_type == DocumentType.LEASE
        assert result.category == DocumentCategory.LANDLORD
        assert result.confidence > 0.7
        assert len(result.parties) >= 2  # Landlord and tenant
        assert len(result.amounts) >= 1
    
    def test_recognize_eviction_notice(self):
        """Test recognition of eviction notice."""
        text = """
        EVICTION NOTICE - PAY OR QUIT
        
        To: Jane Doe
        Address: 456 Oak Street, St. Paul, MN
        
        You have failed to pay rent of $1,200.00 due on January 1, 2025.
        
        PURSUANT TO MINNESOTA STATUTE 504B.135, you have 14 DAYS to pay
        or vacate the premises.
        
        Landlord: Robert Johnson
        """
        
        result = recognize_document(text, "eviction_notice.pdf")
        
        assert result.doc_type in (DocumentType.EVICTION_NOTICE, DocumentType.NOTICE_TO_QUIT)
        assert result.category == DocumentCategory.LANDLORD
        assert "504B" in str(result.key_terms) or "504B.135" in str(result.key_terms)
    
    def test_recognize_notice_to_quit(self):
        """Test recognition of notice to quit."""
        text = """
        NOTICE TO QUIT
        
        14-DAY PAY OR QUIT NOTICE
        
        You are hereby notified to pay the rent owed or quit and vacate
        the premises within 14 days.
        
        Amount Due: $2,400.00
        """
        
        result = recognize_document(text, "notice.pdf")
        
        assert result.doc_type in (DocumentType.EVICTION_NOTICE, DocumentType.NOTICE_TO_QUIT)
        assert "quit" in result.title.lower() or "eviction" in result.title.lower()
    
    # === FINANCIAL DOCUMENT TESTS ===
    
    def test_recognize_receipt(self):
        """Test recognition of payment receipt."""
        text = """
        RENT RECEIPT
        
        Date: January 3, 2025
        Receipt #: 2025-0103
        
        RECEIVED FROM: David Chen
        
        Amount Paid: $1,350.00
        Payment Method: Check
        
        Thank you for your payment.
        """
        
        result = recognize_document(text, "receipt.pdf")
        
        assert result.doc_type == DocumentType.RECEIPT
        assert result.category == DocumentCategory.FINANCIAL
        assert result.confidence > 0.8
        assert len(result.amounts) >= 1
    
    # === ENTITY EXTRACTION TESTS ===
    
    def test_extract_dates(self, engine):
        """Test date extraction with context."""
        text = """
        Filed: December 28, 2024
        Hearing scheduled for January 15, 2025
        Deadline to respond: 01/10/2025
        Lease begins: 2024-06-01
        """
        
        result = engine.recognize(text, "test.pdf")
        
        assert len(result.dates) >= 3
        # Check that context labels are meaningful
        date_labels = [d.context_label for d in result.dates]
        assert any("Deadline" in label or "Respond" in label or "Court" in label 
                   for label in date_labels)
    
    def test_extract_amounts(self, engine):
        """Test amount extraction with context."""
        text = """
        Rent due: $1,200.00
        Late fee: $50.00
        Security deposit: $1,200.00
        Judgment amount: $4,500.00
        Attorney fees: $500.00
        """
        
        result = engine.recognize(text, "test.pdf")
        
        assert len(result.amounts) >= 3
        amount_labels = [a.context_label for a in result.amounts]
        assert any("Rent" in label or "Late Fee" in label or "Security" in label 
                   for label in amount_labels)
    
    def test_extract_case_number(self, engine):
        """Test case number extraction."""
        text = """
        Case No: 27-CV-25-3456
        File Number: 62-CV-25-1234
        """
        
        result = engine.recognize(text, "test.pdf")
        
        assert len(result.case_numbers) >= 1
        case_nums = [c.value for c in result.case_numbers]
        assert any("27-CV-25-3456" in num or "62-CV-25-1234" in num 
                   for num in case_nums)
    
    def test_extract_addresses(self, engine):
        """Test address extraction."""
        text = """
        Property located at: 123 Main Street, Apt 4B
        Landlord address: 456 Corporate Blvd
        """
        
        result = engine.recognize(text, "test.pdf")
        
        assert len(result.addresses) >= 1
        assert any("123 Main Street" in a.value for a in result.addresses)
    
    def test_extract_parties(self, engine):
        """Test party extraction."""
        text = """
        LANDLORD: ABC Properties LLC
        TENANT: John Smith
        PLAINTIFF: XYZ Management
        DEFENDANT: Jane Doe
        """
        
        result = engine.recognize(text, "test.pdf")
        
        assert len(result.parties) >= 2
        party_roles = [p.context_label.lower() for p in result.parties]
        assert any("landlord" in role for role in party_roles)
        assert any("tenant" in role for role in party_roles)
    
    # === URGENCY TESTS ===
    
    def test_urgency_critical_writ(self):
        """Test that writs are marked as critical urgency."""
        text = """
        WRIT OF RESTITUTION
        You are hereby commanded to remove the defendant from the premises.
        """
        
        result = recognize_document(text, "writ.pdf")
        
        assert result.urgency_level == "critical"
    
    def test_urgency_high_for_court_docs(self):
        """Test that court documents have high urgency by default."""
        text = """
        STATE OF MINNESOTA DISTRICT COURT
        SUMMONS
        You are hereby summoned to respond.
        """
        
        result = recognize_document(text, "summons.pdf")
        
        assert result.urgency_level in ("high", "critical")
    
    # === CONFIDENCE TESTS ===
    
    def test_high_confidence_clear_match(self):
        """Test that clear matches have high confidence."""
        text = """
        RESIDENTIAL LEASE AGREEMENT
        This Lease Agreement is entered into between LANDLORD and TENANT.
        TERM OF LEASE: 12 months
        MONTHLY RENT: $1,500
        SECURITY DEPOSIT: $1,500
        """
        
        result = recognize_document(text, "lease_agreement.pdf")
        
        assert result.confidence > 0.7
    
    def test_low_confidence_ambiguous(self):
        """Test that ambiguous documents have lower confidence."""
        text = "Some random text that doesn't match any specific document type."
        
        result = recognize_document(text, "unknown.pdf")
        
        assert result.confidence < 0.5
    
    # === KEY TERMS TESTS ===
    
    def test_extract_mn_statute_references(self):
        """Test extraction of Minnesota statute references."""
        text = """
        Pursuant to Minnesota Statute 504B.135, you must vacate within 14 days.
        See also 504B.211 for eviction proceedings.
        """
        
        result = recognize_document(text, "notice.pdf")
        
        assert any("504B" in term for term in result.key_terms)
    
    def test_extract_legal_terms(self):
        """Test extraction of legal terms."""
        text = """
        This is an unlawful detainer action.
        The warranty of habitability has been breached.
        Tenant claims constructive eviction.
        """
        
        result = recognize_document(text, "court_doc.pdf")
        
        key_terms_lower = [t.lower() for t in result.key_terms]
        assert any("unlawful detainer" in term for term in key_terms_lower)
    
    # === REASONING CHAIN TESTS ===
    
    def test_reasoning_chain_populated(self):
        """Test that reasoning chain is populated for classifications."""
        text = """
        LEASE AGREEMENT
        LANDLORD: ABC Inc
        TENANT: John Doe
        RENT: $1,500/month
        """
        
        result = recognize_document(text, "lease.pdf")
        
        assert len(result.reasoning_chain) > 0
        assert any("match" in r.lower() or "score" in r.lower() 
                   for r in result.reasoning_chain)
    
    # === EDGE CASES ===
    
    def test_empty_text(self):
        """Test handling of empty text."""
        result = recognize_document("", "empty.pdf")
        
        assert result.doc_type == DocumentType.UNKNOWN
        assert result.confidence < 0.3
    
    def test_filename_hints(self):
        """Test that filename provides classification hints."""
        text = "Some generic document text without clear indicators."
        
        result = recognize_document(text, "summons_2025_smith.pdf")
        
        # Filename should boost summons score even with weak content
        assert "summons" in str(result.reasoning_chain).lower()
    
    def test_to_dict_format(self):
        """Test that to_dict returns expected format."""
        text = """
        LEASE AGREEMENT
        LANDLORD: ABC Inc
        TENANT: John Doe
        """
        
        result = recognize_document(text, "lease.pdf")
        result_dict = result.to_dict()
        
        # Check required fields
        assert "category" in result_dict
        assert "doc_type" in result_dict
        assert "confidence" in result_dict
        assert "title" in result_dict
        assert "summary" in result_dict
        assert "key_dates" in result_dict
        assert "key_parties" in result_dict
        assert "key_amounts" in result_dict
        assert "key_terms" in result_dict
