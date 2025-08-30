from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field

from workspacex import ArtifactType


class FormFieldType(str, Enum):
    """Form field types for artifact creation forms"""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    SELECT = "select"
    FILE = "file"
    URL = "url"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    COLOR = "color"
    RANGE = "range"
    HIDDEN = "hidden"
    PASSWORD = "password"
    EMAIL = "email"
    TEL = "tel"
    RADIO = "radio"


class FormFieldOption(BaseModel):
    """Option for select, radio, and checkbox fields"""
    label: str = Field(..., description="Display label for the option")
    value: str = Field(..., description="Value for the option")
    description: Optional[str] = Field(None, description="Optional description for the option")


class FormFieldValidation(BaseModel):
    """Validation rules for form fields"""
    required: bool = Field(False, description="Whether the field is required")
    min_length: Optional[int] = Field(None, description="Minimum length for text fields")
    max_length: Optional[int] = Field(None, description="Maximum length for text fields")
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value for number fields")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value for number fields")
    pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    pattern_error: Optional[str] = Field(None, description="Error message for pattern validation")
    custom_validator: Optional[str] = Field(None, description="Name of custom validator function")


class FormField(BaseModel):
    """Definition of a form field for artifact creation"""
    name: str = Field(..., description="Field name (used as key in form data)")
    label: str = Field(..., description="Display label for the field")
    type: FormFieldType = Field(..., description="Field type")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    description: Optional[str] = Field(None, description="Help text for the field")
    default_value: Optional[Any] = Field(None, description="Default value for the field")
    options: Optional[List[FormFieldOption]] = Field(None, description="Options for select, radio, checkbox fields")
    validation: Optional[FormFieldValidation] = Field(None, description="Validation rules")
    dependent_on: Optional[Dict[str, Any]] = Field(None, description="Show field only if another field has specific value")
    order: int = Field(0, description="Display order in the form")
    group: Optional[str] = Field(None, description="Group name for organizing fields")
    width: Optional[str] = Field(None, description="Field width (e.g., 'full', 'half')")
    advanced: bool = Field(False, description="Whether this is an advanced field (can be hidden)")


class ArtifactFormDefinition(BaseModel):
    """Form definition for creating artifacts of a specific type"""
    artifact_type: ArtifactType = Field(..., description="Artifact type this form is for")
    title: str = Field(..., description="Form title")
    description: str = Field(..., description="Form description")
    fields: List[FormField] = Field(..., description="Form fields")
    submit_label: str = Field("Create", description="Label for the submit button")
    cancel_label: str = Field("Cancel", description="Label for the cancel button")
    success_message: str = Field("Artifact created successfully", description="Message shown on successful submission")
    error_message: str = Field("Failed to create artifact", description="Default error message")


# Form definitions for different artifact types
ARXIV_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.ARXIV,
    title="arXiv Paper",
    description="Create an artifact from an arXiv paper",
    fields=[
        FormField(
            name="arxiv_id_or_url",
            label="arXiv ID or URL",
            type=FormFieldType.TEXT,
            placeholder="e.g., 2307.09288 or https://arxiv.org/abs/2307.09288",
            description="Enter either an arXiv ID or the full URL to the paper",
            validation=FormFieldValidation(
                required=True,
                pattern=r"(^\d{4}\.\d{5}(v\d+)?$)|(arxiv\.org\/(?:abs|pdf)\/\d{4}\.\d{5}(v\d+)?)",
                pattern_error="Please enter a valid arXiv ID or URL"
            ),
            order=1
        ),
        FormField(
            name="page_count",
            label="Page Count",
            type=FormFieldType.NUMBER,
            description="Number of pages to process (-1 for all pages)",
            default_value=-1,
            validation=FormFieldValidation(
                required=False,
                min_value=-1
            ),
            order=2,
            advanced=True
        )
    ],
    submit_label="Process arXiv Paper",
    success_message="arXiv paper processed successfully"
)

PDF_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.PDF,
    title="PDF Document",
    description="Create an artifact from a PDF document",
    fields=[
        FormField(
            name="source_type",
            label="Source Type",
            type=FormFieldType.RADIO,
            options=[
                FormFieldOption(label="Upload File", value="file"),
                FormFieldOption(label="URL", value="url")
            ],
            default_value="file",
            validation=FormFieldValidation(required=True),
            order=1
        ),
        FormField(
            name="file_path",
            label="PDF File",
            type=FormFieldType.FILE,
            description="Upload a PDF file",
            validation=FormFieldValidation(required=True),
            dependent_on={"source_type": "file"},
            order=2
        ),
        FormField(
            name="url",
            label="PDF URL",
            type=FormFieldType.URL,
            placeholder="https://example.com/document.pdf",
            description="URL to a PDF document",
            validation=FormFieldValidation(
                required=True,
                pattern=r"^https?:\/\/.*\.pdf(\?.*)?$",
                pattern_error="Please enter a valid URL to a PDF document"
            ),
            dependent_on={"source_type": "url"},
            order=3
        ),
        FormField(
            name="page_count",
            label="Page Count",
            type=FormFieldType.NUMBER,
            description="Number of pages to process (-1 for all pages)",
            default_value=-1,
            validation=FormFieldValidation(
                required=False,
                min_value=-1
            ),
            order=4,
            advanced=True
        )
    ],
    submit_label="Process PDF",
    success_message="PDF document processed successfully"
)

