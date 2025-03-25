"""
Event models for database storage and API responses.
"""
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .c3d_file import C3DFile

class EventBase(SQLModel):
    """Base model for event data."""
    event_name: str
    event_time: float

class Event(EventBase, table=True):
    """Database model for event metadata."""
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="c3d_files.id")
    c3d_files: "C3DFile" = Relationship(back_populates="events")

class EventRead(EventBase):
    """API response model for event data."""
    pass