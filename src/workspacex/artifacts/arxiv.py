import os
import re
from pathlib import Path
from typing import Union, Optional, Tuple, Dict, Any

from workspacex import Artifact, ArtifactType
from workspacex.artifact import ArtifactStatus, AttachmentFile
from workspacex.chunk.base import ChunkConfig, ChunkerFactory
from workspacex.utils import io
from workspacex.utils.logger import logger
from workspacex.artifacts.base_pdf_processor import BasePDFArtifact


class ArxivArtifact(BasePDFArtifact):
    """
    Represents an arXiv paper artifact
    
    This artifact type handles arXiv papers, downloading the PDF and converting to markdown
    for further processing.
    """

    @staticmethod
    def from_arxiv_id(arxiv_id_or_url: str, page_count: int = -1, **kwargs) -> 'ArxivArtifact':
        """
        Create an arXiv artifact from an arXiv ID
        """
        arxiv_id = ArxivArtifact._extract_arxiv_id(arxiv_id_or_url)
        artifact_id = kwargs.pop("artifact_id", f"arxiv_{arxiv_id}")
        if not artifact_id:
            artifact_id = f"arxiv_{arxiv_id}"
        metadata = kwargs.pop("metadata", {}).update({"arxiv_id": arxiv_id, "page_count": page_count})
        if not metadata:
            metadata = {"arxiv_id": arxiv_id, "page_count": page_count}
        artifact_type = kwargs.pop("artifact_type", ArtifactType.ARXIV)
        if not artifact_type:
            artifact_type = ArtifactType.ARXIV

        return ArxivArtifact(artifact_id=artifact_id,
                             artifact_type=artifact_type,
                             metadata=metadata,
                             content=kwargs.pop("content", ""),
                             **kwargs)


    @staticmethod
    def _extract_arxiv_id(arxiv_id_or_url: str) -> str:
        """
        Extract arXiv ID from either an ID string or URL
        
        Args:
            arxiv_id_or_url (str): arXiv ID or URL
            
        Returns:
            str: Extracted arXiv ID
            
        Raises:
            ValueError: If the input doesn't contain a valid arXiv ID
        """
        # Check if it's already just an ID (common patterns: 2307.09288, 2307.09288v1)
        if re.match(r'^\d{4}\.\d{5}(v\d+)?$', arxiv_id_or_url):
            return arxiv_id_or_url

        # Try to extract from URL
        # Patterns like:
        # - https://arxiv.org/abs/2307.09288
        # - https://arxiv.org/pdf/2307.09288.pdf
        # - https://arxiv.org/abs/2307.09288v1
        url_pattern = r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{5}(?:v\d+)?)'
        match = re.search(url_pattern, arxiv_id_or_url)

        if match:
            return match.group(1).replace('.pdf', '')

        raise ValueError(
            f"❌ Could not extract arXiv ID from input: {arxiv_id_or_url}")

    @property
    def arxiv_id(self) -> str:
        """Get the arXiv ID"""
        return self.metadata.get('arxiv_id')

    @property
    def page_count(self) -> int:
        """Get the page count to process"""
        return self.metadata.get('page_count', -1)

    @page_count.setter
    def page_count(self, page_count: int):
        """Set the page count to process"""
        self.metadata['page_count'] = page_count

    @property
    def chunker(self):
        """Get the chunker configuration for this artifact type"""
        chunk_config = ChunkConfig(enabled=True, provider="markdown")

        return ChunkerFactory.get_chunker(chunk_config)

    def after_chunker(self):
        """Clean up after chunking is complete"""
        self.content = ""

    async def post_process(self) -> None:
        """
        Post-process arXiv paper: download PDF, convert to markdown, and chunk the content
        
        Uses batch processing (5 pages per batch) to avoid GPU memory issues.
        
        Returns:
            None: Updates the artifact with processed content and chunks
        """
        logger.info(f"📄 Post-processing arXiv paper: {self.arxiv_id}")
        url = f"https://arxiv.org/pdf/{self.arxiv_id}"

        # 1. download pdf
        filename, temp_file_path = await io.download_pdf_from_url(url)
        if not filename:
            raise ValueError(
                "❌ download_pdf_from_url failed, no filename found")
        logger.info(f"📥 Downloaded PDF from {url} to {temp_file_path}")

        # Add the PDF as an attachment
        self.add_attachment_file(
            AttachmentFile(file_name=filename,
                           file_desc="PDF file",
                           file_path=temp_file_path))
        logger.info(
            f"📎 Added PDF attachment, total attachments: {len(self.attachment_files)}"
        )

        # 2. Process PDF to markdown using base class
        # Always use batch processing for arXiv papers to avoid memory issues
        try:
            markdown_content = await self.process_pdf_to_markdown(
                pdf_path=temp_file_path,
                page_count=self.page_count,
                use_batch_processing=True,
                batch_size=5)

            # Set the content
            self.content = markdown_content

            # Mark processing as complete
            self.mark_complete()
            logger.info(
                f"✅ Successfully processed arXiv paper {self.arxiv_id} using batch processing"
            )

        except Exception as e:
            logger.error(f"❌ Failed to process arXiv paper: {e}")
            raise
