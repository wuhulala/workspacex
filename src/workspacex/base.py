from pydantic import Field, BaseModel

from workspacex.chunk.base import ChunkConfig
from workspacex.config import CHROMA_CLIENT_AUTH_PROVIDER, \
    CHROMA_CLIENT_AUTH_CREDENTIALS, CHROMA_HTTP_HOST, CHROMA_HTTP_PORT, CHROMA_HTTP_SSL, CHROMA_HTTP_HEADERS, \
    CHROMA_TENANT, CHROMA_DATABASE, CHROMA_DATA_PATH, WORKSPACEX_RERANKER_MODEL_NAME, WORKSPACEX_RERANKER_BASE_URL, \
    WORKSPACEX_RERANKER_API_KEY, WORKSPACEX_RERANKER_PROVIDER
from workspacex.config import WORKSPACEX_CHUNK_OVERLAP, WORKSPACEX_CHUNK_SIZE, WORKSPACEX_CHUNK_TEXT_SPLITTER, \
    WORKSPACEX_EMBEDDING_API_BASE_URL, WORKSPACEX_EMBEDDING_API_KEY, WORKSPACEX_EMBEDDING_BATCH_SIZE, \
    WORKSPACEX_EMBEDDING_CONTEXT_LENGTH, WORKSPACEX_EMBEDDING_DIMENSIONS, WORKSPACEX_EMBEDDING_MODEL, \
    WORKSPACEX_EMBEDDING_PROVIDER, WORKSPACEX_EMBEDDING_TIMEOUT, WORKSPACEX_ENABLE_HYBRID_SEARCH, \
    WORKSPACEX_HYBRID_SEARCH_THRESHOLD, WORKSPACEX_HYBRID_SEARCH_TOP_K, WORKSPACEX_VECTOR_DB_PROVIDER, \
    WORKSPACEX_ENABLE_CHUNKING, WORKSPACEX_ENABLE_EMBEDDING, WORKSPACEX_FULLTEXT_DB_PROVIDER, ELASTICSEARCH_HOSTS, \
    ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD, \
    ELASTICSEARCH_INDEX_PREFIX, ELASTICSEARCH_NUMBER_OF_SHARDS, ELASTICSEARCH_NUMBER_OF_REPLICAS
from workspacex.embedding.base import EmbeddingsConfig
from workspacex.fulltext.factory import FulltextDBConfig
from workspacex.reranker.base import RerankConfig
from workspacex.vector.factory import VectorDBConfig


class HybridSearchConfig(BaseModel):
    enabled: bool = Field(default=False, description="enabled flag")
    top_k: int = Field(default=10, description="Top K results")
    threshold: float = Field(default=0.8, description="Threshold for similarity search")
    
    @classmethod
    def from_config(cls, config: dict):
        """
        Create a HybridSearchConfig instance from a dictionary configuration.
        
        Args:
            config (dict): Configuration dictionary containing the following keys:
                - enabled (bool): Whether hybrid search is enabled
        """
        if not config:
            return None
        return cls(
            enabled=config.get("enabled", False),
            top_k=config.get("top_k", 10),
            threshold=config.get("threshold", 0.8)
        )

