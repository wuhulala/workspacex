import uuid
import zipfile
from pathlib import Path

from workspacex import Artifact, ArtifactType
from workspacex.artifact import AttachmentFile
from workspacex.chunk.base import ChunkConfig, ChunkerFactory
from workspacex.utils import pdf
from workspacex.utils.logger import logger


class PdfArtifact(Artifact):
    def __init__(self, file_name: str, pdf_path: str, page_count: int = -1, **kwargs):
        artifact_id = f"pdf_{uuid.uuid4().hex}"
        metadata = {
            "pdf_path": pdf_path,
            "file_name": file_name,
            "page_count": page_count
        }
        super().__init__(artifact_id=artifact_id, content="", artifact_type=ArtifactType.PDF, metadata=metadata,
                         **kwargs)

    @property
    def page_count(self):
        return self.metadata.get('page_count', -1)

    @page_count.setter
    def page_count(self, page_count: int):
        self.metadata['page_count'] = page_count

    @property
    def file_name(self):
        return self.metadata.get("file_name")

    @property
    def pdf_path(self):
        return self.metadata.get("pdf_path")

    @property
    def chunker(self):
        chunk_config = ChunkConfig(
            enabled=True,
            provider="markdown"
        )

        return ChunkerFactory.get_chunker(chunk_config)

    def after_chunker(self):
        self.content = ""

    async def process_pdf(self):
        """
        Process arXiv paper: download PDF, convert to markdown, and chunk the content

        Returns:
            None: Updates the artifact with processed content and chunks
        """

        self.add_attachment_file(AttachmentFile(file_name=self.filename, file_desc="PDF file", file_path=self.pdf_path))
        logger.info(f"📎 Added PDF attachment, total attachments: {len(self.attachment_files)}")

        # 1. call api resolve pdf as markdown
        markdown_zip_filename, markdown_zip_file_path = await pdf.parse_pdf_to_zip(self.pdf_path,
                                                                                   page_count=self.page_count)
        logger.info(f"📄 Parsed PDF to markdown {markdown_zip_file_path}")
        if not markdown_zip_filename:
            raise ValueError("❌parse_pdf_to_zip No markdown zip file found")
        self.add_attachment_file(AttachmentFile(file_name=markdown_zip_filename, file_desc="Markdown zip file",
                                                file_path=markdown_zip_file_path))
        logger.info(f"📎 Added markdown zip attachment, total attachments: {len(self.attachment_files)}")

        # 3. unzip zipfile, get converted_content.markdown file
        extract_dir = Path(self.pdf_path).parent / f"extracted_{self.artifact_id}"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(markdown_zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find the markdown file in the extracted directory
        markdown_file_path = None
        for file_path in extract_dir.rglob("converted_content.markdown"):
            markdown_file_path = file_path
            break

        if not markdown_file_path:
            # Try to find .md files as fallback
            for file_path in extract_dir.rglob("*.md"):
                markdown_file_path = file_path
                break

        if not markdown_file_path:
            raise FileNotFoundError(f"❌ No markdown file found in extracted zip: {markdown_zip_file_path}")

        logger.info(f"📝 Found markdown file: {markdown_file_path}")

        # 4. Read markdown content
        with open(markdown_file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        self.content = markdown_content
        logger.info(f"📖 Read markdown content, length: {len(markdown_content)} characters")

        # 5. Set the markdown content as artifact content
        # self.content = markdown_content
        self.add_attachment_file(AttachmentFile(
            file_name="result.md",
            file_desc="Markdown content file",
            file_path=str(markdown_file_path)
        ))
        logger.info(f"📎 Added markdown content attachment, total attachments: {len(self.attachment_files)}")

        self.mark_complete()

        logger.info(f"✅ Successfully processed pdf  {self.artifact_id}")


