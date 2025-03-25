"""
Search query models for API requests.
"""
from typing import Any
from pydantic import BaseModel
from .response import FileRead

class RegexField(BaseModel):
    """Model for a field with regex option."""
    value: str | None = None
    use_regex: bool = False

class FileQuery(BaseModel):
    """Model for basic file queries with optional regex support."""
    filename: str | None = None
    filename_regex: bool = False
    classification: str | None = None
    classification_regex: bool = False
    subject: str | None = None
    subject_regex: bool = False
    session_name: str | None = None
    session_regex: bool = False
    min_duration: float | None = None
    max_duration: float | None = None
    min_frame_count: int | None = None
    max_frame_count: int | None = None
    marker: str | None = None
    marker_regex: bool = False
    channel: str | None = None
    channel_regex: bool = False
    event: str | None = None
    event_regex: bool = False
    analysis_name: str | None = None
    analysis_params: dict[str, Any] | None = None

class SearchQuery(BaseModel):
    """Model for advanced search queries."""
    # Basic file metadata filters
    filename: RegexField = RegexField()
    subject: RegexField = RegexField()
    classification: RegexField = RegexField()
    session_name: RegexField = RegexField()
    min_duration: float | None = None
    max_duration: float | None = None
    min_frame_count: int | None = None
    max_frame_count: int | None = None
    
    # Content filters
    marker: RegexField = RegexField()
    channel: RegexField = RegexField()
    event: RegexField = RegexField()
    
    # Analysis filters
    analysis_name: str | None = None
    analysis_params: dict[str, Any] | None = None

class SearchResult(BaseModel):
    """Model for search results."""
    total: int
    results: list[FileRead]

