"""
Analog Channel models for database storage and API responses.
"""
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .c3d_file import C3DFile

class ChannelBase(SQLModel):
    """Base model for analog channel data."""
    channel_name: str

class AnalogChannel(ChannelBase, table=True):
    """Database model for analog channel metadata."""
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="c3d_files.id")
    c3d_files: "C3DFile" = Relationship(back_populates="analog_channels")

class ChannelRead(ChannelBase):
    """API response model for analog channel data."""
    pass