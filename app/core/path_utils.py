"""
Semptify Path Utilities
Normalize paths for different storage systems to prevent folder creation conflicts.
"""

import re
from typing import Union
from pathlib import Path, PurePosixPath, PureWindowsPath
import logging
logger = logging.getLogger(__name__)


def normalize_cloud_path(path: Union[str, Path]) -> str:
    """
    Normalize path for cloud storage APIs (Google Drive, Dropbox, OneDrive).
    
    All cloud APIs expect forward slashes (/) as path separators.
    Removes leading/trailing slashes and ensures consistent format.
    
    Args:
        path: Path to normalize (string or Path object)
        
    Returns:
        Normalized path with forward slashes
        
    Examples:
        >>> normalize_cloud_path("Semptify5.0\\Vault\\documents")
        'Semptify5.0/Vault/documents'
        
        >>> normalize_cloud_path("/Semptify5.0/Vault/documents/")
        'Semptify5.0/Vault/documents'
    """
    if isinstance(path, Path):
        path = str(path)
    
    # Convert all backslashes to forward slashes
    normalized = path.replace("\\", "/")
    
    # Remove leading/trailing slashes
    normalized = normalized.strip("/")
    
    # Replace multiple consecutive slashes with single slash
    normalized = re.sub(r"/+", "/", normalized)
    
    return normalized


def normalize_local_path(path: Union[str, Path]) -> str:
    """
    Normalize path for local Windows file system.
    
    Uses backslashes (\) as path separators for Windows compatibility.
    
    Args:
        path: Path to normalize (string or Path object)
        
    Returns:
        Normalized path with backslashes
        
    Examples:
        >>> normalize_local_path("Semptify5.0/Vault/documents")
        'Semptify5.0\\Vault\\documents'
    """
    if isinstance(path, Path):
        path = str(path)
    
    # Convert all forward slashes to backslashes
    normalized = path.replace("/", "\\")
    
    # Remove leading/trailing backslashes (but preserve drive letters)
    if len(normalized) > 1 and normalized[1] == ":":
        # Drive letter case - preserve drive, trim trailing
        normalized = normalized.rstrip("\\")
    else:
        # Regular path - trim both ends
        normalized = normalized.strip("\\")
    
    # Replace multiple consecutive backslashes with single backslash
    normalized = re.sub(r"\\+", "\\", normalized)
    
    return normalized


def ensure_cloud_path(path: Union[str, Path]) -> str:
    """
    Ensure path is in cloud format (forward slashes).
    Alias for normalize_cloud_path for semantic clarity.
    
    Args:
        path: Path to ensure is cloud format
        
    Returns:
        Cloud-formatted path
    """
    return normalize_cloud_path(path)


def ensure_local_path(path: Union[str, Path]) -> str:
    """
    Ensure path is in local Windows format (backslashes).
    Alias for normalize_local_path for semantic clarity.
    
    Args:
        path: Path to ensure is local format
        
    Returns:
        Local-formatted path
    """
    return normalize_local_path(path)


def split_cloud_path(path: Union[str, Path]) -> list[str]:
    """
    Split cloud path into components.
    
    Args:
        path: Cloud-formatted path
        
    Returns:
        List of path components
        
    Examples:
        >>> split_cloud_path("Semptify5.0/Vault/documents")
        ['Semptify5.0', 'Vault', 'documents']
    """
    normalized = normalize_cloud_path(path)
    return normalized.split("/") if normalized else []


def join_cloud_path(*parts: Union[str, Path]) -> str:
    """
    Join path components using cloud format (forward slashes).
    
    Args:
        *parts: Path components to join
        
    Returns:
        Joined cloud path
        
    Examples:
        >>> join_cloud_path("Semptify5.0", "Vault", "documents")
        'Semptify5.0/Vault/documents'
    """
    normalized_parts = [normalize_cloud_path(part) for part in parts if part]
    return "/".join(normalized_parts)


def get_cloud_parent(path: Union[str, Path]) -> str:
    """
    Get parent directory of cloud path.
    
    Args:
        path: Cloud-formatted path
        
    Returns:
        Parent path (empty string if no parent)
        
    Examples:
        >>> get_cloud_parent("Semptify5.0/Vault/documents")
        'Semptify5.0/Vault'
    """
    parts = split_cloud_path(path)
    return join_cloud_path(*parts[:-1]) if len(parts) > 1 else ""


def get_cloud_basename(path: Union[str, Path]) -> str:
    """
    Get basename (last component) of cloud path.
    
    Args:
        path: Cloud-formatted path
        
    Returns:
        Basename of path
        
    Examples:
        >>> get_cloud_basename("Semptify5.0/Vault/documents")
        'documents'
    """
    parts = split_cloud_path(path)
    return parts[-1] if parts else ""


def is_cloud_path(path: Union[str, Path]) -> bool:
    """
    Check if path is already in cloud format.
    
    Args:
        path: Path to check
        
    Returns:
        True if path uses forward slashes, False otherwise
    """
    if isinstance(path, Path):
        path = str(path)
    return "/" in path and "\\" not in path


def is_local_path(path: Union[str, Path]) -> bool:
    """
    Check if path is in local Windows format.
    
    Args:
        path: Path to check
        
    Returns:
        True if path uses backslashes, False otherwise
    """
    if isinstance(path, Path):
        path = str(path)
    return "\\" in path


def convert_path_format(path: Union[str, Path], target_format: str = "cloud") -> str:
    """
    Convert path between cloud and local formats.
    
    Args:
        path: Path to convert
        target_format: "cloud" or "local"
        
    Returns:
        Converted path
        
    Raises:
        ValueError: If target_format is not "cloud" or "local"
    """
    if target_format == "cloud":
        return normalize_cloud_path(path)
    elif target_format == "local":
        return normalize_local_path(path)
    else:
        raise ValueError("target_format must be 'cloud' or 'local'")


# =============================================================================
# Path Validation
# =============================================================================

def validate_cloud_path(path: Union[str, Path]) -> bool:
    """
    Validate cloud path format.
    
    Args:
        path: Path to validate
        
    Returns:
        True if valid cloud path, False otherwise
    """
    if isinstance(path, Path):
        path = str(path)
    
    # Check for invalid characters (cloud APIs typically reject these)
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    path_str = normalize_cloud_path(path)
    
    return not any(char in path_str for char in invalid_chars)


def validate_local_path(path: Union[str, Path]) -> bool:
    """
    Validate local Windows path format.
    
    Args:
        path: Path to validate
        
    Returns:
        True if valid local path, False otherwise
    """
    if isinstance(path, Path):
        path = str(path)
    
    # Check for invalid Windows filename characters
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    path_str = normalize_local_path(path)
    
    # Split path and check each component
    components = path_str.split("\\")
    for component in components:
        if component and any(char in component for char in invalid_chars):
            return False
    
    return True
