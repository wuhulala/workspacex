import asyncio
import os
from pathlib import Path
from typing import Tuple

import PyPDF2
import aiohttp


def get_pdf_page_count(pdf_file_path: str) -> int:
    """
    Get the total number of pages in a PDF file
    
    Args:
        pdf_file_path (str): Path to the PDF file
        
    Returns:
        int: Total number of pages in the PDF
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        PyPDF2.PdfReadError: If the PDF file is corrupted or cannot be read
    """
    try:
        with open(pdf_file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {pdf_file_path}")
    except Exception as e:
        raise PyPDF2.PdfReadError(f"Error reading PDF file: {str(e)}")


async def parse_pdf_to_markdown(pdf_file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Parse PDF file to markdown format using remote API with streaming upload
    
    Args:
        pdf_file_path (str): Path to the PDF file to parse
        chunk_size (int): Size of chunks to read file in bytes (default: 1MB)
        
    Returns:
        str: Markdown content extracted from the PDF
        
    Example:
        curl -X 'POST' \
      'http://192.168.0.21:8001/marker/upload' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -F 'page_range=0' \
      -F 'force_ocr=false' \
      -F 'paginate_output=false' \
      -F 'output_format=markdown' \
      -F 'file=@🛠️ Java JAR 修改指南 _ Open WebUI.pdf;type=application/pdf'
    """
    # Get PDF page count before uploading
    try:
        page_count = get_pdf_page_count(pdf_file_path)
        print(f"📄 PDF has {page_count} pages")
    except Exception as e:
        print(f"⚠️ Warning: Could not get page count: {e}")
        page_count = 0
    
    # Check file size
    file_size = Path(pdf_file_path).stat().st_size
    print(f"📊 File size: {file_size / (1024*1024):.2f} MB")
    
    # 1. upload pdf to server
    url = os.getenv("MARKER_API_URL")
    
    # Prepare form data with streaming
    data = aiohttp.FormData()
    data.add_field('page_range', f'0-{page_count-1}')
    data.add_field('force_ocr', 'false')
    data.add_field('paginate_output', 'false')
    data.add_field('output_format', 'markdown')
    
    # Add file with streaming to avoid memory overflow
    filename = Path(pdf_file_path).name
    data.add_field('file', 
                   open(pdf_file_path, 'rb'),  # File object for streaming
                   filename=filename, 
                   content_type='application/pdf')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()
                print(result)
                return result.get('content', '')  # Return the markdown content from response
    finally:
        # Ensure file is closed
        for field in data._fields:
            if hasattr(field[1], 'close'):
                field[1].close()


async def parse_pdf_to_zip(pdf_file_path: str, output_dir: str = None, page_count: int = -1) -> Tuple[str, str]:
    """
    Parse PDF file and save the returned zip file
    
    Args:
        pdf_file_path (str): Path to the PDF file to parse
        output_dir (str): Directory to save the zip file (default: same directory as PDF)
        
    Returns:
        str: Path to the saved zip file
        
    Example:
        curl -X 'POST' \
      'http://192.168.0.21:8001/marker/upload/zip' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -F 'page_range=0' \
      -F 'force_ocr=false' \
      -F 'paginate_output=false' \
      -F 'output_format=markdown' \
      -F 'file=@🛠️ Java JAR 修改指南 _ Open WebUI.pdf;type=application/pdf'
    """
    # Get PDF page count before uploading
    try:
        if page_count < 0:
            page_count = get_pdf_page_count(pdf_file_path)
        print(f"📄 PDF resolve {page_count} pages")
    except Exception as e:
        print(f"⚠️ Warning: Could not get page count: {e}")
        page_count = 0
    
    # Check file size
    file_size = Path(pdf_file_path).stat().st_size
    print(f"📊 File size: {file_size / (1024*1024):.2f} MB")
    
    # 1. upload pdf to server
    url = os.getenv("MARKER_API_URL")
    
    # Prepare form data with streaming
    data = aiohttp.FormData()
    data.add_field('page_range', f'0-{page_count-1}')
    data.add_field('force_ocr', 'false')
    data.add_field('paginate_output', 'false')
    data.add_field('output_format', 'markdown')
    
    # Add file with streaming to avoid memory overflow
    filename = Path(pdf_file_path).name
    data.add_field('file', 
                   open(pdf_file_path, 'rb'),  # File object for streaming
                   filename=filename, 
                   content_type='application/pdf')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                # Check if response is successful
                if response.status == 200:
                    # Get the zip file content
                    zip_content = await response.read()
                    
                    # Determine output directory
                    if output_dir is None:
                        output_dir = Path(pdf_file_path).parent
                    else:
                        output_dir = Path(output_dir)
                    
                    # Create output directory if it doesn't exist
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Generate zip filename
                    pdf_name = Path(pdf_file_path).stem
                    zip_filename = f"{pdf_name}_markdown.zip"
                    zip_path = output_dir / zip_filename
                    
                    # Save zip file
                    with open(zip_path, 'wb') as f:
                        f.write(zip_content)
                    
                    print(f"✅ Zip file saved to: {zip_path}")
                    return zip_filename, str(zip_path)
                else:
                    error_text = await response.text()
                    print(f"❌ Error: HTTP {response.status} - {error_text}")
                    return None, None
    finally:
        # Ensure file is closed
        for field in data._fields:
            if hasattr(field[1], 'close'):
                field[1].close()

if __name__ == '__main__':
    pdf_path = "/Users/xah/PycharmProjects/workspacex/src/examples/data/test.pdf"

    asyncio.run(parse_pdf_to_zip(pdf_path))