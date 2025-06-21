import json
import logging
import os
import shutil
import base64

from datetime import datetime
from pathlib import Path
from typing import Generic, Optional, TypeVar
from urllib.parse import urlparse

import requests
from pydantic import BaseModel



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
WORKSPACEX_EMBEDDING_ENGINE = os.environ.get("WORKSPACEX_EMBEDDING_ENGINE", "")
WORKSPACEX_EMBEDDING_MODEL = os.environ.get("WORKSPACEX_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
WORKSPACEX_EMBEDDING_MODEL_AUTO_UPDATE = os.environ.get("WORKSPACEX_EMBEDDING_MODEL_AUTO_UPDATE", "True").lower() == "true"
WORKSPACEX_EMBEDDING_MODEL_TRUST_REMOTE_CODE = os.environ.get("WORKSPACEX_EMBEDDING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
WORKSPACEX_EMBEDDING_BATCH_SIZE = os.environ.get("WORKSPACEX_EMBEDDING_BATCH_SIZE", "1")
WORKSPACEX_EMBEDDING_QUERY_PREFIX = os.environ.get("WORKSPACEX_EMBEDDING_QUERY_PREFIX", None)
WORKSPACEX_EMBEDDING_CONTENT_PREFIX = os.environ.get("WORKSPACEX_EMBEDDING_CONTENT_PREFIX", None)
WORKSPACEX_EMBEDDING_PREFIX_FIELD_NAME = os.environ.get("WORKSPACEX_EMBEDDING_PREFIX_FIELD_NAME", None)

####################################
# Config for Vector Database
####################################

VECTOR_DB = os.environ.get("VECTOR_DB", "chroma")

# Chroma
CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"

if VECTOR_DB == "chroma":
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
# Config for Retrieval
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


####################################
# Config for Reranking
####################################

WORKSPACEX_RERANKING_MODEL = os.environ.get("WORKSPACEX_RERANKING_MODEL", "")
WORKSPACEX_TOP_K = os.environ.get("WORKSPACEX_TOP_K", "3")
WORKSPACEX_TOP_K_RERANKER = os.environ.get("WORKSPACEX_TOP_K_RERANKER", "3")
WORKSPACEX_RELEVANCE_THRESHOLD = os.environ.get("WORKSPACEX_RELEVANCE_THRESHOLD", "0.0")


WORKSPACEX_ENABLE_HYBRID_SEARCH = os.environ.get("WORKSPACEX_ENABLE_HYBRID_SEARCH", "").lower() == "true"
WORKSPACEX_FULL_CONTEXT = os.environ.get("WORKSPACEX_FULL_CONTEXT", "False").lower() == "true"
WORKSPACEX_FILE_MAX_COUNT = os.environ.get("WORKSPACEX_FILE_MAX_COUNT", None)
WORKSPACEX_FILE_MAX_SIZE = os.environ.get("WORKSPACEX_FILE_MAX_SIZE", None)

WORKSPACEX_RAG_TEMPLATE = os.environ.get("WORKSPACEX_RAG_TEMPLATE", WORKSPACEX_DEFAULT_RETRIEVAL_TEMPLATE)

