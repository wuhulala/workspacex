from typing import Optional, List, Dict, Any

from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import bulk

from workspacex.fulltext.dbs.base import FulltextDB, FulltextSearchResult, FulltextSearchResults
from workspacex.utils.logger import logger


class ElasticsearchFulltextDB(FulltextDB):
    """Elasticsearch implementation of full-text search database."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Elasticsearch client.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary containing:
                - hosts: List of Elasticsearch hosts
                - username: Elasticsearch username
                - password: Elasticsearch password
                - index_prefix: Prefix for index names
                - number_of_shards: Number of shards for indices
                - number_of_replicas: Number of replicas for indices
                - use_chinese_analyzer: Whether to use Chinese analyzer (ik_max_word/ik_smart)
        """
        self.config = config
        self.hosts = config.get("hosts", ["http://localhost:9200"])
        self.username = config.get("username")
        self.password = config.get("password")
        self.index_prefix = config.get("index_prefix", "workspacex")
        self.number_of_shards = config.get("number_of_shards", 1)
        self.number_of_replicas = config.get("number_of_replicas", 0)
        self.use_chinese_analyzer = config.get("use_chinese_analyzer", True)
        
        # Initialize Elasticsearch client
        try:
            if self.username and self.password:
                self.es = Elasticsearch(
                    hosts=self.hosts,
                    basic_auth=(self.username, self.password),
                    verify_certs=False,
                    ssl_show_warn=False,
                    max_retries=3,
                    retry_on_timeout=True
                )
            else:
                self.es = Elasticsearch(
                    self.hosts,
                    max_retries=3,
                    retry_on_timeout=True
                )

            # Test connection
            if not self.es.ping():
                raise ConnectionError(f"Failed to connect to Elasticsearch at {self.hosts}: info is {self.es.info()}")
                
            logger.info(f"✅ Connected to Elasticsearch at {self.hosts}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Elasticsearch client: {e}")
            logger.error(f"   Hosts: {self.hosts}")
            logger.error(f"   Username: {self.username}")
            raise ConnectionError(f"Failed to connect to Elasticsearch: {e}")
    
    def _get_index_name(self, index_name: str) -> str:
        """Get the full index name with prefix.
        
        Args:
            index_name (str): Base index name
            
        Returns:
            str: Full index name with prefix
        """
        return f"{self.index_prefix}_{index_name}"
    
    def has_index(self, index_name: str) -> bool:
        """Check if an index exists.
        
        Args:
            index_name (str): Name of the index
            
        Returns:
            bool: True if index exists, False otherwise
        """
        try:
            return self.es.indices.exists(index=self._get_index_name(index_name))
        except Exception as e:
            logger.error(f"Error checking index existence: {e}")
            return False
    
    def delete_index(self, index_name: str):
        """Delete an index.
        
        Args:
            index_name (str): Name of the index to delete
        """
        try:
            full_index_name = self._get_index_name(index_name)
            if self.es.indices.exists(index=full_index_name):
                self.es.indices.delete(index=full_index_name)
                logger.info(f"Deleted index: {full_index_name}")
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {e}")
    
    def _create_index_if_not_exists(self, index_name: str):
        """Create index if it doesn't exist.
        
        Args:
            index_name (str): Name of the index
        """
        full_index_name = self._get_index_name(index_name)
        
        if not self.es.indices.exists(index=full_index_name):
            # Choose analyzer based on configuration
            if self.use_chinese_analyzer:
                content_analyzer = "ik_max_word"
                content_search_analyzer = "ik_smart"
                description_analyzer = "ik_max_word"
                description_search_analyzer = "ik_smart"
                logger.info(f"🔤 Using Chinese analyzer (ik_max_word/ik_smart) for index: {full_index_name}")
            else:
                content_analyzer = "standard"
                content_search_analyzer = "standard"
                description_analyzer = "standard"
                description_search_analyzer = "standard"
                logger.info(f"🔤 Using standard analyzer for index: {full_index_name}")
            
            # Define index mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "content": {
                            "type": "text",
                            "analyzer": content_analyzer,
                            "search_analyzer": content_search_analyzer
                        },
                        "artifact_id": {
                            "type": "keyword"
                        },
                        "chunk_id": {
                            "type": "keyword"
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "artifact_type": {
                                    "type": "keyword"
                                },
                                "description": {
                                    "type": "text",
                                    "analyzer": description_analyzer,
                                    "search_analyzer": description_search_analyzer
                                },
                                "filename": {
                                    "type": "keyword"
                                },
                                "chunk_index": {
                                    "type": "long"
                                },
                                "chunk_size": {
                                    "type": "long"
                                },
                                "chunk_overlap": {
                                    "type": "long"
                                },
                                "content_size": {
                                    "type": "long"
                                }
                            },
                            "dynamic": True
                        },
                        "created_at": {
                            "type": "date"
                        },
                        "updated_at": {
                            "type": "date"
                        }
                    }
                },
                "settings": {
                    "number_of_shards": self.number_of_shards,
                    "number_of_replicas": self.number_of_replicas
                }
            }
            
            self.es.indices.create(index=full_index_name, body=mapping)
            logger.info(f"✅ Created index: {full_index_name}")
    
    def recreate_index(self, index_name: str):
        """Recreate index with current analyzer configuration.
        
        This method deletes the existing index and creates a new one with the current
        analyzer settings. Use this when you want to change analyzer configuration.
        
        Args:
            index_name (str): Name of the index to recreate
        """
        try:
            full_index_name = self._get_index_name(index_name)
            
            # Delete existing index if it exists
            if self.es.indices.exists(index=full_index_name):
                self.es.indices.delete(index=full_index_name)
                logger.info(f"🗑️ Deleted existing index: {full_index_name}")
            
            # Create new index with current configuration
            self._create_index_if_not_exists(index_name)
            logger.info(f"🔄 Recreated index: {full_index_name}")
            
        except Exception as e:
            logger.error(f"❌ Error recreating index {index_name}: {e}")
    
    def search(
        self, 
        index_name: str, 
        query: str, 
        filter: Optional[Dict[str, Any]] = None, 
        limit: int = 10,
        offset: int = 0
    ) -> Optional[FulltextSearchResults]:
        """Search for text content based on query.
        
        Args:
            index_name (str): Name of the index
            query (str): Search query
            filter (Optional[Dict[str, Any]]): Filter conditions
            limit (int): Maximum number of results to return
            offset (int): Number of results to skip
            
        Returns:
            Optional[FulltextSearchResults]: Search results or None if index doesn't exist
        """
        try:
            full_index_name = self._get_index_name(index_name)
            
            if not self.es.indices.exists(index=full_index_name):
                return None
            
            # Build search body
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "metadata.artifact_type", "metadata.description", "metadata.filename"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ]
                    }
                },
                "from": offset,
                "size": limit,
                "highlight": {
                    "fields": {
                        "content": {
                            "pre_tags": ["<em>"],
                            "post_tags": ["</em>"]
                        }
                    }
                }
            }
            
            # Add filter if provided
            if filter:
                search_body["query"]["bool"]["filter"] = []
                for key, value in filter.items():
                    search_body["query"]["bool"]["filter"].append({
                        "term": {key: value}
                    })
            
            # Execute search
            response = self.es.search(index=full_index_name, body=search_body)
            
            # Process results
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlight = hit.get("highlight", {})
                
                # Use highlighted content if available
                content = source["content"]
                if "content" in highlight:
                    content = " ".join(highlight["content"])
                
                result = FulltextSearchResult(
                    id=hit["_id"],
                    score=hit["_score"],
                    content=content,
                    metadata=source.get("metadata", {}),
                    artifact_id=source["artifact_id"],
                    chunk_id=source.get("chunk_id")
                )
                results.append(result)
            
            return FulltextSearchResults(
                results=results,
                total=response["hits"]["total"]["value"],
                took=response["took"] / 1000.0  # Convert to seconds
            )
            
        except Exception as e:
            logger.error(f"Error searching index {index_name}: {e}")
            return None
    
    def query(
        self, 
        index_name: str, 
        filter: Dict[str, Any], 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Optional[FulltextSearchResults]:
        """Query items from the index based on filter.
        
        Args:
            index_name (str): Name of the index
            filter (Dict[str, Any]): Filter conditions
            limit (Optional[int]): Maximum number of results to return
            offset (int): Number of results to skip
            
        Returns:
            Optional[FulltextSearchResults]: Query results or None if index doesn't exist
        """
        try:
            full_index_name = self._get_index_name(index_name)
            
            if not self.es.indices.exists(index=full_index_name):
                return None
            
            # Build query body
            query_body = {
                "query": {
                    "bool": {
                        "filter": []
                    }
                },
                "from": offset,
                "size": limit or 10000  # Default to 10000 if no limit
            }
            
            # Add filters
            for key, value in filter.items():
                query_body["query"]["bool"]["filter"].append({
                    "term": {key: value}
                })
            
            # Execute query
            response = self.es.search(index=full_index_name, body=query_body)
            
            # Process results
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                result = FulltextSearchResult(
                    id=hit["_id"],
                    score=hit["_score"],
                    content=source["content"],
                    metadata=source.get("metadata", {}),
                    artifact_id=source["artifact_id"],
                    chunk_id=source.get("chunk_id")
                )
                results.append(result)
            
            return FulltextSearchResults(
                results=results,
                total=response["hits"]["total"]["value"],
                took=response["took"] / 1000.0
            )
            
        except Exception as e:
            logger.error(f"Error querying index {index_name}: {e}")
            return None
    
    def get(self, index_name: str, limit: Optional[int] = None) -> Optional[FulltextSearchResults]:
        """Get all items in the index.
        
        Args:
            index_name (str): Name of the index
            limit (Optional[int]): Maximum number of results to return
            
        Returns:
            Optional[FulltextSearchResults]: All items in the index or None if index doesn't exist
        """
        return self.query(index_name, {}, limit=limit)
    
    def insert(self, index_name: str, documents: List[Dict[str, Any]]):
        """Insert documents into the index.
        
        Args:
            index_name (str): Name of the index
            documents (List[Dict[str, Any]]): List of documents to insert
        """
        try:
            self._create_index_if_not_exists(index_name)
            full_index_name = self._get_index_name(index_name)
            
            # Prepare bulk actions
            actions = []
            for doc in documents:
                action = {
                    "_index": full_index_name,
                    "_source": doc
                }
                if "id" in doc:
                    action["_id"] = doc["id"]
                actions.append(action)
            
            # Execute bulk insert
            if actions:
                success, failed = bulk(self.es, actions, refresh=True)
                logger.info(f"Inserted {success} documents into {full_index_name}")
                if failed:
                    logger.warning(f"Failed to insert {len(failed)} documents")
                    
        except Exception as e:
            logger.error(f"Error inserting documents into {index_name}: {e}")
    
    def upsert(self, index_name: str, documents: List[Dict[str, Any]]):
        """Update or insert documents in the index.
        
        Args:
            index_name (str): Name of the index
            documents (List[Dict[str, Any]]): List of documents to upsert
        """
        try:
            self._create_index_if_not_exists(index_name)
            full_index_name = self._get_index_name(index_name)
            
            # Prepare bulk actions
            actions = []
            for doc in documents:
                action = {
                    "_index": full_index_name,
                    "_source": doc
                }
                if "id" in doc:
                    action["_id"] = doc["id"]
                actions.append(action)
            
            # Execute bulk upsert
            if actions:
                success, failed = bulk(self.es, actions, refresh=True)
                logger.info(f"Upserted {success} documents into {full_index_name}")
                if failed:
                    logger.warning(f"Failed to upsert {len(failed)} documents")
                    
        except Exception as e:
            logger.error(f"Error upserting documents into {index_name}: {e}")
    
    def delete(
        self,
        index_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
    ):
        """Delete documents from the index.
        
        Args:
            index_name (str): Name of the index
            ids (Optional[List[str]]): List of document IDs to delete
            filter (Optional[Dict[str, Any]]): Filter conditions for documents to delete
        """
        try:
            full_index_name = self._get_index_name(index_name)
            
            if not self.es.indices.exists(index=full_index_name):
                return
            
            if ids:
                # Delete by IDs
                for doc_id in ids:
                    try:
                        self.es.delete(index=full_index_name, id=doc_id)
                    except NotFoundError:
                        logger.warning(f"Document {doc_id} not found in {full_index_name}")
                logger.info(f"Deleted {len(ids)} documents from {full_index_name}")
                
            elif filter:
                # Delete by filter
                query_body = {
                    "query": {
                        "bool": {
                            "filter": []
                        }
                    }
                }
                
                for key, value in filter.items():
                    query_body["query"]["bool"]["filter"].append({
                        "term": {key: value}
                    })
                
                response = self.es.delete_by_query(index=full_index_name, body=query_body)
                deleted_count = response["deleted"]
                logger.info(f"Deleted {deleted_count} documents from {full_index_name} using filter")
                
        except Exception as e:
            logger.error(f"Error deleting documents from {index_name}: {e}")
    
    def reset(self):
        """Reset the database.
        
        This will delete all indices and document entries.
        """
        try:
            # Get all indices with the prefix
            indices = self.es.indices.get(index=f"{self.index_prefix}_*")
            for index_name in indices:
                self.es.indices.delete(index=index_name)
                logger.info(f"Deleted index: {index_name}")
        except Exception as e:
            logger.error(f"Error resetting database: {e}") 