"""
Batch Auto Mode Analysis
========================

Script to run auto mode analysis on all existing uploaded documents.
Generates comprehensive summaries with actionable recommendations.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchAutoModeAnalyzer:
    """Analyzes multiple documents in auto mode."""
    
    def __init__(self, documents_root: str = "data/documents"):
        self.documents_root = documents_root
        self.results = []
    
    def get_uploaded_documents(self) -> List[Dict[str, Any]]:
        """Scan and list all uploaded documents."""
        documents = []
        root_path = Path(self.documents_root)
        
        if not root_path.exists():
            logger.error(f"Documents folder not found: {self.documents_root}")
            return documents
        
        # Scan all user folders
        for user_folder in sorted(root_path.iterdir()):
            if user_folder.is_dir() and user_folder.name != 'open-mode-user':
                user_id = user_folder.name
                
                # Get all files in user folder
                for doc_file in sorted(user_folder.iterdir()):
                    if doc_file.is_file() and not doc_file.name.startswith('.'):
                        documents.append({
                            'doc_id': doc_file.stem[:20],  # Use first 20 chars of filename
                            'user_id': user_id,
                            'filename': doc_file.name,
                            'filepath': str(doc_file),
                            'size': doc_file.stat().st_size
                        })
        
        return documents
    
    def extract_text_from_file(self, filepath: str) -> str:
        """Extract text content from various file types."""
        try:
            if filepath.lower().endswith('.pdf'):
                return self._extract_pdf_text(filepath)
            elif filepath.lower().endswith(('.jpg', '.jpeg', '.png')):
                return self._extract_image_text(filepath)
            elif filepath.lower().endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # Try as text file
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Error extracting text from {filepath}: {e}")
            return f"[Unable to extract text from {filepath}]"
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF."""
        text = []
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num, page in enumerate(pdf_reader.pages[:5]):  # First 5 pages
                    try:
                        text.append(page.extract_text())
                    except:
                        pass
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            return ""
    
    def _extract_image_text(self, image_path: str) -> str:
        """Extract text from image using OCR."""
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except:
            # Fallback if OCR not available
            return f"[Image file: {image_path}]"
    
    async def analyze_document(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """Run auto mode analysis on a single document."""
        try:
            from app.services.auto_mode_orchestrator import AutoModeOrchestrator
            
            logger.info(f"Analyzing: {doc_info['filename']}")
            
            # Extract text
            doc_content = self.extract_text_from_file(doc_info['filepath'])
            
            if not doc_content or len(doc_content.strip()) < 100:
                logger.warning(f"Insufficient content: {doc_info['filename']}")
                return {
                    'status': 'skipped',
                    'reason': 'insufficient_content',
                    **doc_info
                }
            
            # Run analysis
            orchestrator = AutoModeOrchestrator()
            results = await orchestrator.run_full_auto_analysis(
                doc_id=doc_info['doc_id'],
                user_id=doc_info['user_id'],
                document_content=doc_content,
                filename=doc_info['filename'],
                document_metadata={
                    'uploaded_by': doc_info['user_id'],
                    'file_size': doc_info['size']
                }
            )
            
            return {
                'status': 'complete',
                **doc_info,
                'analysis': results
            }
        
        except Exception as e:
            logger.error(f"Error analyzing {doc_info['filename']}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                **doc_info
            }
    
    async def run_batch_analysis(self, limit: int = None) -> List[Dict[str, Any]]:
        """Run analysis on all documents."""
        documents = self.get_uploaded_documents()
        
        if limit:
            documents = documents[:limit]
        
        logger.info(f"Starting batch analysis of {len(documents)} document(s)")
        
        # Run analyses concurrently
        tasks = [self.analyze_document(doc) for doc in documents]
        results = await asyncio.gather(*tasks)
        
        self.results = results
        return results
    
    def generate_batch_report(self) -> Dict[str, Any]:
        """Generate comprehensive batch report."""
        total_docs = len(self.results)
        completed = sum(1 for r in self.results if r['status'] == 'complete')
        failed = sum(1 for r in self.results if r['status'] == 'error')
        skipped = sum(1 for r in self.results if r['status'] == 'skipped')
        
        # Aggregate statistics
        totals = {
            'timeline_events': 0,
            'calendar_events': 0,
            'complaints': 0,
            'rights': 0,
            'missteps': 0,
            'tactics': 0
        }
        
        all_actions = []
        all_urgent = []
        
        for result in self.results:
            if result.get('status') == 'complete':
                summary = result.get('summary') or result.get('analysis', {}).get('summary', {}) or {}
                
                if summary:
                    totals['timeline_events'] += summary.get('timeline_events', 0) if summary else 0
                    totals['calendar_events'] += summary.get('calendar_events', 0) if summary else 0
                    totals['complaints'] += summary.get('complaints_identified', 0) if summary else 0
                    totals['rights'] += summary.get('rights_count', 0) if summary else 0
                    totals['missteps'] += summary.get('missteps_count', 0) if summary else 0
                    totals['tactics'] += summary.get('tactics_recommended', 0) if summary else 0
                    
                    all_actions.extend(summary.get('recommended_actions', []) or [])
                    all_urgent.extend(summary.get('urgent_actions', []) or [])
        
        # Prioritize actions by severity
        all_urgent.sort(key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x.get('severity', 'medium'), 3))
        all_actions.sort(key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x.get('priority', 'medium'), 3))
        
        return {
            'batch_summary': {
                'total_documents': total_docs,
                'completed': completed,
                'failed': failed,
                'skipped': skipped,
                'success_rate': f"{(completed/total_docs*100):.1f}%" if total_docs > 0 else "0%"
            },
            'aggregated_statistics': totals,
            'all_urgent_actions': all_urgent[:10],  # Top 10
            'top_recommended_actions': all_actions[:10],  # Top 10
            'documents_analyzed': [
                {
                    'filename': r['filename'],
                    'status': r['status'],
                    'summary': r.get('analysis', {}).get('summary') if r['status'] == 'complete' else None
                }
                for r in self.results
            ]
        }
    
    def save_report(self, report: Dict[str, Any], output_file: str = "batch_analysis_report.json"):
        """Save report to file."""
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {output_file}")


