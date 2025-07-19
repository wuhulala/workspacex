
from pydantic import BaseModel

from workspacex.vector.dbs.base import VectorDB


class VectorDBConfig(BaseModel):
    provider: str = "chroma"
    config: dict = {}
    
    @classmethod
    def from_config(cls, config: dict):
        if not config:
            return None
        return cls(
            provider=config.get("provider", "chroma"),
            config=config.get("config", {})
        )


class VectorDBFactory:

    @staticmethod
    def get_vector_db(vector_db_config: VectorDBConfig) -> VectorDB:
        if vector_db_config.provider == "chroma":
            from workspacex.vector.dbs.chroma import ChromaVectorDB
            return ChromaVectorDB(vector_db_config.config)
        else:
            raise ValueError(f"Vector database {vector_db_config.provider} is not supported")