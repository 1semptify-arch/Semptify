"""
Context Analyzer
================

Understands document structure, flow, and context.
Identifies sections, determines document type hints from structure,
and assesses text quality.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .models import (
    DocumentContext, DocumentSection, ConfidenceMetrics,
    ReasoningChain, ReasoningStep, ReasoningType
)


@dataclass
class StructuralPattern:
    """A recognized structural pattern"""
    name: str
    pattern: str
    found: bool = False
    position: int = -1
    content: str = ""
    confidence: float = 0.0


class ContextAnalyzer:
    """
    Analyzes document context, structure, and quality.
    
    Responsibilities:
    - Detect document structure (headers, footers, sections)
    - Identify document flow type (letter, form, legal filing, etc.)
    - Assess text quality and completeness
    - Extract structural metadata
    """
    
    def __init__(self):
        # Document type structural indicators
        self.structural_patterns = self._build_structural_patterns()
        self.section_patterns = self._build_section_patterns()
        self.quality_indicators = self._build_quality_indicators()
    
    def _build_structural_patterns(self) -> Dict[str, List[str]]:
        """Build patterns for structural elements"""
        return {
            "letterhead": [
                r"(?i)^[A-Z][A-Za-z\s]+(?:LLC|Inc\.|Corp\.?|Company|Management|Properties)",
                r"(?i)\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",  # Phone number at top
                r"(?i)^(?:RE:|Re:|Subject:)",
            ],
            "date_line": [
                r"(?i)^(?:Date[d]?:?\s*)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
                r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
                r"(?i)^(?:Date[d]?:?\s*)?\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}",
            ],
            "address_block": [
                r"(?:\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*(?:\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir)\.?))",
                r"(?i)(?:Apt|Apartment|Unit|Suite|Ste|#)\s*[A-Za-z0-9]+",
                r"[A-Za-z\s]+,\s*(?:MN|Minnesota)\s+\d{5}(?:-\d{4})?",
            ],
            "salutation": [
                r"(?i)^Dear\s+",
                r"(?i)^To\s+(?:Whom\s+It\s+May\s+Concern|the\s+Tenant)",
                r"(?i)^(?:NOTICE\s+TO|ATTENTION):?\s*",
            ],
            "signature_block": [
                r"(?i)(?:Sincerely|Respectfully|Regards|Thank\s+you)[,:]?\s*$",
                r"(?i)^(?:Signature|Signed)[:\s]*",
                r"(?i)___+\s*$",
                r"(?i)^(?:By|Per):\s*",
            ],
            "notary_block": [
                r"(?i)NOTARY\s+PUBLIC",
                r"(?i)State\s+of\s+Minnesota.*County\s+of",
                r"(?i)subscribed\s+and\s+sworn",
                r"(?i)My\s+Commission\s+Expires",
            ],
            "case_caption": [
                r"(?i)STATE\s+OF\s+MINNESOTA",
                r"(?i)DISTRICT\s+COURT",
                r"(?i)(?:COUNTY\s+OF|IN\s+THE\s+MATTER\s+OF)",
                r"(?i)Case\s+(?:No\.|Number|#):?\s*\d+",
                r"(?i)(?:Plaintiff|Petitioner)\s*(?:v\.?|vs\.?)\s*(?:Defendant|Respondent)",
            ],
            "legal_heading": [
                r"(?i)^(?:SUMMONS|COMPLAINT|MOTION|ORDER|AFFIDAVIT|STIPULATION)",
                r"(?i)^NOTICE\s+(?:TO\s+(?:QUIT|VACATE)|OF\s+(?:EVICTION|TERMINATION))",
                r"(?i)^(?:WRIT\s+OF\s+(?:RECOVERY|RESTITUTION))",
            ],
        }
    
    def _build_section_patterns(self) -> Dict[str, re.Pattern]:
        """Build patterns for identifying sections"""
        return {
            "numbered_section": re.compile(r"^(?:\d+\.|\([a-z]\)|\([A-Z]\)|\([ivx]+\))\s+", re.MULTILINE),
            "capitalized_header": re.compile(r"^[A-Z][A-Z\s]{3,}(?:\:|\s*$)", re.MULTILINE),
            "underlined_section": re.compile(r"^.*\n[_\-=]{3,}\s*$", re.MULTILINE),
            "bold_markers": re.compile(r"(?:\*\*|__)(.*?)(?:\*\*|__)", re.MULTILINE),
        }
    
    def _build_quality_indicators(self) -> Dict[str, Any]:
        """Build quality assessment patterns"""
        return {
            "ocr_errors": [
                r"[|l1I]{3,}",  # Repeated similar chars (OCR confusion)
                r"[0O]{3,}",
                r"\b(?:tlie|tliat|witli|wliich)\b",  # Common OCR errors
                r"(?:rn|nn|ni){2,}",  # m/n confusion
            ],
            "incomplete_indicators": [
                r"(?:\.\.\.|…)\s*$",  # Trailing ellipsis
                r"^\s*\[continued\]",
                r"(?:page|pg\.?)\s*\d+\s*of\s*\d+",
            ],
            "good_quality_indicators": [
                r"(?:[.!?])\s+[A-Z]",  # Proper sentence endings
                r"\b(?:the|and|of|to|in|for|is|that|with)\b",  # Common words
            ],
        }
    
    def analyze(self, text: str, filename: str = None, 
                file_type: str = None) -> Tuple[DocumentContext, ReasoningChain]:
        """
        Perform full context analysis on document text.
        
        Returns:
            Tuple of (DocumentContext, ReasoningChain)
        """
        reasoning = ReasoningChain(pass_number=1)
        context = DocumentContext()
        
        if filename:
            context.filename = filename
        if file_type:
            context.file_type = file_type
        
        # Step 1: Basic text statistics
        reasoning.add_step(
            ReasoningType.STRUCTURAL_ANALYSIS,
            "Computing basic text statistics",
            {"text_length": len(text)},
            {}
        )
        context = self._compute_text_stats(text, context)
        
        # Step 2: Detect structural elements
        reasoning.add_step(
            ReasoningType.PATTERN_MATCH,
            "Detecting structural elements (letterhead, date, address, etc.)",
            {"patterns_checked": list(self.structural_patterns.keys())},
            {}
        )
        context = self._detect_structural_elements(text, context)
        
        # Step 3: Identify sections
        reasoning.add_step(
            ReasoningType.STRUCTURAL_ANALYSIS,
            "Identifying document sections and hierarchy",
            {},
            {}
        )
        context = self._identify_sections(text, context)
        
        # Step 4: Determine document flow type
        reasoning.add_step(
            ReasoningType.SEMANTIC_ANALYSIS,
            "Determining document flow type",
            {"elements_found": self._summarize_elements(context)},
            {}
        )
        context = self._determine_flow_type(context)
        
        # Step 5: Assess text quality
        reasoning.add_step(
            ReasoningType.STATISTICAL,
            "Assessing text quality and OCR accuracy",
            {},
            {}
        )
        context = self._assess_quality(text, context)
        
        # Step 6: Detect special characteristics
        reasoning.add_step(
            ReasoningType.PATTERN_MATCH,
            "Detecting special characteristics (scanned, signatures, etc.)",
            {},
            {}
        )
        context = self._detect_special_characteristics(text, context)
        
        reasoning.completed_at = datetime.now()
        reasoning.conclusion = f"Document type: {context.document_flow_type}, Quality: {context.ocr_quality:.1f}"
        
        return context, reasoning
    
    def _compute_text_stats(self, text: str, context: DocumentContext) -> DocumentContext:
        """Compute basic text statistics"""
        context.total_characters = len(text)
        context.total_words = len(text.split())
        
        # Count sentences (approximate)
        sentences = re.split(r'[.!?]+', text)
        context.total_sentences = len([s for s in sentences if s.strip()])
        
        # Estimate page count (rough: ~3000 chars per page)
        if context.total_characters > 0:
            context.page_count = max(1, context.total_characters // 3000)
        
        return context
    
    def _detect_structural_elements(self, text: str, context: DocumentContext) -> DocumentContext:
        """Detect structural elements in the document"""
        text_lines = text.split('\n')
        header_region = '\n'.join(text_lines[:min(20, len(text_lines))])
        footer_region = '\n'.join(text_lines[max(0, len(text_lines)-10):])
        
        # Check for letterhead (typically in first 10 lines)
        for pattern in self.structural_patterns["letterhead"]:
            if re.search(pattern, header_region, re.MULTILINE):
                context.has_letterhead = True
                context.has_header = True
                break
        
        # Check for date line
        for pattern in self.structural_patterns["date_line"]:
            if re.search(pattern, text, re.MULTILINE):
                context.has_date_line = True
                break
        
        # Check for address block
        address_matches = 0
        for pattern in self.structural_patterns["address_block"]:
            if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
                address_matches += 1
        context.has_address_block = address_matches >= 2
        
        # Check for salutation
        for pattern in self.structural_patterns["salutation"]:
            if re.search(pattern, text, re.MULTILINE):
                context.has_salutation = True
                break
        
        # Check for signature block
        for pattern in self.structural_patterns["signature_block"]:
            if re.search(pattern, footer_region, re.MULTILINE):
                context.has_signature_block = True
                break
        
        # Check for notary block
        notary_matches = 0
        for pattern in self.structural_patterns["notary_block"]:
            if re.search(pattern, text, re.MULTILINE):
                notary_matches += 1
        context.has_notary_block = notary_matches >= 2
        
        # Check for case caption (legal document)
        caption_matches = 0
        for pattern in self.structural_patterns["case_caption"]:
            if re.search(pattern, header_region, re.MULTILINE):
                caption_matches += 1
        context.has_case_caption = caption_matches >= 2
        
        return context
    
    def _identify_sections(self, text: str, context: DocumentContext) -> DocumentContext:
        """Identify and extract document sections"""
        sections = []
        
        # Find numbered sections
        numbered_matches = list(self.section_patterns["numbered_section"].finditer(text))
        for i, match in enumerate(numbered_matches):
            end_pos = numbered_matches[i+1].start() if i+1 < len(numbered_matches) else len(text)
            sections.append(DocumentSection(
                section_type="numbered",
                content=text[match.start():min(end_pos, match.start()+500)],
                start_position=match.start(),
                end_position=end_pos,
            ))
        
        # Find capitalized headers
        for match in self.section_patterns["capitalized_header"].finditer(text):
            header_text = match.group().strip()
            if len(header_text) > 3 and not any(c.isdigit() for c in header_text):
                sections.append(DocumentSection(
                    section_type="header",
                    title=header_text,
                    start_position=match.start(),
                    end_position=match.end(),
                ))
        
        # Identify key sections by content
        section_keywords = {
            "terms": ["terms", "conditions", "agreement"],
            "notice": ["hereby", "notice", "notification"],
            "signature": ["signature", "signed", "witness"],
            "parties": ["landlord", "tenant", "lessor", "lessee"],
            "property": ["premises", "property", "located at"],
            "payment": ["rent", "payment", "deposit", "amount"],
        }
        
        for section_name, keywords in section_keywords.items():
            for keyword in keywords:
                matches = list(re.finditer(rf'\b{keyword}\b', text, re.IGNORECASE))
                if matches:
                    # Mark regions around keyword matches as relevant sections
                    for match in matches[:3]:  # Limit to first 3 occurrences
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 500)
                        sections.append(DocumentSection(
                            section_type=section_name,
                            content=text[start:end],
                            start_position=start,
                            end_position=end,
                            importance_score=0.5
                        ))
        
        context.sections = sections
        return context
    
    def _determine_flow_type(self, context: DocumentContext) -> DocumentContext:
        """Determine the overall document flow type"""
        scores = {
            "legal_filing": 0,
            "letter": 0,
            "form": 0,
            "notice": 0,
            "contract": 0,
            "evidence": 0,
        }
        
        # Legal filing indicators
        if context.has_case_caption:
            scores["legal_filing"] += 5
        if context.has_notary_block:
            scores["legal_filing"] += 2
            scores["contract"] += 1
        
        # Letter indicators
        if context.has_letterhead:
            scores["letter"] += 2
        if context.has_salutation:
            scores["letter"] += 3
        if context.has_signature_block:
            scores["letter"] += 2
            scores["contract"] += 1
        if context.has_date_line:
            scores["letter"] += 1
            scores["notice"] += 1
        if context.has_address_block:
            scores["letter"] += 2
            scores["notice"] += 1
        
        # Notice indicators
        for section in context.sections:
            if section.section_type == "notice":
                scores["notice"] += 2
            elif section.section_type == "terms":
                scores["contract"] += 2
        
        # Determine winner
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            context.document_flow_type = best_type
        else:
            context.document_flow_type = "unknown"
        
        # Determine if it's a form
        context.is_form = self._detect_form_characteristics(context)
        
        return context
    
    def _detect_form_characteristics(self, context: DocumentContext) -> bool:
        """Detect if document appears to be a form"""
        form_indicators = 0
        
        # Check for blank lines (form fields)
        blank_line_patterns = ["____", ".....", "______"]
        for section in context.sections:
            for pattern in blank_line_patterns:
                if pattern in section.content:
                    form_indicators += 1
        
        # Check for checkbox indicators
        checkbox_patterns = ["[ ]", "[x]", "[X]", "☐", "☑", "☒"]
        for section in context.sections:
            for pattern in checkbox_patterns:
                if pattern in section.content:
                    form_indicators += 2
        
        return form_indicators >= 3
    
    def _assess_quality(self, text: str, context: DocumentContext) -> DocumentContext:
        """Assess text quality and OCR accuracy"""
        quality_score = 100.0
        
        # Check for OCR errors
        ocr_error_count = 0
        for pattern in self.quality_indicators["ocr_errors"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            ocr_error_count += len(matches)
        
        # Penalize for OCR errors
        quality_score -= min(30, ocr_error_count * 5)
        
        # Check for good quality indicators
        good_indicator_count = 0
        for pattern in self.quality_indicators["good_quality_indicators"]:
            matches = re.findall(pattern, text)
            good_indicator_count += len(matches)
        
        # Reward for good indicators
        quality_score += min(20, good_indicator_count // 10)
        
        # Check text completeness
        incomplete_count = 0
        for pattern in self.quality_indicators["incomplete_indicators"]:
            if re.search(pattern, text, re.IGNORECASE):
                incomplete_count += 1
        
        # Calculate completeness score
        completeness = max(0, 100 - incomplete_count * 20)
        
        # Word density check (good documents have reasonable word density)
        if context.total_characters > 0:
            word_density = context.total_words / (context.total_characters / 100)
            if 10 <= word_density <= 25:  # Typical range for English text
                quality_score += 10
            elif word_density < 5 or word_density > 35:
                quality_score -= 15
        
        context.ocr_quality = max(0, min(100, quality_score))
        context.is_scanned = quality_score < 80 or ocr_error_count > 5
        
        # Structural clarity based on section identification
        section_count = len(context.sections)
        if section_count >= 3:
            context.structural_clarity = min(100, 50 + section_count * 5)
        else:
            context.structural_clarity = max(20, section_count * 20)
        
        context.text_completeness = completeness
        
        return context
    
    def _detect_special_characteristics(self, text: str, context: DocumentContext) -> DocumentContext:
        """Detect special document characteristics"""
        text_lower = text.lower()
        
        # Handwriting indicators (often OCR produces specific patterns for handwriting)
        handwriting_patterns = [
            r"(?:illegible|unclear|handwritten)",
            r"\[.*?\?\]",  # Uncertain transcriptions
        ]
        for pattern in handwriting_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                context.has_handwriting = True
                break
        
        # Signature indicators
        signature_patterns = [
            r"(?:signature|signed|sign here)",
            r"(?:/s/|/S/)\s*[A-Za-z]",  # Electronic signature
            r"x_+",  # Signature line
        ]
        for pattern in signature_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                context.has_signatures = True
                break
        
        # Stamp indicators
        stamp_patterns = [
            r"(?:FILED|RECEIVED|STAMPED|CERTIFIED)",
            r"(?:OFFICIAL|CLERK|COURT)\s+(?:STAMP|SEAL)",
        ]
        for pattern in stamp_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                context.has_stamps = True
                break
        
        # Language detection (basic - check for non-English)
        spanish_words = ["el", "la", "de", "que", "en", "los", "del", "las"]
        spanish_count = sum(1 for word in spanish_words if f" {word} " in text_lower)
        if spanish_count >= 3:
            context.language = "es"  # Spanish
        
        return context
    
    def _summarize_elements(self, context: DocumentContext) -> Dict[str, bool]:
        """Summarize detected elements for reasoning chain"""
        return {
            "letterhead": context.has_letterhead,
            "date_line": context.has_date_line,
            "address_block": context.has_address_block,
            "salutation": context.has_salutation,
            "signature_block": context.has_signature_block,
            "notary_block": context.has_notary_block,
            "case_caption": context.has_case_caption,
        }
    
    def get_key_sections(self, context: DocumentContext, 
                         max_sections: int = 5) -> List[DocumentSection]:
        """Get the most important sections for analysis"""
        # Sort by importance score
        sorted_sections = sorted(
            context.sections,
            key=lambda s: s.importance_score,
            reverse=True
        )
        return sorted_sections[:max_sections]
    
    def extract_header_info(self, text: str) -> Dict[str, Any]:
        """Extract information typically found in document headers"""
        header_info = {
            "date": None,
            "from_party": None,
            "to_party": None,
            "re_subject": None,
            "case_number": None,
        }
        
        # Look in first 30 lines
        lines = text.split('\n')[:30]
        header_text = '\n'.join(lines)
        
        # Extract date
        date_patterns = [
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE)
            if match:
                header_info["date"] = match.group()
                break
        
        # Extract RE: subject line
        re_match = re.search(r"(?:RE|Re|Subject):\s*(.+?)(?:\n|$)", header_text)
        if re_match:
            header_info["re_subject"] = re_match.group(1).strip()
        
        # Extract case number
        case_match = re.search(r"(?:Case|File|No\.|Number|#)[:\s]*(\d+[-\w]*\d*)", header_text, re.IGNORECASE)
        if case_match:
            header_info["case_number"] = case_match.group(1)
        
        return header_info
