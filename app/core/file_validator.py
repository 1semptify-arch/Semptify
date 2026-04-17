"""
File Validator - Security and Validation for File Uploads
=====================================================

Handles file type validation, size limits, and security checks.
"""

import logging
import mimetypes
import os
import hashlib
import magic
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FileValidationResult:
    """Result of file validation."""
    is_valid: bool
    error_message: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    security_risk: Optional[str] = None
    recommended_action: Optional[str] = None

class FileValidator:
    """Validates files for security and compliance."""
    
    # Allowed file types and their properties
    ALLOWED_TYPES = {
        # Documents
        'pdf': {
            'mime_types': ['application/pdf'],
            'max_size_mb': 50,
            'description': 'PDF document',
            'risk_level': 'low'
        },
        'doc': {
            'mime_types': ['application/msword'],
            'max_size_mb': 25,
            'description': 'Microsoft Word document',
            'risk_level': 'medium'
        },
        'docx': {
            'mime_types': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'max_size_mb': 25,
            'description': 'Microsoft Word document',
            'risk_level': 'medium'
        },
        'txt': {
            'mime_types': ['text/plain'],
            'max_size_mb': 10,
            'description': 'Plain text file',
            'risk_level': 'low'
        },
        'rtf': {
            'mime_types': ['application/rtf', 'text/rtf'],
            'max_size_mb': 10,
            'description': 'Rich text format',
            'risk_level': 'medium'
        },
        
        # Images
        'jpg': {
            'mime_types': ['image/jpeg'],
            'max_size_mb': 20,
            'description': 'JPEG image',
            'risk_level': 'low'
        },
        'jpeg': {
            'mime_types': ['image/jpeg'],
            'max_size_mb': 20,
            'description': 'JPEG image',
            'risk_level': 'low'
        },
        'png': {
            'mime_types': ['image/png'],
            'max_size_mb': 20,
            'description': 'PNG image',
            'risk_level': 'low'
        },
        'gif': {
            'mime_types': ['image/gif'],
            'max_size_mb': 10,
            'description': 'GIF image',
            'risk_level': 'low'
        },
        'tiff': {
            'mime_types': ['image/tiff', 'image/tiff-fx'],
            'max_size_mb': 50,
            'description': 'TIFF image',
            'risk_level': 'low'
        },
        'bmp': {
            'mime_types': ['image/bmp', 'image/x-bmp'],
            'max_size_mb': 20,
            'description': 'Bitmap image',
            'risk_level': 'low'
        },
        
        # Audio
        'mp3': {
            'mime_types': ['audio/mpeg', 'audio/mp3'],
            'max_size_mb': 100,
            'description': 'MP3 audio file',
            'risk_level': 'medium'
        },
        'wav': {
            'mime_types': ['audio/wav', 'audio/x-wav'],
            'max_size_mb': 200,
            'description': 'WAV audio file',
            'risk_level': 'low'
        },
        'm4a': {
            'mime_types': ['audio/mp4', 'audio/x-m4a'],
            'max_size_mb': 100,
            'description': 'M4A audio file',
            'risk_level': 'medium'
        },
        
        # Video
        'mp4': {
            'mime_types': ['video/mp4'],
            'max_size_mb': 500,
            'description': 'MP4 video file',
            'risk_level': 'medium'
        },
        'mov': {
            'mime_types': ['video/quicktime'],
            'max_size_mb': 500,
            'description': 'QuickTime video',
            'risk_level': 'medium'
        },
        'avi': {
            'mime_types': ['video/x-msvideo'],
            'max_size_mb': 500,
            'description': 'AVI video file',
            'risk_level': 'medium'
        },
        
        # Spreadsheets
        'xls': {
            'mime_types': ['application/vnd.ms-excel'],
            'max_size_mb': 25,
            'description': 'Microsoft Excel spreadsheet',
            'risk_level': 'medium'
        },
        'xlsx': {
            'mime_types': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
            'max_size_mb': 25,
            'description': 'Microsoft Excel spreadsheet',
            'risk_level': 'medium'
        },
        'csv': {
            'mime_types': ['text/csv', 'application/csv'],
            'max_size_mb': 10,
            'description': 'CSV spreadsheet',
            'risk_level': 'low'
        }
    }
    
    # Dangerous file extensions to block
    BLOCKED_EXTENSIONS = {
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar', 'app', 'deb', 'pkg',
        'dmg', 'iso', 'img', 'bin', 'run', 'sh', 'ps1', 'py', 'pl', 'rb', 'php', 'asp', 'jsp',
        'msi', 'msp', 'mst', 'cpl', 'inf', 'reg', 'scr', 'sct', 'shb', 'shs', 'url', 'vbe',
        'wsc', 'wsf', 'wsh', 'ps1xml', 'ps2', 'ps2xml', 'psc1', 'psd1', 'psdxml', 'cdxml',
        'cer', 'crt', 'der', 'p7b', 'p7c', 'p7m', 'p7s', 'spc', 'sst', 'stl'
    }
    
    # Dangerous MIME types to block
    BLOCKED_MIME_TYPES = {
        'application/x-executable', 'application/x-msdownload', 'application/x-msdos-program',
        'application/x-msi', 'application/x-sh', 'application/x-shellscript',
        'application/javascript', 'text/javascript', 'application/x-java-applet',
        'application/x-java-jnlp-file', 'application/x-java-archive', 'application/x-python-code',
        'application/x-perl', 'application/x-ruby', 'application/x-php', 'text/x-php',
        'application/x-ms-shortcut', 'application/x-lnk'
    }
    
    def __init__(self):
        self.max_total_size_mb = 1000  # Max total upload size per session
        
    def validate_file(self, file_content: bytes, filename: str, file_size: int) -> FileValidationResult:
        """Validate a file for security and compliance."""
        
        # Basic checks
        if not file_content or file_size == 0:
            return FileValidationResult(
                is_valid=False,
                error_message="File is empty"
            )
        
        # Check file extension
        file_ext = Path(filename).suffix.lower().lstrip('.')
        if file_ext in self.BLOCKED_EXTENSIONS:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File type .{file_ext} is not allowed for security reasons",
                security_risk="blocked_extension",
                recommended_action="Use a different file format"
            )
        
        # Check if file type is allowed
        if file_ext not in self.ALLOWED_TYPES:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File type .{file_ext} is not supported",
                file_type=file_ext,
                recommended_action="Use supported file formats: PDF, DOC, DOCX, TXT, JPG, PNG, MP3, MP4, etc."
            )
        
        file_type_info = self.ALLOWED_TYPES[file_ext]
        
        # Check file size
        if file_size > file_type_info['max_size_mb'] * 1024 * 1024:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File size {file_size/1024/1024:.1f}MB exceeds limit of {file_type_info['max_size_mb']}MB for {file_type_info['description']}",
                file_size=file_size,
                recommended_action="Compress the file or use a smaller version"
            )
        
        # Detect MIME type
        detected_mime = self._detect_mime_type(file_content, filename)
        
        # Validate MIME type matches extension
        if detected_mime and detected_mime not in file_type_info['mime_types']:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File content doesn't match .{file_ext} extension. Detected: {detected_mime}",
                file_type=file_ext,
                mime_type=detected_mime,
                security_risk="mime_mismatch",
                recommended_action="Ensure file has correct extension"
            )
        
        # Check for dangerous MIME types
        if detected_mime in self.BLOCKED_MIME_TYPES:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File contains dangerous content type: {detected_mime}",
                mime_type=detected_mime,
                security_risk="dangerous_mime",
                recommended_action="Use a safe file format"
            )
        
        # Additional security checks for high-risk files
        security_issues = self._check_file_security(file_content, file_ext)
        if security_issues:
            return FileValidationResult(
                is_valid=False,
                error_message=f"Security risk detected: {', '.join(security_issues)}",
                file_type=file_ext,
                security_risk=", ".join(security_issues),
                recommended_action="Scan file for viruses and try again"
            )
        
        # File is valid
        return FileValidationResult(
            is_valid=True,
            file_type=file_ext,
            file_size=file_size,
            mime_type=detected_mime,
            security_risk=file_type_info['risk_level']
        )
    
    def _detect_mime_type(self, file_content: bytes, filename: str) -> Optional[str]:
        """Detect MIME type using python-magic or fallback to mimetypes."""
        try:
            # Try python-magic first (more accurate)
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_buffer(file_content)
            
            # Validate the detected MIME type
            if detected_mime and '/' in detected_mime:
                return detected_mime
        except (ImportError, AttributeError):
            # Fallback to mimetypes
            detected_mime, _ = mimetypes.guess_type(filename)
            return detected_mime
        except Exception as e:
            logger.warning(f"MIME type detection failed: {e}")
        
        return None
    
    def _check_file_security(self, file_content: bytes, file_ext: str) -> List[str]:
        """Check for security issues in file content."""
        issues = []
        
        # Check for executable signatures
        if self._has_executable_signature(file_content):
            issues.append("executable_signature")
        
        # Check for script content
        if self._has_script_content(file_content):
            issues.append("script_content")
        
        # Check for suspicious patterns
        if self._has_suspicious_patterns(file_content):
            issues.append("suspicious_patterns")
        
        # Specific checks for document types
        if file_ext in ['doc', 'docx', 'xls', 'xlsx']:
            if self._has_macro_content(file_content):
                issues.append("macro_content")
        
        return issues
    
    def _has_executable_signature(self, file_content: bytes) -> bool:
        """Check if file has executable signature."""
        # Check for common executable signatures
        exe_signatures = [
            b'MZ',                    # Windows PE
            b'\x7fELF',              # Linux ELF
            b'\xca\xfe\xba\xbe',     # Java class
            b'\xfe\xed\xfa\xce',     # Mach-O binary (macOS)
            b'\xfe\xed\xfa\xcf',     # Mach-O binary (macOS)
        ]
        
        for signature in exe_signatures:
            if file_content.startswith(signature):
                return True
        
        return False
    
    def _has_script_content(self, file_content: bytes) -> bool:
        """Check if file contains script content."""
        script_patterns = [
            b'<script',              # HTML/JavaScript
            b'javascript:',          # JavaScript protocol
            b'vbscript:',            # VBScript
            b'powershell',           # PowerShell
            b'#!/bin/',              # Unix scripts
            b'#!/usr/bin/',          # Unix scripts
            b'eval(',                # Common in scripts
            b'exec(',                # Common in scripts
            b'system(',              # System calls
        ]
        
        content_lower = file_content.lower()
        for pattern in script_patterns:
            if pattern in content_lower:
                return True
        
        return False
    
    def _has_suspicious_patterns(self, file_content: bytes) -> bool:
        """Check for suspicious patterns in file."""
        suspicious_patterns = [
            b'base64_decode',        # Common in obfuscated code
            b'shell_exec',           # Command execution
            b'passthru',             # Command execution
            b'proc_open',            # Process execution
            b'curl_exec',            # HTTP execution
            b'create_function',      # Dynamic function creation
        ]
        
        content_lower = file_content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                return True
        
        return False
    
    def _has_macro_content(self, file_content: bytes) -> bool:
        """Check if Office document contains macros."""
        # Simple check for macro indicators in Office documents
        macro_indicators = [
            b'vbaProject',           # VBA project
            b'macros',              # General macro reference
            b'autoexec',            # Auto-exec macros
            b'Workbook_Open',        # Excel auto-open
            b'Document_Open',        # Word auto-open
        ]
        
        content_lower = file_content.lower()
        for indicator in macro_indicators:
            if indicator in content_lower:
                return True
        
        return False
    
    def get_allowed_extensions(self) -> List[str]:
        """Get list of allowed file extensions."""
        return list(self.ALLOWED_TYPES.keys())
    
    def get_file_type_info(self, extension: str) -> Optional[Dict[str, Any]]:
        """Get information about a file type."""
        extension = extension.lower().lstrip('.')
        return self.ALLOWED_TYPES.get(extension)
    
    def generate_file_hash(self, file_content: bytes) -> str:
        """Generate SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Remove path separators and dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        sanitized = ''.join(c for c in filename if c in safe_chars)
        
        # Remove leading dots and dashes
        sanitized = sanitized.lstrip('.-')
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "uploaded_file"
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:255-len(ext)] + ext
        
        return sanitized

# Global validator instance
file_validator = FileValidator()

def get_file_validator() -> FileValidator:
    """Get the global file validator instance."""
    return file_validator

def validate_upload_file(file_content: bytes, filename: str, file_size: int) -> FileValidationResult:
    """Validate uploaded file."""
    return file_validator.validate_file(file_content, filename, file_size)

def get_allowed_file_types() -> Dict[str, Dict[str, Any]]:
    """Get allowed file types with their properties."""
    return file_validator.ALLOWED_TYPES.copy()
