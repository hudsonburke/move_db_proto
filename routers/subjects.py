from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Optional
from models.c3d_file import C3DFile
from app import get_db_session

router = APIRouter()

@router.get("/subjects/")
def get_subjects(
    classification: str | None = None,
    session: Session = Depends(get_db_session)
):
    """Get all available subjects, optionally filtered by classification."""
    if classification == "Uncategorized":
        classification = ""
        
    query = select(C3DFile.subject_name).distinct()
    if classification is not None:
        query = query.where(C3DFile.classification == classification)
        
    subjects = session.exec(query).all()
    
    # Filter out empty subjects and sort
    valid_subjects = sorted([s for s in subjects if s])
    
    # Add "Unknown" for files with no subject
    if "" in subjects:
        valid_subjects.append("Unknown")
        
    return {"subjects": valid_subjects}
