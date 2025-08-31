import traceback
from typing import Dict, Any, Optional, Type, Union, ClassVar

from workspacex import Artifact, ArtifactType
from workspacex.artifacts.arxiv import ArxivArtifact
from workspacex.artifacts.pdf_artifact import PDFArtifact
from workspacex.artifacts.web_pages import WebPagesArtifact, WebPageCollection
from workspacex.utils.logger import logger
from workspacex.artifacts.novel_artifact import NovelArtifact


class ArtifactFactory:
    """
    Factory class for creating artifact instances
    
    This class provides methods to create various types of artifacts based on form data.
    """

    # Registry of artifact classes by type
    _artifact_classes: ClassVar[Dict[ArtifactType, Type[Artifact]]] = {
        ArtifactType.ARXIV: ArxivArtifact,
        ArtifactType.PDF: PDFArtifact,
        ArtifactType.WEB_PAGES: WebPagesArtifact,
        ArtifactType.NOVEL: NovelArtifact
    }

    @classmethod
    def register_artifact_class(cls, artifact_type: ArtifactType,
                                artifact_class: Type[Artifact]) -> None:
        """
        Register a new artifact class for a specific type
        
        Args:
            artifact_type (ArtifactType): The artifact type
            artifact_class (Type[Artifact]): The artifact class
        """
        cls._artifact_classes[artifact_type] = artifact_class

        logger.info(
            f"📝 Registered artifact class for type: {artifact_type.value}")

    @classmethod
    def create_artifact(cls, artifact_type: ArtifactType,
                        form_data: Dict[str, Any], **kwargs) -> Artifact:
        """
        Create an artifact instance based on form data
        
        Args:
            artifact_type (ArtifactType): The type of artifact to create
            form_data (Dict[str, Any]): Form data for creating the artifact
            **kwargs: Additional keyword arguments to pass to the artifact constructor
            
        Returns:
            Artifact: The created artifact instance
            
        Raises:
            ValueError: If the artifact type is not supported or required fields are missing
        """
        # Check if artifact type is supported
        if artifact_type not in cls._artifact_classes:
            raise ValueError(
                f"❌ Unsupported artifact type: {artifact_type.value}")

        # Create artifact based on type
        if artifact_type == ArtifactType.ARXIV:
            return cls._create_arxiv_artifact(form_data, **kwargs)
        elif artifact_type == ArtifactType.PDF:
            return cls._create_pdf_artifact(form_data, **kwargs)
        elif artifact_type == ArtifactType.WEB_PAGES:
            return cls._create_web_pages_artifact(form_data, **kwargs)
        else:
            # Generic artifact creation
            artifact_class = cls._artifact_classes[artifact_type]
            return artifact_class(**form_data, **kwargs)

    @staticmethod
    def _create_arxiv_artifact(form_data: Dict[str, Any],
                               **kwargs) -> ArxivArtifact:
        """
        Create an arXiv artifact
        
        Args:
            form_data (Dict[str, Any]): Form data for creating the artifact
            **kwargs: Additional keyword arguments to pass to the artifact constructor
            
        Returns:
            ArxivArtifact: The created arXiv artifact
            
        Raises:
            ValueError: If required fields are missing
        """
        # Check required fields
        if 'arxiv_id_or_url' not in form_data:
            raise ValueError("❌ Missing required field: arxiv_id_or_url")

        # Create artifact
        arxiv_id_or_url = form_data['arxiv_id_or_url']
        page_count = form_data.get('page_count', -1)

        return ArxivArtifact(arxiv_id_or_url=arxiv_id_or_url,
                             page_count=page_count,
                             **kwargs)

    @staticmethod
    def _create_pdf_artifact(form_data: Dict[str, Any],
                             **kwargs) -> PDFArtifact:
        """
        Create a PDF artifact
        
        Args:
            form_data (Dict[str, Any]): Form data for creating the artifact
            **kwargs: Additional keyword arguments to pass to the artifact constructor
            
        Returns:
            PDFArtifact: The created PDF artifact
            
        Raises:
            ValueError: If required fields are missing
        """
        # Check source type
        source_type = form_data.get('source_type', 'file')

        if source_type == 'file':
            # File upload
            if 'file_path' not in form_data:
                raise ValueError("❌ Missing required field: file_path")

            file_path = form_data['file_path']
            page_count = form_data.get('page_count', -1)

            return PDFArtifact(file_path=file_path,
                               page_count=page_count,
                               **kwargs)
        else:
            # URL
            if 'url' not in form_data:
                raise ValueError("❌ Missing required field: url")

            url = form_data['url']
            page_count = form_data.get('page_count', -1)

            return PDFArtifact(url=url, page_count=page_count, **kwargs)

    @staticmethod
    def _create_web_pages_artifact(
            form_data: Dict[str, Any],
            **kwargs) -> Union[WebPagesArtifact, WebPageCollection]:
        """
        Create a web pages artifact or collection
        
        Args:
            form_data (Dict[str, Any]): Form data for creating the artifact
            **kwargs: Additional keyword arguments to pass to the artifact constructor
            
        Returns:
            Union[WebPagesArtifact, WebPageCollection]: The created web pages artifact or collection
            
        Raises:
            ValueError: If required fields are missing
        """
        # Check if it's a collection
        if 'urls' in form_data:
            # Collection
            urls = form_data['urls'].strip().split('\n')
            collection_name = form_data.get('collection_name',
                                            'Web Collection')

            return WebPageCollection(urls=urls,
                                     collection_name=collection_name,
                                     **kwargs)
        else:
            # Single web page
            if 'url' not in form_data:
                raise ValueError("❌ Missing required field: url")

            url = form_data['url']
            title = form_data.get('title', '')
            content = form_data.get('content', '')
            html_content = form_data.get('html_content')

            metadata = {}
            if title:
                metadata['title'] = title

            return WebPagesArtifact(url=url,
                                    content=content,
                                    html_content=html_content,
                                    metadata=metadata,
                                    **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional[Artifact]:
        """
        restore an Artifact instance
        
        This method will create the corresponding subclass instance according to the artifact_type field, ensure that the deserialized object
        maintains the same type and behavior as the original object. This is very important for scenarios that require calling subclass specific methods.
        maintains the same type and behavior as the original object. This is very important for scenarios that require calling subclass specific methods.
        
        Args:
            data (Dict[str, Any]): the dictionary data containing artifact information
            
        Returns:
            Optional[Artifact]: the created artifact instance with the correct subclass type, if the artifact_id does not exist, return None
            
        Raises:
            ValueError: if the artifact_type is not supported
        """
        if not data.get("artifact_id"):
            return None

        # Get artifact type
        artifact_type_str = data.get("artifact_type")
        if not artifact_type_str:
            logger.warning(
                f"⚠️ Missing artifact_type in data for artifact_id: {data.get('artifact_id')}"
            )
            return None

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            logger.warning(f"⚠️ Invalid artifact_type: {artifact_type_str}")
            return None

        # Check if artifact type is supported
        if artifact_type not in cls._artifact_classes:
            return Artifact.from_dict(data)

        try:
            # Get the appropriate artifact class
            artifact_class = cls._artifact_classes[artifact_type]

            # Check if there is a special from_dict static method
            if hasattr(artifact_class, 'from_dict') and callable(
                    getattr(artifact_class, 'from_dict')):
                # Use the class's own from_dict method to create an instance
                artifact = artifact_class.from_dict(data)
            else:
                # Use the general way to create an instance
                artifact = artifact_class(data)
            logger.info(
                f"📥 Deserialized artifact of type {artifact_type.value}: {artifact.artifact_id}"
            )
            return artifact
        except Exception as e:
            logger.error(
                f"❌ Failed to deserialize artifact of type {artifact_type.value if 'artifact_type' in locals() else 'unknown'}: {e}, traceback: {traceback.format_exc()}"
            )
            return None
