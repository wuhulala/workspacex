
from pydantic import BaseModel

from workspacex.vector.dbs.base import VectorDB


class VectorDBConfig(BaseModel):
    provider: str = "chroma"


class VectorDBFactory:

    @staticmethod
    def get_vector_db(config: VectorDBConfig) -> VectorDB:
        if config.provider == "chroma":
            from workspacex.vector.dbs.chroma import ChromaVectorDB
            return ChromaVectorDB()
        else:
            raise ValueError(f"Vector database {config.provider} is not supported")