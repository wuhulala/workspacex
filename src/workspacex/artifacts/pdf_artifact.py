import os
from pathlib import Path
from typing import Optional, Union, Dict, Any

from workspacex import Artifact, ArtifactType
from workspacex.artifact import AttachmentFile
from workspacex.chunk.base import ChunkConfig, ChunkerFactory
from workspacex.utils import io
from workspacex.utils.logger import logger
from workspacex.artifacts.base_pdf_processor import BasePDFArtifact


class PDFArtifact(BasePDFArtifact):
    """
    Represents a PDF document artifact
    
    This artifact type handles PDF documents, converting them to markdown
    for further processing and analysis.
    """



    @property
    def source(self) -> str:
        """Get the source of the PDF (file path or URL)"""
        return self.metadata.get('source', '')

    @property
    def is_url(self) -> bool:
        """Check if the PDF source is a URL"""
        return self.metadata.get('is_url', False)

    @property
    def file_path(self) -> Optional[str]:
        """Get the local file path if available"""
        return self.metadata.get('file_path')

    @property
    def url(self) -> Optional[str]:
        """Get the URL if available"""
        return self.metadata.get('url')

    @property
    def page_count(self) -> int:
        """Get the page count to process"""
        return self.metadata.get('page_count', -1)

    @page_count.setter
    def page_count(self, page_count: int):
        """Set the page count to process"""
        self.metadata['page_count'] = page_count

    @property
    def file_name(self) -> str:
        """Get the PDF file name"""
        return self.metadata.get('file_name', '')

    @property
    def chunker(self):
        """Get the chunker configuration for this artifact type"""
        chunk_config = ChunkConfig(
            enabled=True,
            provider="markdown"
        )
        return ChunkerFactory.get_chunker(chunk_config)

    def after_chunker(self):
        """Clean up after chunking is complete"""
        self.content = ""
        
    @staticmethod
    def from_file(file_path: str, page_count: int = -1, **kwargs) -> 'PDFArtifact':
        """
        Create a PDF artifact from a local file path
        
        Args:
            file_path (str): Local path to PDF file
            page_count (int): Number of pages to process (-1 for all pages)
            **kwargs: Additional keyword arguments for the Artifact base class
            
        Returns:
            PDFArtifact: Created PDF artifact instance
            
        Raises:
            FileNotFoundError: If the file does not exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ PDF file not found: {file_path}")
            
        file_name = os.path.basename(file_path)
        artifact_id = f"pdf_{Path(file_name).stem}"
        
        metadata = {
            "source": file_path,
            "is_url": False,
            "file_path": file_path,
            "url": None,
            "page_count": page_count,
            "file_name": file_name
        }
        
        return PDFArtifact(
            artifact_id=artifact_id,
            content="",
            artifact_type=ArtifactType.PDF,
            metadata=metadata,
            **kwargs
        )
    
    @staticmethod
    def from_url(url: str, page_count: int = -1, **kwargs) -> 'PDFArtifact':
        """
        Create a PDF artifact from a URL
        
        Args:
            url (str): URL to download PDF from
            page_count (int): Number of pages to process (-1 for all pages)
            **kwargs: Additional keyword arguments for the Artifact base class
            
        Returns:
            PDFArtifact: Created PDF artifact instance
        """
        # Extract filename from URL or use URL hash
        file_name = os.path.basename(url).split('?')[0] or f"url_pdf_{hash(url) % 10000}"
        artifact_id = f"pdf_{Path(file_name).stem}"
        
        metadata = {
            "source": url,
            "is_url": True,
            "file_path": None,
            "url": url,
            "page_count": page_count,
            "file_name": file_name
        }
        
        return PDFArtifact(
            artifact_id=artifact_id,
            content="",
            artifact_type=ArtifactType.PDF,
            metadata=metadata,
            **kwargs
        )


    async def post_process(self) -> None:
        """
        Post-process PDF document: download if needed, convert to markdown, and chunk the content
        
        Returns:
            None: Updates the artifact with processed content and chunks
            
        Raises:
            ValueError: If PDF processing fails
            FileNotFoundError: If markdown file is not found
        """
        # Step 1: Get the PDF file (download if needed)
        temp_file_path = None
        
        if self.is_url:
            # Download PDF from URL
            filename, temp_file_path = await io.download_pdf_from_url(self.url)
            if not filename or not temp_file_path:
                raise ValueError(f"❌ Failed to download PDF from URL: {self.url}")
            logger.info(f"📥 Downloaded PDF from {self.url} to {temp_file_path}")
        else:
            # Use local file
            temp_file_path = self.file_path
            filename = self.file_name
            if not os.path.exists(temp_file_path):
                raise FileNotFoundError(f"❌ PDF file not found: {temp_file_path}")
            logger.info(f"📄 Using local PDF file: {temp_file_path}")
            
        # Add the PDF as an attachment
        self.add_attachment_file(AttachmentFile(
            file_name=filename, 
            file_desc="PDF file", 
            file_path=temp_file_path
        ))
        logger.info(f"📎 Added PDF attachment, total attachments: {len(self.attachment_files)}")

        # Step 2: Process PDF to markdown using base class
        # Use batch processing for large PDFs to avoid memory issues
        use_batch_processing = self.page_count > 10 or self.page_count == -1
        
        try:
            markdown_content = await self.process_pdf_to_markdown(
                pdf_path=temp_file_path,
                page_count=self.page_count,
                use_batch_processing=use_batch_processing,
                batch_size=5
            )
            
            # Set the content
            self.content = markdown_content
            
            # Mark processing as complete
            self.mark_complete()
            logger.info(f"✅ Successfully processed PDF document: {self.file_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process PDF: {e}")
            raise
