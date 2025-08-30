import hashlib
import re
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse

from workspacex import Artifact, ArtifactType
from workspacex.artifact import AttachmentFile
from workspacex.chunk.base import ChunkConfig, ChunkerFactory
from workspacex.utils.logger import logger


class WebPagesArtifact(Artifact):
    """
    Represents a web pages artifact
    
    This artifact type handles web page content, storing both the raw HTML
    and processed text content for analysis.
    """

    @staticmethod
    def from_url(url: str, 
                 content: Optional[str] = None,
                 html_content: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 **kwargs) -> 'WebPagesArtifact':
        """
        Create a web pages artifact from a URL
        
        Args:
            url (str): URL of the web page
            content (str, optional): Processed text content of the web page
            html_content (str, optional): Raw HTML content of the web page
            metadata (dict, optional): Additional metadata for the web page
            **kwargs: Additional keyword arguments for the Artifact base class
            
        Returns:
            WebPagesArtifact: The created web pages artifact
        """
        # Validate URL
        WebPagesArtifact._validate_url(url)
        
        # Generate a unique artifact ID based on URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        domain = WebPagesArtifact._extract_domain(url)
        artifact_id = f"web_{domain}_{url_hash}"
        
        # Initialize metadata
        if metadata is None:
            metadata = {}
            
        metadata.update({
            "url": url,
            "domain": domain,
            "title": metadata.get("title", ""),
            "has_html": html_content is not None,
        })
        
        # Create instance using private constructor
        instance = WebPagesArtifact.__new__(WebPagesArtifact)
        instance._init_web_pages(
            artifact_id=artifact_id,
            content=content or "",
            metadata=metadata,
            html_content=html_content,
            **kwargs
        )
        
        return instance

    def _init_web_pages(self, 
                        artifact_id: str,
                        content: str,
                        metadata: Dict[str, Any],
                        html_content: Optional[str] = None,
                        **kwargs) -> None:
        """
        Private initialization method for web pages artifact
        
        Args:
            artifact_id (str): Unique identifier for the artifact
            content (str): Processed text content of the web page
            metadata (dict): Metadata for the web page
            html_content (str, optional): Raw HTML content of the web page
            **kwargs: Additional keyword arguments for the Artifact base class
        """
        super().__init__(
            artifact_id=artifact_id, 
            content=content, 
            artifact_type=ArtifactType.WEB_PAGES, 
            metadata=metadata, 
            **kwargs
        )
        
        # Store HTML content as attachment if provided
        if html_content:
            self._add_html_attachment(html_content)

    def __init__(self, *args, **kwargs):
        """
        Initialize a web pages artifact
        
        This constructor is kept for backward compatibility but should not be used directly.
        Use WebPagesArtifact.from_url() instead.
        """
        raise NotImplementedError(
            "❌ Use WebPagesArtifact.from_url() to create instances instead of direct constructor"
        )

    @staticmethod
    def _validate_url(url: str) -> None:
        """
        Validate that the URL is properly formatted
        
        Args:
            url (str): URL to validate
            
        Raises:
            ValueError: If URL is invalid
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError(f"❌ Invalid URL format: {url}")
        except Exception as e:
            raise ValueError(f"❌ Invalid URL: {url}, error: {str(e)}")

    @staticmethod
    def _extract_domain(url: str) -> str:
        """
        Extract domain name from URL
        
        Args:
            url (str): URL to extract domain from
            
        Returns:
            str: Domain name
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            # Remove www. prefix if present
            domain = re.sub(r'^www\.', '', domain)
            # Remove port number if present
            domain = domain.split(':')[0]
            return domain
        except Exception:
            # Return a safe default if parsing fails
            return "website"

    def _add_html_attachment(self, html_content: str) -> None:
        """
        Add HTML content as an attachment
        
        Args:
            html_content (str): HTML content to add
        """
        # Create a temporary file to store HTML content
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        file_name = f"{self.artifact_id}.html"
        file_path = os.path.join(temp_dir, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Add as attachment
        self.add_attachment_file(AttachmentFile(
            file_name=file_name,
            file_desc="HTML content",
            file_path=file_path
        ))
        
        # Update metadata
        self.metadata['has_html'] = True
        logger.info(f"📎 Added HTML attachment for {self.url}")

    @property
    def url(self) -> str:
        """Get the URL of the web page"""
        return self.metadata.get('url', '')

    @property
    def domain(self) -> str:
        """Get the domain of the web page"""
        return self.metadata.get('domain', '')

    @property
    def title(self) -> str:
        """Get the title of the web page"""
        return self.metadata.get('title', '')

    @title.setter
    def title(self, title: str) -> None:
        """Set the title of the web page"""
        self.metadata['title'] = title

    @property
    def has_html(self) -> bool:
        """Check if the artifact has HTML content"""
        return self.metadata.get('has_html', False)

    @property
    def chunker(self):
        """Get the chunker configuration for this artifact type"""
        chunk_config = ChunkConfig(
            enabled=True,
            provider="text"
        )
        return ChunkerFactory.get_chunker(chunk_config)

    def after_chunker(self):
        """Clean up after chunking is complete"""
        # Keep the content for web pages
        pass
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebPagesArtifact':
        """
        从字典创建 WebPagesArtifact 实例
        
        Args:
            data (Dict[str, Any]): 包含 artifact 信息的字典数据
            
        Returns:
            WebPagesArtifact: 创建的 WebPagesArtifact 实例
            
        Raises:
            ValueError: 如果缺少必要的字段
        """
        metadata = data.get("metadata", {})
        url = metadata.get("url")
        
        if not url:
            raise ValueError(f"❌ Missing required field 'url' in metadata for WebPagesArtifact")
            
        # 创建实例
        return cls.from_url(
            url=url,
            content=data.get("content", ""),
            metadata=metadata,
            artifact_id=data.get("artifact_id")
        )

    async def post_process(self, html_content: Optional[str] = None) -> None:
        """
        Post-process web page content
        
        Args:
            html_content (str, optional): HTML content to process
            
        Returns:
            None: Updates the artifact with processed content
        """
        if html_content and not self.has_html:
            self._add_html_attachment(html_content)
        
        # Mark processing as complete
        self.mark_complete()
        logger.info(f"✅ Successfully processed web page: {self.url}")


class WebPageCollection(Artifact):
    """
    Represents a collection of web pages
    
    This artifact type handles multiple web pages, storing them as sub-artifacts.
    """

    @staticmethod
    def from_urls(urls: List[str],
                  collection_name: Optional[str] = None,
                  **kwargs) -> 'WebPageCollection':
        """
        Create a web page collection from a list of URLs
        
        Args:
            urls (List[str]): List of URLs to include in the collection
            collection_name (str, optional): Name of the collection
            **kwargs: Additional keyword arguments for the Artifact base class
            
        Returns:
            WebPageCollection: The created web page collection artifact
        """
        # Validate URLs
        for url in urls:
            WebPagesArtifact._validate_url(url)
        
        # Generate a unique artifact ID
        collection_name = collection_name or "web_collection"
        artifact_id = f"{collection_name}_{len(urls)}_pages"
        
        # Initialize metadata
        metadata = {
            "urls": urls,
            "collection_name": collection_name,
            "page_count": len(urls)
        }
        
        # Create instance using private constructor
        instance = WebPageCollection.__new__(WebPageCollection)
        instance._init_web_page_collection(
            artifact_id=artifact_id,
            metadata=metadata,
            **kwargs
        )
        
        return instance

    def _init_web_page_collection(self,
                                 artifact_id: str,
                                 metadata: Dict[str, Any],
                                 **kwargs) -> None:
        """
        Private initialization method for web page collection
        
        Args:
            artifact_id (str): Unique identifier for the artifact
            metadata (dict): Metadata for the collection
            **kwargs: Additional keyword arguments for the Artifact base class
        """
        super().__init__(
            artifact_id=artifact_id, 
            content="", 
            artifact_type=ArtifactType.WEB_PAGES, 
            metadata=metadata, 
            **kwargs
        )

    def __init__(self, *args, **kwargs):
        """
        Initialize a web page collection
        
        This constructor is kept for backward compatibility but should not be used directly.
        Use WebPageCollection.from_urls() instead.
        """
        raise NotImplementedError(
            "❌ Use WebPageCollection.from_urls() to create instances instead of direct constructor"
        )

    @property
    def urls(self) -> List[str]:
        """Get the list of URLs in the collection"""
        return self.metadata.get('urls', [])

    @property
    def collection_name(self) -> str:
        """Get the name of the collection"""
        return self.metadata.get('collection_name', '')

    @property
    def page_count(self) -> int:
        """Get the number of pages in the collection"""
        return self.metadata.get('page_count', 0)

    async def add_page(self, 
                       url: str, 
                       content: Optional[str] = None,
                       html_content: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> WebPagesArtifact:
        """
        Add a web page to the collection
        
        Args:
            url (str): URL of the web page
            content (str, optional): Processed text content of the web page
            html_content (str, optional): Raw HTML content of the web page
            metadata (dict, optional): Additional metadata for the web page
            
        Returns:
            WebPagesArtifact: The created web page artifact
        """
        # Create web page artifact
        web_page = WebPagesArtifact.from_url(
            url=url,
            content=content,
            html_content=html_content,
            metadata=metadata,
            parent_id=self.artifact_id
        )
        
        # Add to collection
        self.add_subartifact(web_page)
        
        # Update metadata
        if url not in self.urls:
            self.metadata['urls'].append(url)
            self.metadata['page_count'] = len(self.metadata['urls'])
        
        return web_page

    async def post_process(self) -> None:
        """
        Post-process all web pages in the collection
        
        Returns:
            None: Updates the artifact with processed content
        """
        # Mark processing as complete
        self.mark_complete()
        logger.info(f"✅ Successfully processed web page collection: {self.collection_name} with {self.page_count} pages")
        