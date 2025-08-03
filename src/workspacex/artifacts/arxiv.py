import zipfile
from pathlib import Path

from workspacex import Artifact, ArtifactType
from workspacex.artifact import AttachmentFile
from workspacex.chunk.base import ChunkConfig, ChunkerFactory
from workspacex.utils import io, pdf
from workspacex.utils.logger import logger


class ArxivArtifact(Artifact):

    def __init__(self, arxiv_id: str, page_count:int = -1, **kwargs):
        artifact_id = f"arxiv_{arxiv_id}"
        metadata = {
            "arxiv_id": arxiv_id,
            "page_count": page_count
        }
        super().__init__(artifact_id =artifact_id, content="", artifact_type=ArtifactType.ARXIV, metadata=metadata, **kwargs)

    @property
    def arxiv_id(self):
        return self.metadata.get('arxiv_id')

    @property
    def page_count(self):
        return self.metadata.get('page_count', -1)

    @page_count.setter
    def page_count(self, page_count: int):
        self.metadata['page_count'] = page_count

    @property
    def chunker(self):
        chunk_config = ChunkConfig(
            enabled=True,
            provider="markdown"
        )

        return ChunkerFactory.get_chunker(chunk_config)

    def after_chunker(self):
        self.content = ""

    async def process_arxiv(self):
        """
        Process arXiv paper: download PDF, convert to markdown, and chunk the content
        
        Returns:
            None: Updates the artifact with processed content and chunks
        """
        url = f"https://arxiv.org/pdf/{self.arxiv_id}"
        # 1. download pdf
        filename, temp_file_path = await io.download_pdf_from_url(url)
        if not filename:
            raise ValueError("❌ download_pdf_from_url failed, no filename found")
        logger.info(f"📥 Downloaded PDF from {url} to {temp_file_path}")
        self.add_attachment_file(AttachmentFile(file_name=filename, file_desc="PDF file", file_path=temp_file_path))
        logger.info(f"📎 Added PDF attachment, total attachments: {len(self.attachment_files)}")

        # 2. call api resolve pdf as markdown
        markdown_zip_filename, markdown_zip_file_path = await pdf.parse_pdf_to_zip(temp_file_path, page_count=self.page_count)
        logger.info(f"📄 Parsed PDF to markdown {markdown_zip_file_path}")
        if not markdown_zip_filename:
            raise ValueError("❌parse_pdf_to_zip No markdown zip file found")
        self.add_attachment_file(AttachmentFile(file_name=markdown_zip_filename, file_desc="Markdown zip file", file_path=markdown_zip_file_path))
        logger.info(f"📎 Added markdown zip attachment, total attachments: {len(self.attachment_files)}")

        # 3. unzip zipfile, get converted_content.markdown file
        extract_dir = Path(temp_file_path).parent / f"extracted_{self.arxiv_id}"
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

        logger.info(f"✅ Successfully processed arXiv paper {self.arxiv_id}")

    
