"""
C3D File models for database storage and API responses.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlmodel import Field, Relationship, SQLModel
from .base import C3DFileBase, GroupFileLink
from .analysis import C3DFileAnalysisLink

if TYPE_CHECKING:
    from .group import TrialGroup
    from .marker import Marker
    from .channel import AnalogChannel
    from .event import Event
    from .analysis import Analysis

class C3DFile(C3DFileBase, table=True):
    """Database model for C3D file records."""
    __tablename__ = "c3d_files"
    
    id: int | None = Field(default=None, primary_key=True)
    filepath: str = Field(unique=True)
    classification: str | None = None
    session_name: str | None = None
    
    # Use forward refs for relationships
    groups: List["TrialGroup"] = Relationship(
        back_populates="c3d_files",
        link_model=GroupFileLink
    )
    markers: list["Marker"] = Relationship(back_populates="c3d_files")
    analog_channels: list["AnalogChannel"] = Relationship(back_populates="c3d_files")
    events: list["Event"] = Relationship(back_populates="c3d_files")
    analyses: list["Analysis"] = Relationship(
        back_populates="c3d_files",
        link_model=C3DFileAnalysisLink
    )

class C3DFileCreate(C3DFileBase):
    """Model for creating C3D file records."""
    filename: str
    filepath: str
    file_size: int
    frame_count: int
    sample_rate: float
    subject_name: str | None = None
    description: str | None = None
    classification: str | None = None
    session_name: str | None = None
