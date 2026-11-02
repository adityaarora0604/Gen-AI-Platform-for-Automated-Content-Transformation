"""Shared Pydantic schemas = the API contract between modules and the frontend."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

OutputType = Literal["executive_summary", "linkedin", "x_thread", "advisory", "presentation"]

ALL_OUTPUT_TYPES: List[str] = [
    "executive_summary",
    "linkedin",
    "x_thread",
    "advisory",
    "presentation",
]

AUDIENCES = ["General public", "Executives / leadership", "Technical specialists", "Government / policy makers", "Media"]
TONES = ["Professional", "Formal", "Neutral", "Urgent", "Friendly"]
LANGUAGES = ["English", "Hindi", "Spanish", "French", "German"]
DETAIL_LEVELS = ["Low", "Medium", "High"]
OBJECTIVES = ["Inform", "Alert", "Persuade", "Educate", "Recommend action"]
STYLES = ["Structured", "Narrative", "Concise", "Analytical"]


class GenerationSettings(BaseModel):
    audience: str = "General public"
    tone: str = "Professional"
    language: str = "English"
    detail_level: Literal["Low", "Medium", "High"] = "Medium"
    objective: str = "Inform"
    style: str = "Structured"


class TransformRequest(BaseModel):
    source_text: str
    output_types: List[OutputType] = Field(default_factory=lambda: list(ALL_OUTPUT_TYPES))
    settings: GenerationSettings = Field(default_factory=GenerationSettings)


class SourceRepresentation(BaseModel):
    summary: str = ""
    key_points: List[str] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    important_figures: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    source_language: str = ""


class OutputItem(BaseModel):
    type: str
    label: str = ""
    content: str = ""
    validation_warnings: List[str] = Field(default_factory=list)
    status: Literal["completed", "failed"] = "completed"
    error: Optional[str] = None


class TransformResponse(BaseModel):
    job_id: str
    status: Literal["completed", "partial", "failed"]
    mode: str = "demo"
    source_representation: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[OutputItem] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    human_review_notice: str = (
        "AI-generated content may contain errors or omissions. A human must review it "
        "before publication or operational use. It has not been verified."
    )


class UploadResponse(BaseModel):
    filename: str
    file_type: str
    char_count: int
    text: str
    truncated: bool = False


class AppError(Exception):
    """Domain error that maps to an HTTP status in the API layer."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
