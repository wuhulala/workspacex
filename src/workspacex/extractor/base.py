

from abc import ABC, abstractmethod
from typing import Any
from workspacex.artifact import Artifact


class BaseExtractor(ABC):
    """Base class for extractors.
    Extractors are used to extract artifacts from content. such as text, images, audio, video, html, pdf, markdown, noval.txt, etc.
    """
    
    @abstractmethod
    def extract(self, content: Any) -> list[Artifact]:
        """Extract artifacts from content."""
        raise NotImplementedError