class WorkspaceConfig:
    enable_hybrid_search: bool = Field(default=False, description="Enable hybrid search")
    chunk_config: ChunkConfig = Field(default=None, description="Chunk configuration")
    embedding_config: EmbeddingsConfig = Field(default=None, description="Embedding configuration")
    vector_db_config: VectorDBConfig = Field(default=None, description="Vector database configuration")
    fulltext_db_config: FulltextDBConfig = Field(default=None, description="Full-text database configuration")
    reranker_config: RerankConfig = Field(default=None, description="Reranker configuration")

    def __init__(self, chunk_config: ChunkConfig = None
                 , embedding_config: EmbeddingsConfig = None
                 , vector_db_config: VectorDBConfig = None
                 , hybrid_search_config: HybridSearchConfig = None
                 , fulltext_db_config: FulltextDBConfig = None
                 , reranker_config: RerankConfig = None
                 ):
        if chunk_config is None:
            self.chunk_config = ChunkConfig(
                enabled=WORKSPACEX_ENABLE_CHUNKING,
                provider=WORKSPACEX_CHUNK_TEXT_SPLITTER,
                chunk_size=WORKSPACEX_CHUNK_SIZE,
                chunk_overlap=WORKSPACEX_CHUNK_OVERLAP
            )
        else:
            self.chunk_config = chunk_config

        if embedding_config is None:
            self.embedding_config = EmbeddingsConfig(
                enabled=WORKSPACEX_ENABLE_EMBEDDING,
                model_name=WORKSPACEX_EMBEDDING_MODEL,
                provider=WORKSPACEX_EMBEDDING_PROVIDER,
                api_key=WORKSPACEX_EMBEDDING_API_KEY,
                base_url=WORKSPACEX_EMBEDDING_API_BASE_URL,
            )
        else:
            self.embedding_config = embedding_config

        if vector_db_config is None:
            self.embedding_config = EmbeddingsConfig(
                enabled=WORKSPACEX_ENABLE_EMBEDDING,
                model_name=WORKSPACEX_EMBEDDING_MODEL,
                provider=WORKSPACEX_EMBEDDING_PROVIDER,
                api_key=WORKSPACEX_EMBEDDING_API_KEY,
                base_url=WORKSPACEX_EMBEDDING_API_BASE_URL,
                context_length=WORKSPACEX_EMBEDDING_CONTEXT_LENGTH,
                dimensions=WORKSPACEX_EMBEDDING_DIMENSIONS,
                batch_size=WORKSPACEX_EMBEDDING_BATCH_SIZE,
                timeout=WORKSPACEX_EMBEDDING_TIMEOUT
            )
        else:
            self.embedding_config = embedding_config

        if vector_db_config is None:
            self.vector_db_config = VectorDBConfig(
                provider=WORKSPACEX_VECTOR_DB_PROVIDER,
                config={
                    "allow_reset": True,
                    "anonymized_telemetry": False,
                    "chroma_client_auth_provider": CHROMA_CLIENT_AUTH_PROVIDER if CHROMA_CLIENT_AUTH_PROVIDER else None,
                    "chroma_client_auth_credentials": CHROMA_CLIENT_AUTH_CREDENTIALS if CHROMA_CLIENT_AUTH_CREDENTIALS else None,
                    "http_host": CHROMA_HTTP_HOST if CHROMA_HTTP_HOST else None,
                    "http_port": CHROMA_HTTP_PORT if CHROMA_HTTP_PORT else None,
                    "http_ssl": CHROMA_HTTP_SSL if CHROMA_HTTP_SSL else None,
                    "http_headers": CHROMA_HTTP_HEADERS if CHROMA_HTTP_HEADERS else None,
                    "tenant": CHROMA_TENANT if CHROMA_TENANT else None,
                    "database": CHROMA_DATABASE if CHROMA_DATABASE else None,
                    "data_path": CHROMA_DATA_PATH if CHROMA_DATA_PATH else None
                }
            )
        else:
            self.vector_db_config = vector_db_config

        if hybrid_search_config is None:
            self.hybrid_search_config = HybridSearchConfig(
                enabled=WORKSPACEX_ENABLE_HYBRID_SEARCH,
                top_k=WORKSPACEX_HYBRID_SEARCH_TOP_K,
                threshold=WORKSPACEX_HYBRID_SEARCH_THRESHOLD
            )
        else:
            self.hybrid_search_config = hybrid_search_config

        if fulltext_db_config is None:
            # Parse Elasticsearch hosts and remove http:// prefix if present
            hosts = ELASTICSEARCH_HOSTS.split(",") if "," in ELASTICSEARCH_HOSTS else ELASTICSEARCH_HOSTS
            cleaned_hosts = []
            if isinstance(hosts,list) and len(hosts) > 1:
                for host in hosts:
                    cleaned_hosts.append(host)
            else:
                cleaned_hosts = hosts
            
            self.fulltext_db_config = FulltextDBConfig(
                provider=WORKSPACEX_FULLTEXT_DB_PROVIDER,
                config={
                    "hosts": cleaned_hosts,
                    "username": ELASTICSEARCH_USERNAME if ELASTICSEARCH_USERNAME else None,
                    "password": ELASTICSEARCH_PASSWORD if ELASTICSEARCH_PASSWORD else None,
                    "index_prefix": ELASTICSEARCH_INDEX_PREFIX,
                    "number_of_shards": ELASTICSEARCH_NUMBER_OF_SHARDS,
                    "number_of_replicas": ELASTICSEARCH_NUMBER_OF_REPLICAS
                }
            )
        else:
            self.fulltext_db_config = fulltext_db_config

        if reranker_config is None:
            self.reranker_config = RerankConfig(
                provider=WORKSPACEX_RERANKER_PROVIDER,
                base_url=WORKSPACEX_RERANKER_BASE_URL,
                api_key=WORKSPACEX_RERANKER_API_KEY,
                model_name=WORKSPACEX_RERANKER_MODEL_NAME,
            )
        else:
            self.reranker_config = reranker_config

    @classmethod
    def from_config(cls, config: dict):
        return cls(
            chunk_config=ChunkConfig.from_config(config.get("chunk_config")) if config else None,
            embedding_config=EmbeddingsConfig.from_config(config.get("embedding_config")) if config else None,
            vector_db_config=VectorDBConfig.from_config(config.get("vector_db_config")) if config else None,
            hybrid_search_config=HybridSearchConfig.from_config(config.get("hybrid_search_config")) if config else None,
            fulltext_db_config=FulltextDBConfig.from_config(config.get("fulltext_db_config")) if config else None,
            reranker_config=RerankConfig.from_config(config.get("reranker_config")) if config else None
        )

    def to_dict(self):
        return {
            "chunk_config": self.chunk_config.model_dump(),
            "embedding_config": self.embedding_config.model_dump(),
            "vector_db_config": self.vector_db_config.model_dump(),
            "hybrid_search_config": self.hybrid_search_config.model_dump(),
            "fulltext_db_config": self.fulltext_db_config.model_dump(),
            "reranker_config": self.reranker_config.model_dump()
        }
