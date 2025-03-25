"""
Analysis models for custom user-defined analyses.
"""
from fastapi import HTTPException
import ezc3d
from typing import Any, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON, Column, Relationship

if TYPE_CHECKING:
    from .c3d_file import C3DFile

# Define the link model first
class C3DFileAnalysisLink(SQLModel, table=True):
    """Link table between C3DFile and Analysis models."""
    analysis_id: int = Field(foreign_key="analysis.id", primary_key=True)
    c3dfile_id: int = Field(foreign_key="c3d_files.id", primary_key=True)

# class AnalysisField(SQLModel):
#     name: str
#     description: str
#     version: str
#     value: Any | None = Field(default=None, sa_column=Column(JSON))

#     def analyze(self, c3d: ezc3d.c3d, parameters: dict[str, Any] = None) -> Any:
#         """Override this method to implement custom analysis logic."""
#         raise NotImplementedError("AnalysisField classes must implement analyze method")

class AnalysisBase(SQLModel):
    """Base class for all analysis models."""
    name: str
    description: str
    version: str | None = "1.0.0"
    parameters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    def analyze(self, c3d: ezc3d.c3d) -> dict[str, Any]:
        """Override this method to implement custom analysis logic."""
        raise NotImplementedError("Analysis classes must implement analyze method")

class Analysis(AnalysisBase, table=True):
    """Database model for analysis results."""
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="c3d_files.id")
    created_at: datetime = Field(default_factory=datetime.now)
    result: bool
    details: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    value: float | None = None
    c3d_files: list["C3DFile"] = Relationship(
        back_populates="analyses",
        link_model=C3DFileAnalysisLink
    )

class AnalysisResult(SQLModel):
    """Model for analysis results."""
    id: int
    file_id: int
    name: str
    description: str
    version: str
    parameters: dict[str, Any]
    result: bool
    details: dict[str, Any]
    value: float | None
    created_at: datetime

class C3DDataExtractor(AnalysisBase):
    """Analysis class for extracting metadata from a C3D file."""
    def __init__(self, parameters: dict[str, Any] = None):
        # Initialize with proper keyword arguments
        super().__init__(
            name="C3D Data Extractor",
            description="Extracts metadata from a C3D file.",
            version="1.0",
            parameters=parameters or {}
        )
        # No need to set these attributes again as they're now passed to the parent constructor

    def analyze(self, filepath: str) -> dict[str, Any]:
        """Extract metadata from a C3D file."""
        try:
            c3d = ezc3d.c3d(filepath)
            
            # Basic file info
            header = c3d.header
            parameters = c3d.parameters
            
            # Extract common metadata
            frame_count = header['points']['last_frame'] - header['points']['first_frame'] + 1
            sample_rate = header['points']['frame_rate']
            duration = frame_count / sample_rate if sample_rate > 0 else 0
            
            # Try to get subject name (if available)
            subject_name = ""
            if "SUBJECTS" in parameters and "NAMES" in parameters["SUBJECTS"]:
                subject_names = parameters["SUBJECTS"]["NAMES"]["value"]
                if subject_names and len(subject_names) > 0:
                    subject_name = subject_names[0]
            
            # Store additional metadata as a string
            metadata = str(parameters)
            
            # Get marker names
            marker_names = c3d.parameters["POINT"]["LABELS"]["value"]
            markers = [name for name in marker_names if name.strip()]
            
            # Get analog channel names
            channels = []
            if "ANALOG" in c3d.parameters and "LABELS" in c3d.parameters["ANALOG"]:
                channel_names = c3d.parameters["ANALOG"]["LABELS"]["value"]
                channels = [name for name in channel_names if name.strip()]
            
            # Get events
            events = []
            if "EVENT" in c3d.parameters and "LABELS" in c3d.parameters["EVENT"]:
                event_names = c3d.parameters["EVENT"]["LABELS"]["value"]
                event_times = c3d.parameters["EVENT"]["TIMES"]["value"]
                
                if len(event_times) > 2:
                    event_times = event_times[2]  # Time values
                    for i, event in enumerate(event_names):
                        if i < len(event_times):
                            events.append((event, event_times[i]))
            
            return {
                "frame_count": frame_count,
                "sample_rate": sample_rate,
                "duration": duration,
                "subject_name": subject_name,
                "metadata": metadata,
                "markers": markers,
                "channels": channels,
                "events": events
            }
        except Exception as e:
            print(f"Error extracting C3D data: {str(e)}")  # Add logging
            raise HTTPException(status_code=400, detail=f"Invalid C3D file: {str(e)}")