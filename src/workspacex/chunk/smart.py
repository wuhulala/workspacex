from typing import List, Tuple
import re

from workspacex.artifact import Artifact
from .base import Chunk, ChunkConfig, ChunkerBase


class SmartChunker(ChunkerBase):
    """
    A smart chunker that splits text more evenly by considering line lengths
    and avoiding chunks that are too large or too small due to single long/short lines.
    """

    def __init__(self, config: ChunkConfig):
        super().__init__(config=config)


    async def chunk(self, artifact: Artifact) -> List[Chunk]:
        """
        Chunks the given content using smart splitting strategy.

        Args:
            artifact: The artifact to chunk.

        Returns:
            A list of `Chunk` objects.
        """
        content = artifact.content
        if not content:
            return []

        # Clean the content first
        content = self._clean_content(content)
        
        # Split content into lines
        lines = content.split(self.config.chunk_separator)
        if not lines:
            return []

        # Create chunks using smart splitting
        chunks = self._smart_split_lines(lines)
        
        # Clean each chunk
        cleaned_chunks = [self._clean_chunk(chunk) for chunk in chunks]
        
        return self._create_chunks(cleaned_chunks, artifact)

    def _smart_split_lines(self, lines: List[str]) -> List[str]:
        """
        Split lines into chunks using smart strategy.
        
        Args:
            lines: List of text lines
            
        Returns:
            List of chunk texts
        """
        chunks = []
        current_chunk = []
        current_size = 0
        overlap_buffer = []
        
        for i, line in enumerate(lines):
            line_size = len(line)
            
            # If adding this line would exceed chunk size
            if current_size + line_size > self.config.chunk_size and current_chunk:
                # Try to find a good split point within the current chunk
                chunk_text = self._create_chunk_with_smart_boundary(
                    current_chunk, self.config.chunk_size, self.config.chunk_overlap
                )
                chunks.append(chunk_text)
                
                # Prepare overlap for next chunk
                overlap_buffer = self._get_overlap_lines(current_chunk, self.config.chunk_overlap)
                current_chunk = overlap_buffer + [line]
                current_size = sum(len(l) for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_text = self.config.chunk_separator.join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks

    def _create_chunk_with_smart_boundary(self, lines: List[str], target_size: int, overlap: int) -> str:
        """
        Create a chunk with smart boundary selection.
        
        Args:
            lines: List of lines to chunk
            target_size: Target chunk size
            overlap: Overlap size
            
        Returns:
            Chunk text
        """
        if not lines:
            return ""
        
        # If lines fit within target size, return all
        total_size = sum(len(line) for line in lines)
        if total_size <= target_size:
            return self.config.chunk_separator.join(lines)
        
        # Find the best split point
        best_split = self._find_best_split_point(lines, target_size)
        
        # Create chunk up to the best split point
        chunk_lines = lines[:best_split]
        return self.separator.join(chunk_lines)

    def _find_best_split_point(self, lines: List[str], target_size: int) -> int:
        """
        Find the best split point within lines to achieve target size.
        
        Args:
            lines: List of lines
            target_size: Target chunk size
            
        Returns:
            Best split index
        """
        current_size = 0
        best_split = 0
        min_diff = float('inf')
        
        for i, line in enumerate(lines):
            line_size = len(line)
            
            # If adding this line would exceed target size
            if current_size + line_size > target_size:
                # Check if this is a better split point
                diff = abs(current_size - target_size)
                if diff < min_diff:
                    min_diff = diff
                    best_split = i
                break
            
            current_size += line_size
            
            # Check if this is a good split point (sentence or paragraph boundary)
            if self._is_good_split_point(line):
                diff = abs(current_size - target_size)
                if diff < min_diff:
                    min_diff = diff
                    best_split = i + 1
        
        # Ensure we have at least one line
        return max(1, best_split)

    def _is_good_split_point(self, line: str) -> bool:
        """
        Check if a line represents a good split point.
        
        Args:
            line: Text line
            
        Returns:
            True if it's a good split point
        """
        # Check for sentence endings
        if re.search(r'[.!?]\s*$', line.strip()):
            return True
        
        # Check for paragraph boundaries (empty lines)
        if not line.strip():
            return True
        
        # Check for common section markers
        if re.match(r'^#{1,6}\s', line.strip()):  # Markdown headers
            return True
        
        # Check for list endings
        if re.match(r'^\s*[-*+]\s', line.strip()) and not line.strip().endswith(','):
            return True
        
        return False

    def _get_overlap_lines(self, lines: List[str], overlap_size: int) -> List[str]:
        """
        Get lines for overlap from the end of the chunk.
        
        Args:
            lines: List of lines
            overlap_size: Desired overlap size in characters
            
        Returns:
            List of lines for overlap
        """
        if not lines or overlap_size <= 0:
            return []
        
        overlap_lines = []
        current_size = 0
        
        # Start from the end and work backwards
        for line in reversed(lines):
            line_size = len(line)
            if current_size + line_size > overlap_size:
                break
            overlap_lines.insert(0, line)
            current_size += line_size
        
        return overlap_lines

    def _clean_content(self, content: str) -> str:
        """
        Clean the input content by removing excessive whitespace and newlines.
        
        Args:
            content: Raw content to clean
            
        Returns:
            Cleaned content
        """
        if not content:
            return content
        
        # Remove excessive newlines (more than 2 consecutive)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove trailing whitespace from each line
        lines = content.split('\n')
        lines = [line.rstrip() for line in lines]
        
        # Remove empty lines at the beginning and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        return '\n'.join(lines)

    def _clean_chunk(self, chunk: str) -> str:
        """
        Clean individual chunk by removing excessive whitespace.
        
        Args:
            chunk: Chunk text to clean
            
        Returns:
            Cleaned chunk text
        """
        if not chunk:
            return chunk
        
        # Remove excessive newlines (more than 2 consecutive)
        chunk = re.sub(r'\n{3,}', '\n\n', chunk)
        
        # Remove trailing whitespace from each line
        lines = chunk.split('\n')
        lines = [line.rstrip() for line in lines]
        
        # Remove empty lines at the beginning and end of chunk
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Join lines and ensure single newline between non-empty lines
        result = []
        prev_empty = False
        
        for line in lines:
            if line.strip():  # Non-empty line
                result.append(line)
                prev_empty = False
            else:  # Empty line
                if not prev_empty:  # Only add one empty line
                    result.append('')
                prev_empty = True
        
        return '\n'.join(result)