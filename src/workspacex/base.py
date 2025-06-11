import json
import logging
from builtins import anext
from datetime import datetime
from typing import Any, Dict, Generator, AsyncGenerator, Optional

from pydantic import Field, BaseModel, model_validator



class OutputPart(BaseModel):
    content: Any
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="metadata")

    @model_validator(mode='after')
    def setup_metadata(self):
        # Ensure metadata is initialized
        if self.metadata is None:
            self.metadata = {}
        return self
    

class Output(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="metadata")
    parts: Any = Field(default_factory=list, exclude=True, description="parts of Output")
    data: Any = Field(default=None, exclude=True, description="Output Data")

    @model_validator(mode='after')
    def setup_defaults(self):
        # Ensure metadata and parts are initialized
        if self.metadata is None:
            self.metadata = {}
        if self.parts is None:
            self.parts = []
        return self

    def add_part(self, content: Any):
        if self.parts is None:
            self.parts = []
        self.parts.append(OutputPart(content=content))

    def output_type(self):
        return "default"
