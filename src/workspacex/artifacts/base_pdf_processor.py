import os
import zipfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from workspacex import Artifact
from workspacex.artifact import AttachmentFile
from workspacex.utils import pdf
from workspacex.utils.logger import logger


class BasePDFArtifact(Artifact):
    """
    Base class for PDF processing artifacts
    
    This class provides common PDF processing functionality that can be shared
    between different artifact types that need to process PDF documents.
    Inherits from Artifact to provide basic artifact functionality.
    """

    async def process_pdf_to_markdown(self,
                                      pdf_path: str,
                                      page_count: int = -1,
                                      use_batch_processing: bool = False,
                                      batch_size: int = 5) -> str:
        """
        Process PDF file to markdown content
        
        Args:
            pdf_path (str): Path to the PDF file
            page_count (int): Number of pages to process (-1 for all pages)
            use_batch_processing (bool): Whether to use batch processing
            batch_size (int): Number of pages per batch
            
        Returns:
            str: Markdown content extracted from the PDF
            
        Raises:
            ValueError: If PDF processing fails
            FileNotFoundError: If markdown file is not found
        """
        if use_batch_processing:
            return await self._process_pdf_in_batches(pdf_path, page_count,
                                                      batch_size)
        else:
            return await self._process_pdf_single(pdf_path, page_count)

    async def _process_pdf_single(self,
                                  pdf_path: str,
                                  page_count: int = -1) -> str:
        """
        Process PDF file in a single operation
        
        Args:
            pdf_path (str): Path to the PDF file
            page_count (int): Number of pages to process
            
        Returns:
            str: Markdown content
        """
        logger.info(f"📄 Processing PDF in single operation: {pdf_path}")

        # Convert PDF to markdown
        markdown_zip_filename, markdown_zip_file_path = await pdf.parse_pdf_to_zip(
            pdf_path, page_count=page_count)
        if not markdown_zip_filename or not markdown_zip_file_path:
            raise ValueError(
                f"❌ Failed to convert PDF to markdown: {pdf_path}")

        logger.info(f"📄 Parsed PDF to markdown {markdown_zip_file_path}")

        # Add the markdown zip as an attachment
        self.add_attachment_file(
            AttachmentFile(file_name=markdown_zip_filename,
                           file_desc="Markdown zip file",
                           file_path=markdown_zip_file_path))
        logger.info(f"📎 Added markdown zip attachment")

        # Extract markdown content from zip
        markdown_content = await self._extract_markdown_from_zip(
            markdown_zip_file_path, pdf_path, "single")

        # Clean up zip file
        if os.path.exists(markdown_zip_file_path):
            os.remove(markdown_zip_file_path)

        return markdown_content

    async def _process_pdf_in_batches(self,
                                      pdf_path: str,
                                      page_count: int = -1,
                                      batch_size: int = 5) -> str:
        """
        Process PDF file in batches to avoid memory issues
        
        Args:
            pdf_path (str): Path to the PDF file
            page_count (int): Number of pages to process
            batch_size (int): Number of pages per batch
            
        Returns:
            str: Merged markdown content from all batches
        """
        # Get PDF page count
        try:
            from workspacex.utils.pdf import get_pdf_page_count
            total_pages = get_pdf_page_count(pdf_path)
            logger.info(f"📄 PDF has {total_pages} pages")
        except Exception as e:
            logger.warning(f"⚠️ Could not get page count, using default: {e}")
            total_pages = 50  # Default fallback

        # Override with user-specified page count if provided
        if page_count > 0:
            total_pages = min(total_pages, page_count)
            logger.info(f"📄 Processing limited to {total_pages} pages")

        # Batch process PDF pages
        all_markdown_content = []
        batch_results = []

        logger.info(
            f"🔄 Starting batch processing: {total_pages} pages in batches of {batch_size}"
        )

        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            batch_pages = f"{batch_start}-{batch_end-1}"

            logger.info(
                f"📦 Processing batch: pages {batch_pages} ({batch_start+1}-{batch_end} of {total_pages})"
            )

            try:
                # Process this batch
                batch_markdown = await self._process_pdf_batch(
                    pdf_path, batch_pages, batch_start, batch_end)

                if batch_markdown:
                    all_markdown_content.append(batch_markdown)
                    batch_results.append({
                        'pages': batch_pages,
                        'content': batch_markdown,
                        'status': 'success'
                    })
                    logger.info(
                        f"✅ Batch {batch_pages} processed successfully")
                else:
                    batch_results.append({
                        'pages': batch_pages,
                        'content': '',
                        'status': 'failed'
                    })
                    logger.warning(f"⚠️ Batch {batch_pages} processing failed")

            except Exception as e:
                logger.error(f"❌ Error processing batch {batch_pages}: {e}")
                batch_results.append({
                    'pages': batch_pages,
                    'content': '',
                    'status': 'failed',
                    'error': str(e)
                })

            # Add small delay between batches to avoid overwhelming the API
            import asyncio
            await asyncio.sleep(1)

        # Merge all batch results
        if all_markdown_content:
            merged_content = self._merge_batch_content(all_markdown_content,
                                                       total_pages)

            # Save merged content as attachment
            merged_file_path = Path(
                pdf_path).parent / f"merged_{self.artifact_id}.md"
            with open(merged_file_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)

            self.add_attachment_file(
                AttachmentFile(
                    file_name="result.md",
                    file_desc="Merged markdown content from all batches",
                    file_path=str(merged_file_path)))

            logger.info(
                f"📖 Merged content from {len(all_markdown_content)} batches, total length: {len(merged_content)} characters"
            )

            # Add batch processing summary to metadata
            self.metadata.update({
                'batch_processing': {
                    'total_pages':
                    total_pages,
                    'batch_size':
                    batch_size,
                    'total_batches':
                    len(batch_results),
                    'successful_batches':
                    len([r for r in batch_results
                         if r['status'] == 'success']),
                    'failed_batches':
                    len([r for r in batch_results if r['status'] == 'failed']),
                    'batch_results':
                    batch_results
                }
            })

            return merged_content
        else:
            raise ValueError("❌ All batches failed, no content was processed")

    async def _process_pdf_batch(self, pdf_path: str, page_range: str,
                                 start_page: int,
                                 end_page: int) -> Optional[str]:
        """
        Process a single batch of PDF pages
        
        Args:
            pdf_path (str): Path to the PDF file
            page_range (str): Page range string (e.g., "0-4")
            start_page (int): Starting page number (0-based)
            end_page (int): Ending page number (exclusive)
            
        Returns:
            Optional[str]: Markdown content for this batch, or None if failed
        """
        try:
            # Call API to process this batch
            markdown_zip_filename, markdown_zip_file_path = await pdf.parse_pdf_to_zip(
                pdf_path, page_count=end_page - start_page)

            if not markdown_zip_filename or not markdown_zip_file_path:
                logger.warning(
                    f"⚠️ No markdown zip file returned for batch {page_range}")
                return None

            # Verify the zip file exists and is valid
            if not os.path.exists(markdown_zip_file_path):
                logger.warning(
                    f"⚠️ Markdown zip file not found for batch {page_range}")
                return None

            # Check if file is actually a zip file
            try:
                with zipfile.ZipFile(markdown_zip_file_path, 'r') as test_zip:
                    test_zip.testzip()
            except zipfile.BadZipFile:
                # If it's not a zip file, check what it actually contains
                try:
                    with open(markdown_zip_file_path, 'r',
                              encoding='utf-8') as f:
                        content = f.read(1000)
                        logger.error(
                            f"❌ Batch {page_range}: File is not a valid zip file. Content preview: {content[:200]}..."
                        )
                        return None
                except UnicodeDecodeError:
                    file_size = os.path.getsize(markdown_zip_file_path)
                    logger.error(
                        f"❌ Batch {page_range}: File is not a valid zip file (size: {file_size} bytes)"
                    )
                    return None

            # Extract markdown content from zip
            markdown_content = await self._extract_markdown_from_zip(
                markdown_zip_file_path, pdf_path,
                f"batch_{start_page}_{end_page}")

            # Clean up zip file
            if os.path.exists(markdown_zip_file_path):
                os.remove(markdown_zip_file_path)

            return markdown_content

        except Exception as e:
            logger.error(f"❌ Error processing batch {page_range}: {e}")
            return None

    async def _extract_markdown_from_zip(self, zip_file_path: str,
                                         pdf_path: str,
                                         extract_suffix: str) -> str:
        """
        Extract markdown content from a zip file
        
        Args:
            zip_file_path (str): Path to the zip file
            pdf_path (str): Path to the original PDF file
            extract_suffix (str): Suffix for the extraction directory
            
        Returns:
            str: Extracted markdown content
            
        Raises:
            FileNotFoundError: If no markdown file is found
        """
        # Extract markdown content from zip
        extract_dir = Path(pdf_path).parent / f"extracted_{extract_suffix}"
        extract_dir.mkdir(exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find the markdown file
            markdown_file_path = None

            # First try to find converted_content.markdown
            for file_path in extract_dir.rglob("converted_content.markdown"):
                markdown_file_path = file_path
                break

            # If not found, try to find any .md file
            if not markdown_file_path:
                for file_path in extract_dir.rglob("*.md"):
                    markdown_file_path = file_path
                    break

            if not markdown_file_path:
                raise FileNotFoundError(
                    f"❌ No markdown file found in extracted zip: {zip_file_path}"
                )

            logger.info(f"📝 Found markdown file: {markdown_file_path}")

            # Read markdown content
            with open(markdown_file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            return markdown_content

        finally:
            # Clean up extraction directory
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

    def _merge_batch_content(self, batch_contents: List[str],
                             total_pages: int) -> str:
        """
        Merge content from multiple batches into a single document
        
        Args:
            batch_contents (List[str]): List of markdown content from each batch
            total_pages (int): Total number of pages in the PDF
            
        Returns:
            str: Merged markdown content
        """
        if not batch_contents:
            return ""

        # Add header with processing information
        header = f"""# PDF Document: {self.artifact_id}

> **Processing Information:**
> - Total Pages: {total_pages}
> - Processed in {len(batch_contents)} batches
> - Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""

        # Merge all batch contents
        merged = header + "\n\n".join(batch_contents)

        # Add footer
        footer = f"""

---

*Document processed using batch processing to optimize memory usage.*
"""

        return merged + footer
