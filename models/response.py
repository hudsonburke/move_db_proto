"""
API response models that combine multiple entity models.
"""
from datetime import datetime
from sqlmodel import SQLModel
from typing import List, Dict, Any
from .base import BaseModel
from .marker import MarkerRead
from .channel import ChannelRead
from .event import EventRead

class FileRead(BaseModel):
    """Complete file response model including related entities."""
    id: int
    filepath: str  # Using filepath as identifier instead of id
    date_added: datetime
    classification: str | None = None
    session_name: str | None = None
    file_metadata: Dict[str, Any] | None = None
    markers: list[MarkerRead] = []
    channels: list[ChannelRead] = []
    events: list[EventRead] = []

class Response(SQLModel):
    """Generic response model."""
    message: str

class ErrorResponse(SQLModel):
    """Error response model."""
    error: str
    details: str