"""
Court Form Generator
====================
Auto-fills Minnesota court forms with case data:
- Answer to Eviction Complaint
- Motion to Dismiss
- Motion for Continuance
- Counterclaim
- Request for Hearing

Features:
- PDF generation with fillable fields
- Print-ready formatting
- Data mapping from FormDataHub
"""

import io
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Form Field Mappings
# =============================================================================

FORM_MAPPINGS = {
    "answer_to_complaint": {
        "title": "Answer to Eviction Complaint",
        "description": "Formal response to landlord's eviction complaint",
        "fields": {
            "court_name": ["court_name", "district_court"],
            "county": ["county", "court_county"],
            "case_number": ["case_number", "case_no"],
            "plaintiff_name": ["plaintiff_name", "landlord_name"],
            "defendant_name": ["defendant_name", "tenant_name", "user_name"],
            "defendant_address": ["defendant_address", "tenant_address", "property_address"],
            "filing_date": ["filing_date", "answer_date"],
            "hearing_date": ["hearing_date", "court_date"],
            "hearing_time": ["hearing_time"],
            "defenses": ["defenses", "defense_list"],
            "signature": ["signature", "defendant_signature"],
            "signature_date": ["signature_date"],
        },
        "sections": ["general_denial", "affirmative_defenses", "counterclaims"],
    },
    "motion_to_dismiss": {
        "title": "Motion to Dismiss",
        "description": "Request to dismiss case due to procedural or legal defects",
        "fields": {
            "court_name": ["court_name"],
            "case_number": ["case_number"],
            "plaintiff_name": ["plaintiff_name"],
            "defendant_name": ["defendant_name"],
            "motion_grounds": ["dismissal_grounds", "motion_reasons"],
            "supporting_facts": ["supporting_facts"],
            "legal_authority": ["legal_citations", "statutes"],
        },
        "sections": ["grounds", "facts", "legal_argument", "conclusion"],
    },
    "motion_for_continuance": {
        "title": "Motion for Continuance",
        "description": "Request to postpone hearing date",
        "fields": {
            "court_name": ["court_name"],
            "case_number": ["case_number"],
            "current_hearing_date": ["hearing_date"],
            "reason_for_continuance": ["continuance_reason"],
            "requested_date": ["requested_hearing_date"],
            "defendant_name": ["defendant_name"],
        },
        "sections": ["request", "grounds", "prejudice_statement"],
    },
    "counterclaim": {
        "title": "Counterclaim",
        "description": "Tenant's claims against landlord",
        "fields": {
            "court_name": ["court_name"],
            "case_number": ["case_number"],
            "plaintiff_name": ["plaintiff_name"],
            "defendant_name": ["defendant_name"],
            "violations": ["landlord_violations", "violations"],
            "damages_claimed": ["damages_amount", "counterclaim_amount"],
            "supporting_facts": ["violation_details"],
        },
        "sections": ["claims", "damages", "relief_requested"],
    },
    "request_for_hearing": {
        "title": "Request for Hearing",
        "description": "Request to schedule or expedite hearing",
        "fields": {
            "court_name": ["court_name"],
            "case_number": ["case_number"],
            "party_name": ["defendant_name"],
            "hearing_type": ["hearing_type"],
            "urgency_reason": ["urgency_reason"],
        },
        "sections": ["request", "grounds"],
    },
}


# =============================================================================
# Defense Templates
# =============================================================================

