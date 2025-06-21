from workspacex.config import VECTOR_DB

if VECTOR_DB == "chroma":
    from workspacex.vector.dbs.chroma import ChromaClient

    VECTOR_DB_CLIENT = ChromaClient()
else:
    raise ValueError(f"Vector database {VECTOR_DB} is not supported")
