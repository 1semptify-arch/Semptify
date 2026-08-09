"""
Litigation Intelligence System (LIS) - Justice-Grade Legal Intelligence
================================================================

Complete litigation intelligence system for housing rights cases.
Extracts, analyzes, and visualizes legal data from Minnesota courts.
"""

import logging

from .court_scraper import CourtScraperPack
from .entity_normalizer import EntityNormalizer
from .graph_engine import GraphEngine
from .gui_butler import GUIButlerIntegration
from .intelligence_engine import LitigationIntelligenceEngine
from .reporting_layer import ReportingLayer
from .scheduler import LitigationScheduler
from .storage_layer import LitigationStorageLayer

logger = logging.getLogger(__name__)

__all__ = [
    "CourtScraperPack",
    "EntityNormalizer",
    "LitigationIntelligenceEngine",
    "GraphEngine",
    "LitigationStorageLayer",
    "ReportingLayer",
    "GUIButlerIntegration",
    "LitigationScheduler",
]
