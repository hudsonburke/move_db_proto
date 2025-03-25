"""
Marker models for database storage and API responses.
"""
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .c3d_file import C3DFile

class MarkerBase(SQLModel):
    """Base model for marker data."""
    marker_name: str

class Marker(MarkerBase, table=True):
    """Database model for marker metadata."""
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="c3d_files.id")
    c3d_files: "C3DFile" = Relationship(back_populates="markers")

class MarkerRead(MarkerBase):
    """API response model for marker data."""
    pass