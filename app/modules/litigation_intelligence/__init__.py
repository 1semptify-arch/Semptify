"""
Litigation Intelligence System (LIS) - Justice-Grade Legal Intelligence
================================================================

Complete litigation intelligence system for housing rights cases.
Extracts, analyzes, and visualizes legal data from Minnesota courts.
"""

from .court_scraper import CourtScraperPack
from .entity_normalizer import EntityNormalizer
from .intelligence_engine import LitigationIntelligenceEngine
# from .graph_engine import GraphEngine  # TODO: graph_engine not implemented yet
from .storage_layer import LitigationStorageLayer
from .reporting_layer import ReportingLayer
from .gui_butler import GUIButlerIntegration
from .scheduler import LitigationScheduler
import logging
logger = logging.getLogger(__name__)

__all__ = [
    'CourtScraperPack',
    'EntityNormalizer',
    'LitigationIntelligenceEngine',
    # 'GraphEngine',  # TODO: graph_engine not implemented yet
    'LitigationStorageLayer',
    'ReportingLayer',
    'GUIButlerIntegration',
    'LitigationScheduler'
]
