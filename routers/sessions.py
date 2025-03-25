from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Optional
from models.c3d_file import C3DFile
from app import get_db_session

router = APIRouter()

@router.get("/sessions/")
def get_sessions(
    classification: str | None = None,
    subject: str | None = None,
    session: Session = Depends(get_db_session)
):
    """Get all available sessions, optionally filtered by classification and subject."""
    if classification == "Uncategorized":
        classification = ""
    if subject == "Unknown":
        subject = ""
        
    query = select(C3DFile.session_name).distinct()
    
    # Apply filters if provided
    if classification is not None:
        query = query.where(C3DFile.classification == classification)
    if subject is not None:
        query = query.where(C3DFile.subject_name == subject)
        
    sessions = session.exec(query).all()
    
    # Filter out empty sessions and sort
    valid_sessions = sorted([s for s in sessions if s])
    
    # Add "Default" for files with no session
    if "" in sessions:
        valid_sessions.append("Default")
        
    return {"sessions": valid_sessions}
