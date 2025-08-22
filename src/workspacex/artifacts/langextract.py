from typing import Dict, Any

from workspacex import Artifact, ArtifactType


class LangExtractorArtifact(Artifact):

    def __init__(self, origin_artifact_id: str, extract_type: str, content: Dict[str, Any], **kwargs):
        artifact_id = f"langextract_{extract_type}_{origin_artifact_id}"
        metadata = {
            "origin_artifact_id": origin_artifact_id,
            "extract_type": extract_type
        }
        super().__init__(
            artifact_id=artifact_id,
            content=content,
            artifact_type=ArtifactType.LANGEXTRACT,
            metadata=metadata,
            **kwargs)