DEFENSE_TEMPLATES = {
    "improper_notice": {
        "title": "Improper Notice",
        "text": """The Plaintiff failed to provide proper notice as required by Minnesota 
Statute § 504B.321. Specifically, the notice was defective because: {details}.""",
        "statute": "Minn. Stat. § 504B.321",
    },
    "retaliation": {
        "title": "Retaliation",
        "text": """This eviction action is retaliatory in violation of Minnesota Statute 
§ 504B.441. The eviction was filed after Defendant: {details}.""",
        "statute": "Minn. Stat. § 504B.441",
    },
    "habitability": {
        "title": "Breach of Warranty of Habitability",
        "text": """Plaintiff breached the implied warranty of habitability under Minnesota 
Statute § 504B.161. The rental unit has the following uninhabitable conditions: {details}.""",
        "statute": "Minn. Stat. § 504B.161",
    },
    "improper_service": {
        "title": "Improper Service",
        "text": """Defendant was not properly served with the summons and complaint as 
required by Minnesota Rules of Civil Procedure. {details}.""",
        "statute": "Minn. R. Civ. P. 4.03",
    },
    "rent_escrow": {
        "title": "Rent Paid or Escrowed",
        "text": """Defendant has paid all rent due or has properly escrowed rent with the 
court pursuant to Minnesota Statute § 504B.385. {details}.""",
        "statute": "Minn. Stat. § 504B.385",
    },
    "discrimination": {
        "title": "Discrimination",
        "text": """This eviction action is discriminatory in violation of the Minnesota 
Human Rights Act § 363A.09. Defendant believes the eviction is based on: {details}.""",
        "statute": "Minn. Stat. § 363A.09",
    },
    "waiver": {
        "title": "Waiver of Right to Evict",
        "text": """Plaintiff waived the right to evict by: {details}. By accepting rent 
or failing to act, Plaintiff waived any breach of the lease.""",
        "statute": "Common Law",
    },
    "cure_within_time": {
        "title": "Violation Cured Within Time",
        "text": """Defendant cured the alleged lease violation within the time period 
specified in the notice. {details}.""",
        "statute": "Minn. Stat. § 504B.321",
    },
}


