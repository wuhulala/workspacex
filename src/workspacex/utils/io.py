# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# reference https://github.com/google/langextract/blob/main/langextract/io.py

"""Supports Input and Output Operations for Data Annotations."""

from typing import Tuple

import requests

from workspacex.utils import progress

DEFAULT_TIMEOUT_SECONDS = 30


class InvalidDatasetError(Exception):
    """Error raised when Dataset is empty or invalid."""


def is_url(text: str) -> bool:
    """Check if the given text is a URL.

    Args:
      text: The string to check.

    Returns:
      True if the text is a URL (starts with http:// or https://), False
      otherwise.
    """
    return text.startswith('http://') or text.startswith('https://')


async def download_pdf_from_url(
        url: str,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        show_progress: bool = True,
        chunk_size: int = 8192,
) -> Tuple[str, str]:
    """
    download pdf from url, return temp file path

    """

    try:
        # Make initial request to get headers
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        # Get content length for progress bar
        total_size = int(response.headers.get('Content-Length', 0))

        filename = url.split('/')[-1][:50]

        # save as pdf temp file return file path
        temp_file_path = f"/tmp/{filename}.pdf"
        # Download content with progress bar
        chunks = []
        if show_progress and total_size > 0:
            progress_bar = progress.create_download_progress_bar(
                total_size=total_size, url=url
            )


            with open(temp_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
            progress_bar.close()
        else:
            # Download without progress bar
            with open(temp_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

        return f"{filename}.pdf",temp_file_path

    except requests.RequestException as e:
        raise requests.RequestException(
            f'Failed to download from {url}: {str(e)}'
        ) from e
    pass


def download_text_from_url(
        url: str,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        show_progress: bool = True,
        chunk_size: int = 8192,
) -> str:
    """Download text content from a URL with optional progress bar.

    Args:
      url: The URL to download from.
      timeout: Request timeout in seconds.
      show_progress: Whether to show a progress bar during download.
      chunk_size: Size of chunks to download at a time.

    Returns:
      The text content of the URL.

    Raises:
      requests.RequestException: If the download fails.
      ValueError: If the content is not text-based.
    """
    try:
        # Make initial request to get headers
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if not any(
                ct in content_type
                for ct in ['text/', 'application/json', 'application/xml']
        ):
            # Try to proceed anyway, but warn
            print(f"Warning: Content-Type '{content_type}' may not be text-based")

        # Get content length for progress bar
        total_size = int(response.headers.get('Content-Length', 0))

        filename = url.split('/')[-1][:50]

        # Download content with progress bar
        chunks = []
        if show_progress and total_size > 0:
            progress_bar = progress.create_download_progress_bar(
                total_size=total_size, url=url
            )

            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    chunks.append(chunk)
                    progress_bar.update(len(chunk))

            progress_bar.close()
        else:
            # Download without progress bar
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    chunks.append(chunk)

        # Combine chunks and decode
        content = b''.join(chunks)

        # Try to decode as text
        encodings = ['utf-8', 'latin-1', 'ascii', 'utf-16']
        text_content = None
        for encoding in encodings:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise ValueError(f'Could not decode content from {url} as text')

        # Show content summary with clean formatting
        if show_progress:
            char_count = len(text_content)
            word_count = len(text_content.split())
            progress.print_download_complete(char_count, word_count, filename)

        return text_content

    except requests.RequestException as e:
        raise requests.RequestException(
            f'Failed to download from {url}: {str(e)}'
        ) from e
