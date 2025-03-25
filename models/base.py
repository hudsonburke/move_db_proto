"""
Base models and utilities for the C3D database.
"""
from typing import ForwardRef
from datetime import datetime
from sqlmodel import Field, SQLModel

class BaseModel(SQLModel):
    """Base model with common fields and methods."""
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    filename: str | None = None
    file_size: int | None = None
    frame_count: int | None = None
    sample_rate: float | None = None
    subject_name: str | None = None
    description: str | None = None
    has_marker_data: bool = False
    has_analog_data: bool = False
    has_event_data: bool = False

class TrialGroupBase(SQLModel):
    """Base model for trial groups with common fields."""
    name: str
    description: str | None = None

# Link table for many-to-many relationship between C3DFile and TrialGroup
class GroupFileLink(SQLModel, table=True):
    """Link table for many-to-many relationship between groups and files."""
    __tablename__ = "group_file_link"
    
    group_id: int | None = Field(
        default=None, foreign_key="trialgroup.id", primary_key=True
    )
    file_id: int | None = Field(
        default=None, foreign_key="c3d_files.id", primary_key=True
    )

# Dictionary to store forward references for model resolution
_model_references: dict[str, ForwardRef] = {}
_initialized = False

def setup_relationship_handlers() -> None:
    """
    Initialize relationships and resolve forward references.
    Called after all models are imported in __init__.py
    """
    global _initialized
    
    if _initialized:
        return
    
    # Import models here to avoid circular imports
    from .c3d_file import C3DFile
    from .group import TrialGroup
    from .marker import Marker
    from .channel import AnalogChannel
    from .event import Event
    
    # Update forward references
    C3DFile.model_rebuild()
    TrialGroup.model_rebuild()
    Marker.model_rebuild()
    AnalogChannel.model_rebuild()
    Event.model_rebuild()
    
    _initialized = True