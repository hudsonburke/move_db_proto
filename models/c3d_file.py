"""
C3D File models for database storage and API responses.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import JSON
from .base import C3DFileBase, GroupFileLink
from .analysis import C3DFileAnalysisLink

if TYPE_CHECKING:
    from .group import TrialGroup
    from .marker import Marker
    from .channel import AnalogChannel
    from .event import Event
    from .analysis import Analysis
    from .hierarchy import Trial

class C3DFile(C3DFileBase, table=True):
    """Database model for C3D file records."""
    __tablename__ = "c3d_files"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str = Field(unique=True)
    
    # Deprecated fields (kept for backward compatibility, but use the hierarchy models instead)
    classification: Optional[str] = None
    session_name: Optional[str] = None
    subject_name: Optional[str] = None
    
    # Additional metadata as JSON
    file_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Use forward refs for relationships
    groups: List["TrialGroup"] = Relationship(
        back_populates="c3d_files",
        link_model=GroupFileLink
    )
    markers: List["Marker"] = Relationship(back_populates="c3d_files")
    analog_channels: List["AnalogChannel"] = Relationship(back_populates="c3d_files")
    events: List["Event"] = Relationship(back_populates="c3d_files")
    analyses: List["Analysis"] = Relationship(
        back_populates="c3d_files",
        link_model=C3DFileAnalysisLink
    )
    # New relationship to Trial (from hierarchy)
    trials: List["Trial"] = Relationship(back_populates="c3d_file")

class C3DFileCreate(C3DFileBase):
    """Model for creating C3D file records."""
    filename: str
    filepath: str
    file_size: int
    frame_count: int
    sample_rate: float
    subject_name: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[str] = None
    session_name: Optional[str] = None
    file_metadata: Optional[Dict[str, Any]] = None

class C3DFileUpdate(SQLModel):
    """Model for updating C3D file records."""
    filename: Optional[str] = None
    subject_name: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[str] = None
    session_name: Optional[str] = None
    file_metadata: Optional[Dict[str, Any]] = None

class C3DFileRead(C3DFileBase):
    """API response model for C3D file data."""
    id: int
    date_added: datetime
    filepath: str
    trial_count: int = 0  # Will be calculated in the router
    # Include the associations with hierarchy
    trials: List[Dict[str, Any]] = []  # Will be populated with trial IDs and names
