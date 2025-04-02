"""
Group models for organizing C3D files into collections.
"""
from typing import List, Optional, TYPE_CHECKING, Type
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

# Import from base models
from .base import TrialGroupBase, GroupFileLink

# Use TYPE_CHECKING to avoid runtime imports
if TYPE_CHECKING:
    from .c3d_file import C3DFile

class TrialGroup(TrialGroupBase, table=True):
    """Model for groups of C3D trials."""
    id: int | None = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    
    # Define the many-to-many relationship with C3DFile
    c3d_files: List["C3DFile"] = Relationship(
        back_populates="groups", 
        link_model=GroupFileLink
    )
    
    @classmethod
    def get_c3d_file_class(cls) -> Type["C3DFile"]:
        """Helper method to get the C3DFile class dynamically, avoiding circular imports."""
        from .c3d_file import C3DFile
        return C3DFile

class TrialGroupCreate(TrialGroupBase):
    """Model for creating a new trial group."""
    file_ids: List[int] = [] # Allow creating a group with initial files

class TrialGroupUpdate(SQLModel):
    """Model for updating an existing trial group."""
    name: Optional[str] = None
    description: Optional[str] = None
    
class TrialGroupRead(TrialGroupBase):
    """Model for reading group data, including ID and file count."""
    id: int
    date_created: datetime
    date_modified: datetime
    file_count: int = 0 # Will be calculated in the router 