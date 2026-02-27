"""
NL Query Cache Manager

Manages caching of formatted SQL queries with metadata and persistence.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

from src.utils.path_resolver import get_data_path

logger = logging.getLogger(__name__)


class NLQueryCache:
    """Cache manager for NL-to-SQL queries with file-based persistence."""
    
    def __init__(self, max_size: int = 50, persist: bool = True):
        """
        Initialize cache with optional persistence.
        
        Args:
            max_size: Maximum number of queries to cache (default: 50)
            persist: Whether to persist cache to file (default: True)
        """
        self.max_size = max_size
        self.persist = persist
        self.queries = {}  # Dict of {id: query_data}
        
        # Get cache file path using path resolver (data/logs/nl_query_cache.json under app base)
        cache_file = get_data_path("logs", "nl_query_cache.json")
        self.cache_file = cache_file
        
        if self.persist:
            self._load_from_file()
    
    def add_query(self, nl_query: str, sql_query: str, formatted_sql: str) -> str:
        """
        Add a new query to cache.
        
        Args:
            nl_query: Original natural language query
            sql_query: Raw SQL query
            formatted_sql: Formatted SQL query for display
            
        Returns:
            Cache entry ID
        """
        # Generate unique ID
        cache_id = str(uuid.uuid4())
        
        # Create display name (first 50 chars of NL query)
        display_name = nl_query[:50] if len(nl_query) > 50 else nl_query
        if not display_name:
            display_name = sql_query[:50] if len(sql_query) > 50 else sql_query
        
        # Create cache entry
        entry = {
            "id": cache_id,
            "nl_query": nl_query,
            "sql_query": sql_query,
            "formatted_sql": formatted_sql,
            "timestamp": datetime.now().timestamp(),
            "display_name": display_name
        }
        
        # Add to cache
        self.queries[cache_id] = entry
        
        # Enforce max size (remove oldest if exceeded)
        if len(self.queries) > self.max_size:
            self._evict_oldest()
        
        # Save to file if persistence enabled
        if self.persist:
            self._save_to_file()
        
        return cache_id
    
    def get_query(self, cache_id: str) -> Optional[Dict]:
        """
        Retrieve a cached query by ID.
        
        Args:
            cache_id: Cache entry ID
            
        Returns:
            Query data dict or None if not found
        """
        return self.queries.get(cache_id)
    
    def get_all_queries(self) -> List[Dict]:
        """
        Get all cached queries, sorted by timestamp (newest first).
        
        Returns:
            List of query data dicts
        """
        queries_list = list(self.queries.values())
        # Sort by timestamp (newest first)
        queries_list.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return queries_list
    
    def clear_cache(self) -> None:
        """Clear all cached queries."""
        self.queries.clear()
        if self.persist:
            self._save_to_file()
    
    def remove_query(self, cache_id: str) -> None:
        """
        Remove a specific query from cache.
        
        Args:
            cache_id: Cache entry ID to remove
        """
        if cache_id in self.queries:
            del self.queries[cache_id]
            if self.persist:
                self._save_to_file()
    
    def _evict_oldest(self) -> None:
        """Remove the oldest query when cache exceeds max size."""
        if not self.queries:
            return
        
        # Find oldest query
        oldest_id = min(
            self.queries.keys(),
            key=lambda k: self.queries[k].get("timestamp", 0)
        )
        del self.queries[oldest_id]
    
    def _load_from_file(self) -> None:
        """Load cache from persistent storage."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    queries_list = data.get('queries', [])
                    self.queries = {q['id']: q for q in queries_list}
                    
                    # Enforce max size after loading
                    if len(self.queries) > self.max_size:
                        # Sort by timestamp and keep newest
                        sorted_queries = sorted(
                            self.queries.items(),
                            key=lambda x: x[1].get("timestamp", 0),
                            reverse=True
                        )
                        self.queries = dict(sorted_queries[:self.max_size])
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self.queries = {}
    
    def _save_to_file(self) -> None:
        """Save cache to persistent storage."""
        try:
            # Save current cache directly to JSON file
            data = {
                "version": "1.0",
                "queries": list(self.queries.values())
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