async def main():
    """Main entry point."""
    analyzer = BatchAutoModeAnalyzer()
    
    # Run batch analysis
    results = await analyzer.run_batch_analysis(limit=5)  # Analyze first 5 docs
    
    # Generate report
    report = analyzer.generate_batch_report()
    
    # Save report
    analyzer.save_report(report)
    
    # Print summary
    print("\n" + "="*80)
    print("BATCH ANALYSIS COMPLETE")
    print("="*80)
    print(f"\n📊 SUMMARY:")
    print(f"  • Total Documents: {report['batch_summary']['total_documents']}")
    print(f"  • Completed: {report['batch_summary']['completed']}")
    print(f"  • Failed: {report['batch_summary']['failed']}")
    print(f"  • Skipped: {report['batch_summary']['skipped']}")
    print(f"  • Success Rate: {report['batch_summary']['success_rate']}")
    
    print(f"\n📈 AGGREGATED STATISTICS:")
    stats = report['aggregated_statistics']
    print(f"  • Timeline Events: {stats['timeline_events']}")
    print(f"  • Calendar Events: {stats['calendar_events']}")
    print(f"  • Complaints Identified: {stats['complaints']}")
    print(f"  • Rights Identified: {stats['rights']}")
    print(f"  • Missteps Detected: {stats['missteps']}")
    print(f"  • Tactics Recommended: {stats['tactics']}")
    
    print(f"\n⚠️  URGENT ACTIONS:")
    for i, action in enumerate(report['all_urgent_actions'][:3], 1):
        print(f"  {i}. [{action.get('severity', 'N/A').upper()}] {action.get('message', 'N/A')} ({action.get('deadline', 'N/A')})")
    
    print(f"\n🎯 TOP RECOMMENDED ACTIONS:")
    for i, action in enumerate(report['top_recommended_actions'][:3], 1):
        print(f"  {i}. {action.get('title', 'N/A')} [{action.get('priority', 'N/A').upper()}]")
    
    print(f"\n✅ Report saved to: batch_analysis_report.json")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())