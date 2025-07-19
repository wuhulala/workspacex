"""
Full-text search module for workspacex.

This module provides full-text search capabilities for artifacts,
supporting various search engines like Elasticsearch.
"""

from .dbs.base import FulltextDB
from .factory import FulltextDBFactory, FulltextDBConfig

__all__ = ["FulltextDBFactory", "FulltextDBConfig", "FulltextDB"] 