WEB_PAGES_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.WEB_PAGES,
    title="Web Page",
    description="Create an artifact from a web page",
    fields=[
        FormField(
            name="url",
            label="Web Page URL",
            type=FormFieldType.URL,
            placeholder="https://example.com/page",
            description="URL of the web page to process",
            validation=FormFieldValidation(
                required=True,
                pattern=r"^https?:\/\/.*$",
                pattern_error="Please enter a valid URL"
            ),
            order=1
        ),
        FormField(
            name="title",
            label="Title",
            type=FormFieldType.TEXT,
            placeholder="Page Title",
            description="Optional title for the web page (will be auto-detected if not provided)",
            validation=FormFieldValidation(required=False),
            order=2
        )
    ],
    submit_label="Process Web Page",
    success_message="Web page processed successfully"
)

WEB_COLLECTION_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.WEB_PAGES,
    title="Web Page Collection",
    description="Create a collection of web pages",
    fields=[
        FormField(
            name="urls",
            label="Web Page URLs",
            type=FormFieldType.TEXTAREA,
            placeholder="https://example.com/page1\nhttps://example.com/page2",
            description="Enter one URL per line",
            validation=FormFieldValidation(
                required=True,
                min_length=1,
                pattern=r"^(https?:\/\/.*(\n|$))+$",
                pattern_error="Please enter valid URLs, one per line"
            ),
            order=1
        ),
        FormField(
            name="collection_name",
            label="Collection Name",
            type=FormFieldType.TEXT,
            placeholder="My Web Collection",
            description="Name for this collection of web pages",
            validation=FormFieldValidation(required=True),
            order=2
        )
    ],
    submit_label="Process Web Pages",
    success_message="Web page collection processed successfully"
)

TEXT_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.TEXT,
    title="Text Content",
    description="Create a text artifact",
    fields=[
        FormField(
            name="content",
            label="Text Content",
            type=FormFieldType.TEXTAREA,
            placeholder="Enter text content here...",
            description="The text content for this artifact",
            validation=FormFieldValidation(required=True),
            order=1
        ),
        FormField(
            name="title",
            label="Title",
            type=FormFieldType.TEXT,
            placeholder="Title for this text content",
            description="A title for this text artifact",
            validation=FormFieldValidation(required=False),
            order=2
        )
    ],
    submit_label="Create Text Artifact",
    success_message="Text artifact created successfully"
)

MARKDOWN_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.MARKDOWN,
    title="Markdown Content",
    description="Create a markdown artifact",
    fields=[
        FormField(
            name="content",
            label="Markdown Content",
            type=FormFieldType.TEXTAREA,
            placeholder="# Title\n\nEnter markdown content here...",
            description="The markdown content for this artifact",
            validation=FormFieldValidation(required=True),
            order=1
        ),
        FormField(
            name="title",
            label="Title",
            type=FormFieldType.TEXT,
            placeholder="Title for this markdown content",
            description="A title for this markdown artifact",
            validation=FormFieldValidation(required=False),
            order=2
        )
    ],
    submit_label="Create Markdown Artifact",
    success_message="Markdown artifact created successfully"
)

CODE_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.CODE,
    title="Code Content",
    description="Create a code artifact",
    fields=[
        FormField(
            name="content",
            label="Code Content",
            type=FormFieldType.TEXTAREA,
            placeholder="def hello_world():\n    print('Hello, world!')",
            description="The code content for this artifact",
            validation=FormFieldValidation(required=True),
            order=1
        ),
        FormField(
            name="language",
            label="Language",
            type=FormFieldType.SELECT,
            options=[
                FormFieldOption(label="Python", value="python"),
                FormFieldOption(label="JavaScript", value="javascript"),
                FormFieldOption(label="TypeScript", value="typescript"),
                FormFieldOption(label="HTML", value="html"),
                FormFieldOption(label="CSS", value="css"),
                FormFieldOption(label="Java", value="java"),
                FormFieldOption(label="C++", value="cpp"),
                FormFieldOption(label="C#", value="csharp"),
                FormFieldOption(label="Go", value="go"),
                FormFieldOption(label="Rust", value="rust"),
                FormFieldOption(label="Other", value="other")
            ],
            default_value="python",
            validation=FormFieldValidation(required=True),
            order=2
        ),
        FormField(
            name="title",
            label="Title",
            type=FormFieldType.TEXT,
            placeholder="Title for this code snippet",
            description="A title for this code artifact",
            validation=FormFieldValidation(required=False),
            order=3
        )
    ],
    submit_label="Create Code Artifact",
    success_message="Code artifact created successfully"
)

# Dictionary mapping artifact types to their form definitions
ARTIFACT_FORM_DEFINITIONS: Dict[ArtifactType, ArtifactFormDefinition] = {
    ArtifactType.ARXIV: ARXIV_FORM,
    ArtifactType.PDF: PDF_FORM,
    ArtifactType.WEB_PAGES: WEB_PAGES_FORM,
    ArtifactType.TEXT: TEXT_FORM,
    ArtifactType.MARKDOWN: MARKDOWN_FORM,
    ArtifactType.CODE: CODE_FORM,
}

# Function to get form definition for a specific artifact type
def get_form_definition(artifact_type: ArtifactType) -> Optional[ArtifactFormDefinition]:
    """
    Get form definition for a specific artifact type
    
    Args:
        artifact_type (ArtifactType): The artifact type to get form definition for
        
    Returns:
        Optional[ArtifactFormDefinition]: Form definition for the specified artifact type,
                                         or None if not found
    """
    return ARTIFACT_FORM_DEFINITIONS.get(artifact_type)


# Function to get all available form definitions
def get_all_form_definitions() -> Dict[str, ArtifactFormDefinition]:
    """
    Get all available form definitions
    
    Returns:
        Dict[str, ArtifactFormDefinition]: Dictionary mapping artifact type names to form definitions
    """
    return {artifact_type.value: form_def for artifact_type, form_def in ARTIFACT_FORM_DEFINITIONS.items()}
