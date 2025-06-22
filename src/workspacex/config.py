import os

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.environ.get("DATA_DIR", f"{os.path.expanduser('~')}/workspacex")


WORKSPACEX_DATA_DIR = os.environ.get("WORKSPACEX_DATA_DIR", f"{DATA_DIR}/workspacex")


####################################
# Config for Extraction
####################################

WORKSPACEX_CHUNK_SIZE = os.environ.get("WORKSPACEX_CHUNK_SIZE", "1000")
WORKSPACEX_CHUNK_OVERLAP = os.environ.get("WORKSPACEX_CHUNK_OVERLAP", "100")
WORKSPACEX_PDF_EXTRACT_IMAGES = os.environ.get("WORKSPACEX_PDF_EXTRACT_IMAGES", "False").lower() == "true"
WORKSPACEX_TEXT_SPLITTER = os.environ.get("WORKSPACEX_TEXT_SPLITTER", "")


####################################
# Config for Embedding
####################################
WORKSPACEX_EMBEDDING_PROVIDER = os.environ.get("WORKSPACEX_EMBEDDING_PROVIDER", "openai")
WORKSPACEX_EMBEDDING_MODEL = os.environ.get("WORKSPACEX_EMBEDDING_MODEL", "nomic-embed-text")
WORKSPACEX_EMBEDDING_API_KEY = os.environ.get("WORKSPACEX_EMBEDDING_API_KEY", "")
WORKSPACEX_EMBEDDING_API_BASE_URL = os.environ.get("WORKSPACEX_EMBEDDING_API_BASE_URL", "https://api.nomic.ai/v1")
WORKSPACEX_EMBEDDING_CONTEXT_LENGTH = os.environ.get("WORKSPACEX_EMBEDDING_CONTEXT_LENGTH", "8191")
WORKSPACEX_EMBEDDING_DIMENSIONS = os.environ.get("WORKSPACEX_EMBEDDING_DIMENSIONS", "1536")
WORKSPACEX_EMBEDDING_BATCH_SIZE = os.environ.get("WORKSPACEX_EMBEDDING_BATCH_SIZE", "100")
WORKSPACEX_EMBEDDING_TIMEOUT = os.environ.get("WORKSPACEX_EMBEDDING_TIMEOUT", "60")

####################################
# Config for Vector Database
####################################

WORKSPACEX_VECTOR_DB_PROVIDER = os.environ.get("WORKSPACEX_VECTOR_DB_PROVIDER", "chroma")

# Chroma
CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"

if WORKSPACEX_VECTOR_DB_PROVIDER == "chroma":
    import chromadb

    CHROMA_TENANT = os.environ.get("CHROMA_TENANT", chromadb.DEFAULT_TENANT)
    CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", chromadb.DEFAULT_DATABASE)
    CHROMA_HTTP_HOST = os.environ.get("CHROMA_HTTP_HOST", "")
    CHROMA_HTTP_PORT = int(os.environ.get("CHROMA_HTTP_PORT", "8000"))
    CHROMA_CLIENT_AUTH_PROVIDER = os.environ.get("CHROMA_CLIENT_AUTH_PROVIDER", "")
    CHROMA_CLIENT_AUTH_CREDENTIALS = os.environ.get(
        "CHROMA_CLIENT_AUTH_CREDENTIALS", ""
    )
    # Comma-separated list of header=value pairs
    CHROMA_HTTP_HEADERS = os.environ.get("CHROMA_HTTP_HEADERS", "")
    if CHROMA_HTTP_HEADERS:
        CHROMA_HTTP_HEADERS = dict(
            [pair.split("=") for pair in CHROMA_HTTP_HEADERS.split(",")]
        )
    else:
        CHROMA_HTTP_HEADERS = None
    CHROMA_HTTP_SSL = os.environ.get("CHROMA_HTTP_SSL", "false").lower() == "true"

####################################
# Config for Hybrid Search
####################################
WORKSPACEX_ENABLE_HYBRID_SEARCH = os.environ.get("WORKSPACEX_ENABLE_HYBRID_SEARCH", "").lower() == "true"
WORKSPACEX_HYBRID_SEARCH_TOP_K = os.environ.get("WORKSPACEX_HYBRID_SEARCH_TOP_K", "10")
WORKSPACEX_HYBRID_SEARCH_THRESHOLD = os.environ.get("WORKSPACEX_HYBRID_SEARCH_THRESHOLD", "0.5")


####################################
# Config for RAG
####################################

WORKSPACEX_DEFAULT_RETRIEVAL_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [id] **only when the <source> tag includes an explicit id attribute** (e.g., <source id="1">).

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [id] (e.g., [1], [2]) when the <source> tag includes an id attribute.**
- Do not cite if the <source> tag does not contain an id attribute.
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in a source with a provided id attribute, the response should include the citation like in the following example:
* "According to the study, the proposed method increases efficiency by 20% [1]."

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [id] only when the <source> tag with id attribute is present in the context.

<context>
{{CONTEXT}}
</context>

<user_query>
{{QUERY}}
</user_query>
"""


WORKSPACEX_RAG_TEMPLATE = os.environ.get("WORKSPACEX_RAG_TEMPLATE", WORKSPACEX_DEFAULT_RETRIEVAL_TEMPLATE)

