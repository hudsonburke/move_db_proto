"""
Initialization for models package with dependency injection to avoid circular imports.
"""
# Import all models but delay the resolution of relationships
from .base import setup_relationship_handlers
from .c3d_file import C3DFile, C3DFileCreate, C3DFileUpdate, C3DFileRead
from .marker import Marker
from .channel import AnalogChannel
from .event import Event
from .response import Response, ErrorResponse
from .search import SearchResult
from .analysis import Analysis, AnalysisResult
from .group import TrialGroup, TrialGroupCreate, TrialGroupUpdate, TrialGroupRead

# Import hierarchy models
from .hierarchy import (
    Classification, ClassificationCreate, ClassificationUpdate, ClassificationRead,
    Subject, SubjectCreate, SubjectUpdate, SubjectRead,
    Session, SessionCreate, SessionUpdate, SessionRead,
    Trial, TrialCreate, TrialUpdate, TrialRead
)

# Initialize SQLModel relationships to resolve forward references
# This is called after all models are imported
setup_relationship_handlers()

__all__ = [
    'C3DFile', 'C3DFileCreate', 'C3DFileUpdate', 'C3DFileRead',
    'TrialGroup', 'TrialGroupCreate', 'TrialGroupUpdate', 'TrialGroupRead',
    'Marker', 'AnalogChannel', 'Event',
    'Response', 'ErrorResponse',
    'SearchResult',
    'Analysis', 'AnalysisResult',
    # Hierarchy models
    'Classification', 'ClassificationCreate', 'ClassificationUpdate', 'ClassificationRead',
    'Subject', 'SubjectCreate', 'SubjectUpdate', 'SubjectRead',
    'Session', 'SessionCreate', 'SessionUpdate', 'SessionRead',
    'Trial', 'TrialCreate', 'TrialUpdate', 'TrialRead'
]