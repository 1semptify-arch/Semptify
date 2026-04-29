"""
Text Preprocessor
=================

Cleans and normalizes OCR text for courtroom-accurate recognition.
This is Pass 0 - runs before the recognition engine.

Goals:
1. Fix common OCR errors
2. Normalize whitespace and formatting
3. Standardize legal terminology
4. Preserve critical information (numbers, dates, amounts)
"""

import re
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, field

from .legal_dictionary import get_legal_dictionary, MinnesotaLegalDictionary


@dataclass
class PreprocessingResult:
    """Result of text preprocessing"""
    original_text: str
    cleaned_text: str
    corrections_made: List[Dict] = field(default_factory=list)
    quality_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    line_count: int = 0
    word_count: int = 0
    has_structured_sections: bool = False


class TextPreprocessor:
    """
    Preprocesses document text for accurate recognition.
    
    Pipeline:
    1. OCR error correction (character substitution)
    2. Whitespace normalization
    3. Line break cleanup
    4. Legal terminology standardization
    5. Critical data preservation validation
    """
    
    def __init__(self):
        self.dictionary = get_legal_dictionary()
        
        # Character substitution patterns
        self.char_substitutions = [
            # Common OCR confusions
            (r'(?<=[a-z])l(?=[a-z])', 'i'),  # l->i in middle of words (fiIe -> file)
            (r'\bl(?=\d)', '1'),  # l at start of number -> 1
            (r'(?<=\d)l', '1'),  # l after digit -> 1
            (r'(?<=\d)O', '0'),  # O after digit -> 0
            (r'O(?=\d)', '0'),  # O before digit -> 0
            (r'\brn(?=[a-z])', 'm'),  # rn at word start -> m
            (r'(?<=[a-z])rn(?=[a-z])', 'm'),  # rn in middle -> m
        ]
        
        # Whitespace patterns
        self.whitespace_patterns = [
            (r'\r\n', '\n'),  # Normalize line endings
            (r'\r', '\n'),
            (r'[ \t]+', ' '),  # Collapse horizontal whitespace
            (r'\n{3,}', '\n\n'),  # Max 2 consecutive newlines
            (r'^\s+', ''),  # Remove leading whitespace
            (r'\s+$', ''),  # Remove trailing whitespace
        ]
        
        # Legal terminology standardization
        self.terminology_standards = {
            # Notice types
            r'(?i)\b14\s*-?\s*day\s+notice\b': '14-DAY NOTICE',
            r'(?i)\bfourteen\s*\(?\s*14\s*\)?\s*day\s+notice\b': '14-DAY NOTICE',
            r'(?i)\bnotice\s+to\s+(?:quit|vacate)\b': 'NOTICE TO QUIT',
            
            # Court terms
            r'(?i)\bdistrict\s+court\b': 'District Court',
            r'(?i)\bhousing\s+court\b': 'Housing Court',
            
            # Parties
            r'(?i)\bplaintiff\s*\(?s?\)?\b': 'Plaintiff',
            r'(?i)\bdefendant\s*\(?s?\)?\b': 'Defendant',
            r'(?i)\bpetitioner\b': 'Petitioner',
            r'(?i)\brespondent\b': 'Respondent',
            
            # Actions
            r'(?i)\bvs?\.?\s+': 'v. ',  # Standardize vs/v./versus
            r'(?i)\bversus\s+': 'v. ',
        }
        
        # Section header patterns (to preserve structure)
        self.section_patterns = [
            r'^[A-Z][A-Z\s]{3,}[:\.]?\s*$',  # ALL CAPS HEADER
            r'^\d+\.\s+[A-Z]',  # 1. Numbered section
            r'^[IVXLC]+\.\s+',  # Roman numeral section
            r'^[A-Z]\.\s+',  # A. Letter section
        ]
    
    def preprocess(self, text: str) -> PreprocessingResult:
        """
        Full preprocessing pipeline.
        
        Args:
            text: Raw OCR text
            
        Returns:
            PreprocessingResult with cleaned text and metadata
        """
        result = PreprocessingResult(
            original_text=text,
            cleaned_text=text,
        )
        
        if not text or not text.strip():
            result.warnings.append("Empty or whitespace-only text")
            return result
        
        # Step 1: Basic cleanup
        cleaned = self._normalize_whitespace(text)
        
        # Step 2: OCR error correction
        cleaned, corrections = self._correct_ocr_errors(cleaned)
        result.corrections_made.extend(corrections)
        
        # Step 3: Apply dictionary corrections
        cleaned = self.dictionary.correct_ocr_text(cleaned)
        
        # Step 4: Standardize legal terminology
        cleaned, term_corrections = self._standardize_terminology(cleaned)
        result.corrections_made.extend(term_corrections)
        
        # Step 5: Preserve critical data
        validation_warnings = self._validate_critical_data(cleaned)
        result.warnings.extend(validation_warnings)
        
        # Step 6: Calculate quality score
        result.quality_score = self._calculate_quality_score(cleaned, text)
        
        # Metadata
        result.cleaned_text = cleaned
        result.line_count = len(cleaned.split('\n'))
        result.word_count = len(cleaned.split())
        result.has_structured_sections = self._has_structure(cleaned)
        
        return result
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize all whitespace"""
        for pattern, replacement in self.whitespace_patterns:
            text = re.sub(pattern, replacement, text)
        
        # Also normalize within lines
        lines = []
        for line in text.split('\n'):
            # Remove multiple spaces but preserve intentional indentation
            line = re.sub(r'(?<=\S)[ \t]{2,}(?=\S)', ' ', line)
            lines.append(line.rstrip())
        
        return '\n'.join(lines)
    
    def _correct_ocr_errors(self, text: str) -> Tuple[str, List[Dict]]:
        """Apply character-level OCR corrections"""
        corrections = []
        original = text
        
        for pattern, replacement in self.char_substitutions:
            matches = list(re.finditer(pattern, text))
            if matches:
                for match in matches:
                    corrections.append({
                        "type": "ocr_char",
                        "original": match.group(),
                        "corrected": replacement,
                        "position": match.start(),
                    })
                text = re.sub(pattern, replacement, text)
        
        return text, corrections
    
    def _standardize_terminology(self, text: str) -> Tuple[str, List[Dict]]:
        """Standardize legal terminology to canonical forms"""
        corrections = []
        
        for pattern, replacement in self.terminology_standards.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                for match in matches:
                    if match.group() != replacement:
                        corrections.append({
                            "type": "terminology",
                            "original": match.group(),
                            "corrected": replacement,
                            "position": match.start(),
                        })
                text = re.sub(pattern, replacement, text)
        
        return text, corrections
    
    def _validate_critical_data(self, text: str) -> List[str]:
        """Validate that critical data is properly formatted"""
        warnings = []
        
        # Check for valid dollar amounts
        dollar_pattern = r'\$\s*([\d,]+(?:\.\d{0,2})?)'
        for match in re.finditer(dollar_pattern, text):
            amount_str = match.group(1)
            # Check for incomplete decimals
            if '.' in amount_str:
                decimal_part = amount_str.split('.')[1]
                if len(decimal_part) == 1:
                    warnings.append(f"Incomplete dollar amount: ${amount_str} (single decimal digit)")
        
        # Check for valid dates
        date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}'
        dates = re.findall(date_pattern, text, re.IGNORECASE)
        for date in dates:
            # Check for 2-digit years
            if re.search(r',?\s+\d{2}$', date):
                warnings.append(f"Ambiguous 2-digit year in date: {date}")
        
        # Check for potential phone number OCR errors
        phone_pattern = r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        # 612, 651, 763, 952 are Minnesota area codes
        for phone in phones:
            area_code = re.search(r'\((\d{3})\)', phone)
            if area_code:
                ac = area_code.group(1)
                if ac not in ['612', '651', '763', '952', '218', '320', '507', '800', '888', '877']:
                    warnings.append(f"Unusual area code (possible OCR error): {phone}")
        
        # Check for missing case numbers in court documents
        if re.search(r'(?i)district\s+court|housing\s+court|summons|complaint', text):
            if not re.search(r'(?i)case\s*(?:no\.?|number|#)', text):
                warnings.append("Court document may be missing case number")
        
        return warnings
    
    def _calculate_quality_score(self, cleaned: str, original: str) -> float:
        """
        Calculate text quality score (0-100).
        
        Higher score = cleaner, more reliable text.
        """
        score = 100.0
        
        # Check for OCR garbage characters
        garbage_chars = len(re.findall(r'[^\x00-\x7F]', cleaned))
        if garbage_chars > 0:
            score -= min(20, garbage_chars * 2)
        
        # Check for unusual character sequences
        unusual = len(re.findall(r'(?:[^aeiouAEIOU\s]{7,})|(?:[aeiouAEIOU]{5,})', cleaned))
        if unusual > 0:
            score -= min(15, unusual * 5)
        
        # Check word-like patterns (good indicator)
        word_like = len(re.findall(r'\b[a-zA-Z]{2,15}\b', cleaned))
        total_tokens = len(cleaned.split())
        if total_tokens > 0:
            word_ratio = word_like / total_tokens
            if word_ratio < 0.7:
                score -= (0.7 - word_ratio) * 30
        
        # Check for common legal terms (boosts confidence)
        legal_terms = [
            'notice', 'tenant', 'landlord', 'rent', 'lease',
            'court', 'eviction', 'property', 'premises', 'deposit'
        ]
        found_terms = sum(1 for term in legal_terms if term.lower() in cleaned.lower())
        score += min(10, found_terms * 2)
        
        # Penalty for very short text
        if len(cleaned) < 100:
            score -= 10
        
        # Penalty for no recognizable structure
        if not re.search(r'\n', cleaned):
            score -= 10
        
        return max(0, min(100, score))
    
    def _has_structure(self, text: str) -> bool:
        """Check if text has recognizable structure"""
        lines = text.split('\n')
        
        # Check for headers
        for line in lines[:20]:  # Check first 20 lines
            for pattern in self.section_patterns:
                if re.match(pattern, line.strip()):
                    return True
        
        # Check for numbered lists
        if re.search(r'^\s*\d+[.)]\s', text, re.MULTILINE):
            return True
        
        # Check for address blocks
        if re.search(r'\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd)', text):
            return True
        
        return False
    
    def quick_clean(self, text: str) -> str:
        """
        Quick cleaning for basic normalization.
        Use full preprocess() for accuracy-critical operations.
        """
        # Just whitespace normalization
        text = re.sub(r'\r\n|\r', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


# Singleton instance
_preprocessor = None

def get_preprocessor() -> TextPreprocessor:
    """Get or create singleton preprocessor instance"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = TextPreprocessor()
    return _preprocessor