class CourtFormGenerator:
    """Generates Minnesota court forms with auto-filled data."""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates" / "forms"
        
    async def generate_form(
        self,
        form_type: str,
        case_data: Dict[str, Any],
        defenses: Optional[List[str]] = None,
        output_format: str = "pdf",
    ) -> Dict[str, Any]:
        """
        Generate a court form with case data.
        
        Args:
            form_type: Type of form (answer_to_complaint, motion_to_dismiss, etc.)
            case_data: Dictionary of case information from FormDataHub
            defenses: List of defense types to include
            output_format: pdf, html, or docx
            
        Returns:
            Dictionary with form content and metadata
        """
        if form_type not in FORM_MAPPINGS:
            return {
                "error": f"Unknown form type: {form_type}",
                "available_forms": list(FORM_MAPPINGS.keys()),
            }
        
        mapping = FORM_MAPPINGS[form_type]
        
        # Map case data to form fields
        form_data = self._map_fields(case_data, mapping["fields"])
        
        # Add defenses if applicable
        if defenses and form_type in ["answer_to_complaint", "counterclaim"]:
            form_data["defenses_text"] = self._format_defenses(defenses, case_data)
        
        # Generate form content
        if output_format == "html":
            content = self._generate_html(form_type, form_data, mapping)
        elif output_format == "pdf":
            content = await self._generate_pdf(form_type, form_data, mapping)
        else:
            content = self._generate_text(form_type, form_data, mapping)
        
        return {
            "form_type": form_type,
            "title": mapping["title"],
            "description": mapping["description"],
            "format": output_format,
            "content": content,
            "fields_used": list(form_data.keys()),
            "generated_at": datetime.now().isoformat(),
        }
    
    def _map_fields(
        self,
        case_data: Dict[str, Any],
        field_mapping: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Map case data to form fields using field mapping."""
        form_data = {}
        
        for form_field, source_fields in field_mapping.items():
            value = None
            for source in source_fields:
                if source in case_data and case_data[source]:
                    value = case_data[source]
                    break
            
            if value is not None:
                # Format dates
                if isinstance(value, (datetime, date)):
                    value = value.strftime("%B %d, %Y")
                form_data[form_field] = value
            else:
                form_data[form_field] = f"[{form_field.upper()}]"
        
        return form_data
    
    def _format_defenses(
        self,
        defense_types: List[str],
        case_data: Dict[str, Any],
    ) -> str:
        """Format defense paragraphs."""
        defense_paragraphs = []
        
        for i, defense_type in enumerate(defense_types, 1):
            if defense_type in DEFENSE_TEMPLATES:
                template = DEFENSE_TEMPLATES[defense_type]
                details = case_data.get(f"{defense_type}_details", "[Specific facts to be added]")
                text = template["text"].format(details=details)
                defense_paragraphs.append(
                    f"{i}. {template['title']}\n\n{text}\n\nSee {template['statute']}."
                )
            else:
                defense_paragraphs.append(f"{i}. {defense_type}")
        
        return "\n\n".join(defense_paragraphs)
    
    def _generate_html(
        self,
        form_type: str,
        form_data: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> str:
        """Generate HTML version of form."""
        if form_type == "answer_to_complaint":
            return self._answer_html(form_data)
        elif form_type == "motion_to_dismiss":
            return self._motion_dismiss_html(form_data)
        elif form_type == "motion_for_continuance":
            return self._continuance_html(form_data)
        elif form_type == "counterclaim":
            return self._counterclaim_html(form_data)
        else:
            return self._generic_form_html(form_type, form_data, mapping)
    
    def _answer_html(self, data: Dict[str, Any]) -> str:
        """Generate Answer to Eviction Complaint HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Answer to Eviction Complaint</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; max-width: 8.5in; margin: 0 auto; padding: 1in; line-height: 1.6; }}
        .header {{ text-align: center; margin-bottom: 2em; }}
        .court-name {{ font-weight: bold; font-size: 14pt; text-transform: uppercase; }}
        .case-caption {{ margin: 2em 0; border: 1px solid #000; padding: 1em; }}
        .case-number {{ float: right; }}
        .party {{ margin: 0.5em 0; }}
        .section {{ margin: 1.5em 0; }}
        .section-title {{ font-weight: bold; text-decoration: underline; }}
        .signature-block {{ margin-top: 3em; }}
        .signature-line {{ border-top: 1px solid #000; width: 250px; margin-top: 3em; }}
        @media print {{ body {{ padding: 0.5in; }} }}
    </style>
</head>
<body>
    <div class="header">
        <div class="court-name">STATE OF MINNESOTA</div>
        <div class="court-name">DISTRICT COURT</div>
        <div>{data.get('county', '[COUNTY]')} COUNTY</div>
        <div>{data.get('court_name', 'DISTRICT COURT')}</div>
    </div>
    
    <div class="case-caption">
        <div class="case-number">Case No: {data.get('case_number', '[CASE NUMBER]')}</div>
        <div class="party"><strong>{data.get('plaintiff_name', '[PLAINTIFF]')}</strong></div>
        <div class="party" style="padding-left: 2em;">Plaintiff,</div>
        <div class="party">vs.</div>
        <div class="party"><strong>{data.get('defendant_name', '[DEFENDANT]')}</strong></div>
        <div class="party" style="padding-left: 2em;">Defendant.</div>
    </div>
    
    <div style="text-align: center; font-weight: bold; font-size: 14pt; margin: 2em 0;">
        ANSWER TO EVICTION COMPLAINT
    </div>
    
    <div class="section">
        <p>Defendant, {data.get('defendant_name', '[DEFENDANT]')}, hereby answers Plaintiff's 
        Complaint as follows:</p>
    </div>
    
    <div class="section">
        <div class="section-title">I. GENERAL DENIAL</div>
        <p>Defendant denies each and every allegation in the Complaint except as specifically 
        admitted herein.</p>
    </div>
    
    <div class="section">
        <div class="section-title">II. AFFIRMATIVE DEFENSES</div>
        {data.get('defenses_text', '<p>[DEFENSES TO BE ADDED]</p>')}
    </div>
    
    <div class="section">
        <div class="section-title">III. REQUEST FOR RELIEF</div>
        <p>WHEREFORE, Defendant respectfully requests that this Court:</p>
        <ol>
            <li>Deny Plaintiff's request for possession;</li>
            <li>Dismiss this action with prejudice;</li>
            <li>Award Defendant costs and disbursements; and</li>
            <li>Grant such other relief as the Court deems just and proper.</li>
        </ol>
    </div>
    
    <div class="signature-block">
        <p>Dated: {data.get('signature_date', datetime.now().strftime('%B %d, %Y'))}</p>
        <div class="signature-line"></div>
        <p>{data.get('defendant_name', '[DEFENDANT NAME]')}<br>
        Pro Se Defendant<br>
        {data.get('defendant_address', '[ADDRESS]')}</p>
    </div>
</body>
</html>"""
    
    def _motion_dismiss_html(self, data: Dict[str, Any]) -> str:
        """Generate Motion to Dismiss HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Motion to Dismiss</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; max-width: 8.5in; margin: 0 auto; padding: 1in; line-height: 1.6; }}
        .header {{ text-align: center; margin-bottom: 2em; }}
        .court-name {{ font-weight: bold; font-size: 14pt; text-transform: uppercase; }}
        .case-caption {{ margin: 2em 0; border: 1px solid #000; padding: 1em; }}
        .section {{ margin: 1.5em 0; }}
        .section-title {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="court-name">STATE OF MINNESOTA - DISTRICT COURT</div>
        <div>{data.get('county', '[COUNTY]')} COUNTY</div>
    </div>
    
    <div class="case-caption">
        <div style="float: right;">Case No: {data.get('case_number', '[CASE NUMBER]')}</div>
        <div><strong>{data.get('plaintiff_name', '[PLAINTIFF]')}</strong>, Plaintiff</div>
        <div>vs.</div>
        <div><strong>{data.get('defendant_name', '[DEFENDANT]')}</strong>, Defendant</div>
    </div>
    
    <div style="text-align: center; font-weight: bold; font-size: 14pt; margin: 2em 0;">
        MOTION TO DISMISS
    </div>
    
    <div class="section">
        <p>Defendant {data.get('defendant_name', '[DEFENDANT]')} moves this Court to dismiss 
        Plaintiff's Complaint with prejudice on the following grounds:</p>
    </div>
    
    <div class="section">
        <div class="section-title">GROUNDS FOR DISMISSAL</div>
        <p>{data.get('motion_grounds', '[GROUNDS TO BE ADDED]')}</p>
    </div>
    
    <div class="section">
        <div class="section-title">SUPPORTING FACTS</div>
        <p>{data.get('supporting_facts', '[FACTS TO BE ADDED]')}</p>
    </div>
    
    <div class="section">
        <div class="section-title">LEGAL AUTHORITY</div>
        <p>{data.get('legal_authority', '[CITATIONS TO BE ADDED]')}</p>
    </div>
    
    <div class="section">
        <p>WHEREFORE, Defendant respectfully requests that this Court grant this Motion 
        and dismiss Plaintiff's Complaint with prejudice.</p>
    </div>
    
    <div style="margin-top: 3em;">
        <p>Dated: {datetime.now().strftime('%B %d, %Y')}</p>
        <div style="border-top: 1px solid #000; width: 250px; margin-top: 3em;"></div>
        <p>{data.get('defendant_name', '[DEFENDANT]')}, Pro Se</p>
    </div>
</body>
</html>"""
    
    def _continuance_html(self, data: Dict[str, Any]) -> str:
        """Generate Motion for Continuance HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Motion for Continuance</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; max-width: 8.5in; margin: 0 auto; padding: 1in; line-height: 1.6; }}
        .header {{ text-align: center; margin-bottom: 2em; }}
        .court-name {{ font-weight: bold; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="court-name">STATE OF MINNESOTA - DISTRICT COURT</div>
        <div>Case No: {data.get('case_number', '[CASE NUMBER]')}</div>
    </div>
    
    <div style="text-align: center; font-weight: bold; margin: 2em 0;">
        MOTION FOR CONTINUANCE
    </div>
    
    <p>Defendant {data.get('defendant_name', '[DEFENDANT]')} respectfully moves this Court 
    to continue the hearing currently scheduled for {data.get('current_hearing_date', '[DATE]')}.</p>
    
    <p><strong>GROUNDS:</strong></p>
    <p>{data.get('reason_for_continuance', '[REASON TO BE ADDED]')}</p>
    
    <p>Defendant requests that the hearing be rescheduled to {data.get('requested_date', '[REQUESTED DATE]')} 
    or the earliest available date convenient to the Court.</p>
    
    <p>This continuance will not prejudice Plaintiff and is necessary for Defendant to 
    adequately prepare for the hearing.</p>
    
    <div style="margin-top: 3em;">
        <p>Dated: {datetime.now().strftime('%B %d, %Y')}</p>
        <div style="border-top: 1px solid #000; width: 250px; margin-top: 3em;"></div>
        <p>{data.get('defendant_name', '[DEFENDANT]')}, Pro Se</p>
    </div>
</body>
</html>"""
    
    def _counterclaim_html(self, data: Dict[str, Any]) -> str:
        """Generate Counterclaim HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Counterclaim</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; max-width: 8.5in; margin: 0 auto; padding: 1in; line-height: 1.6; }}
        .header {{ text-align: center; margin-bottom: 2em; }}
    </style>
</head>
<body>
    <div class="header">
        <div style="font-weight: bold; text-transform: uppercase;">STATE OF MINNESOTA - DISTRICT COURT</div>
        <div>Case No: {data.get('case_number', '[CASE NUMBER]')}</div>
    </div>
    
    <div style="text-align: center; font-weight: bold; margin: 2em 0;">
        DEFENDANT'S COUNTERCLAIM
    </div>
    
    <p>Defendant {data.get('defendant_name', '[DEFENDANT]')} hereby asserts the following 
    counterclaims against Plaintiff {data.get('plaintiff_name', '[PLAINTIFF]')}:</p>
    
    <h3>CLAIMS</h3>
    <p>{data.get('violations', '[VIOLATIONS TO BE ADDED]')}</p>
    
    <h3>DAMAGES</h3>
    <p>As a result of Plaintiff's conduct, Defendant has suffered damages in the amount of 
    ${data.get('damages_claimed', '[AMOUNT]')}, including but not limited to:</p>
    <ul>
        <li>Diminished value of rental premises</li>
        <li>Out-of-pocket expenses</li>
        <li>Emotional distress</li>
    </ul>
    
    <h3>RELIEF REQUESTED</h3>
    <p>WHEREFORE, Defendant requests judgment against Plaintiff for:</p>
    <ol>
        <li>Compensatory damages in the amount of ${data.get('damages_claimed', '[AMOUNT]')};</li>
        <li>Costs and disbursements;</li>
        <li>Such other relief as the Court deems just.</li>
    </ol>
    
    <div style="margin-top: 3em;">
        <p>Dated: {datetime.now().strftime('%B %d, %Y')}</p>
        <div style="border-top: 1px solid #000; width: 250px; margin-top: 3em;"></div>
        <p>{data.get('defendant_name', '[DEFENDANT]')}, Pro Se</p>
    </div>
</body>
</html>"""
    
    def _generic_form_html(
        self,
        form_type: str,
        data: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> str:
        """Generate generic form HTML."""
        fields_html = ""
        for field, value in data.items():
            fields_html += f"<p><strong>{field.replace('_', ' ').title()}:</strong> {value}</p>\n"
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{mapping['title']}</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; max-width: 8.5in; margin: 0 auto; padding: 1in; }}
    </style>
</head>
<body>
    <h1 style="text-align: center;">{mapping['title']}</h1>
    <p>{mapping['description']}</p>
    <hr>
    {fields_html}
</body>
</html>"""
    
    async def _generate_pdf(
        self,
        form_type: str,
        form_data: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> bytes:
        """Generate PDF version of form."""
        # Generate HTML first
        html = self._generate_html(form_type, form_data, mapping)
        
        # Try to convert to PDF
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html).write_pdf()
            return pdf_bytes
        except ImportError:
            pass
        
        try:
            from xhtml2pdf import pisa
            result = io.BytesIO()
            pisa.CreatePDF(io.StringIO(html), dest=result)
            return result.getvalue()
        except ImportError:
            pass
        
        # Return HTML as fallback
        logger.warning("PDF generation libraries not available, returning HTML")
        return html.encode('utf-8')
    
    def _generate_text(
        self,
        form_type: str,
        form_data: Dict[str, Any],
        mapping: Dict[str, Any],
    ) -> str:
        """Generate plain text version of form."""
        lines = [
            f"{'=' * 60}",
            mapping['title'].upper(),
            f"{'=' * 60}",
            "",
        ]
        
        for field, value in form_data.items():
            label = field.replace('_', ' ').title()
            lines.append(f"{label}: {value}")
        
        return "\n".join(lines)
    
    def get_available_forms(self) -> List[Dict[str, str]]:
        """Get list of available form types."""
        return [
            {
                "type": form_type,
                "title": mapping["title"],
                "description": mapping["description"],
            }
            for form_type, mapping in FORM_MAPPINGS.items()
        ]
    
    def get_available_defenses(self) -> List[Dict[str, str]]:
        """Get list of available defense types."""
        return [
            {
                "type": defense_type,
                "title": template["title"],
                "statute": template["statute"],
            }
            for defense_type, template in DEFENSE_TEMPLATES.items()
        ]


# Singleton instance
form_generator = CourtFormGenerator()
