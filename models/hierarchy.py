"""
Hierarchical models for organizing data: Classification > Subject > Session > Trial
"""
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON

if TYPE_CHECKING:
    from .c3d_file import C3DFile

class ClassificationBase(SQLModel):
    """Base model for classification data."""
    name: str
    description: Optional[str] = None

class Classification(ClassificationBase, table=True):
    """Database model for classification of research data (e.g., "Clinical", "Research")."""
    __tablename__ = "classifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    subjects: List["Subject"] = Relationship(back_populates="classification")
    
    # Metadata as JSON for flexible fields
    meta_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class ClassificationCreate(ClassificationBase):
    """API model for creating a new classification."""
    meta_data: Optional[Dict[str, Any]] = None

class ClassificationUpdate(SQLModel):
    """API model for updating an existing classification."""
    name: Optional[str] = None
    description: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class ClassificationRead(ClassificationBase):
    """API response model for classification data."""
    id: int
    date_created: datetime
    date_modified: datetime
    meta_data: Dict[str, Any] = {}
    subject_count: int = 0  # Will be calculated in the router

class SubjectBase(SQLModel):
    """Base model for subject data."""
    name: str
    description: Optional[str] = None

class Subject(SubjectBase, table=True):
    """Database model for research subjects."""
    __tablename__ = "subjects"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    
    # Foreign Keys
    classification_id: Optional[int] = Field(default=None, foreign_key="classifications.id")
    
    # Relationships
    classification: Optional[Classification] = Relationship(back_populates="subjects")
    sessions: List["Session"] = Relationship(back_populates="subject")
    
    # Metadata as JSON for flexible demographics and other fields
    demographics: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class SubjectCreate(SubjectBase):
    """API model for creating a new subject."""
    classification_id: Optional[int] = None
    demographics: Optional[Dict[str, Any]] = None

class SubjectUpdate(SQLModel):
    """API model for updating an existing subject."""
    name: Optional[str] = None
    description: Optional[str] = None
    classification_id: Optional[int] = None
    demographics: Optional[Dict[str, Any]] = None

class SubjectRead(SubjectBase):
    """API response model for subject data."""
    id: int
    date_created: datetime
    date_modified: datetime
    classification_id: Optional[int] = None
    session_count: int = 0  # Will be calculated in the router
    demographics: Dict[str, Any] = {}

class SessionBase(SQLModel):
    """Base model for session data."""
    name: str
    description: Optional[str] = None
    date: Optional[datetime] = None

class Session(SessionBase, table=True):
    """Database model for data collection sessions."""
    __tablename__ = "sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    
    # Foreign Keys
    subject_id: int = Field(foreign_key="subjects.id")
    
    # Relationships
    subject: Subject = Relationship(back_populates="sessions")
    trials: List["Trial"] = Relationship(back_populates="session")
    
    # Metadata as JSON for flexible conditions and other fields
    conditions: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class SessionCreate(SessionBase):
    """API model for creating a new session."""
    subject_id: int
    conditions: Optional[Dict[str, Any]] = None

class SessionUpdate(SQLModel):
    """API model for updating an existing session."""
    name: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    conditions: Optional[Dict[str, Any]] = None

class SessionRead(SessionBase):
    """API response model for session data."""
    id: int
    date_created: datetime
    date_modified: datetime
    subject_id: int
    trial_count: int = 0  # Will be calculated in the router
    conditions: Dict[str, Any] = {}

class TrialBase(SQLModel):
    """Base model for trial data."""
    name: str
    description: Optional[str] = None

class Trial(TrialBase, table=True):
    """Database model for individual trials within a session."""
    __tablename__ = "trials"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    
    # Foreign Keys
    session_id: int = Field(foreign_key="sessions.id")
    c3d_file_id: int = Field(foreign_key="c3d_files.id")
    
    # Relationships
    session: Session = Relationship(back_populates="trials")
    c3d_file: "C3DFile" = Relationship(back_populates="trials")
    
    # Metadata as JSON for flexible trial parameters and results
    parameters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    results: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class TrialCreate(TrialBase):
    """API model for creating a new trial."""
    session_id: int
    c3d_file_id: int
    parameters: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None

class TrialUpdate(SQLModel):
    """API model for updating an existing trial."""
    name: Optional[str] = None
    description: Optional[str] = None
    c3d_file_id: Optional[int] = None  # Can still be None in updates but validated in router
    parameters: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None

class TrialRead(TrialBase):
    """API response model for trial data."""
    id: int
    date_created: datetime
    date_modified: datetime
    session_id: int
    c3d_file_id: Optional[int] = None
    parameters: Dict[str, Any] = {}
    results: Dict[str, Any] = {} 