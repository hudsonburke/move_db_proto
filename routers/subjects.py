"""
Router for managing Subjects in the hierarchical structure.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from dependencies import get_db_session
from models import (
    Subject, SubjectCreate, SubjectUpdate, SubjectRead,
    Classification, Session as SessionModel
)

router = APIRouter(
    prefix="/subjects",
    tags=["subjects"],
)

@router.post("/", response_model=SubjectRead)
def create_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db_session)
):
    """Create a new subject in the database."""
    db_subject = Subject.from_orm(subject)
    
    # Check if classification exists if provided
    if subject.classification_id:
        classification = db.get(Classification, subject.classification_id)
        if not classification:
            raise HTTPException(
                status_code=404,
                detail=f"Classification with ID {subject.classification_id} not found"
            )
    
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    
    # Set session count to 0 for a new subject
    db_subject_dict = db_subject.dict()
    db_subject_dict["session_count"] = 0
    
    return db_subject_dict

@router.get("/", response_model=List[SubjectRead])
def get_subjects(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = Query(None, description="Filter by name"),
    classification_id: Optional[int] = Query(None, description="Filter by classification ID"),
    db: Session = Depends(get_db_session)
):
    """Get a list of subjects with optional filtering."""
    query = select(Subject)
    
    # Apply filters
    if name:
        query = query.where(Subject.name.contains(name))
    if classification_id:
        query = query.where(Subject.classification_id == classification_id)
    
    subjects = db.exec(query.offset(skip).limit(limit)).all()
    
    # Add session counts
    result = []
    for subject in subjects:
        subject_dict = subject.dict()
        session_count = db.exec(
            select(func.count()).where(SessionModel.subject_id == subject.id)
        ).one()
        subject_dict["session_count"] = session_count
        result.append(subject_dict)
    
    return result

@router.get("/{subject_id}", response_model=SubjectRead)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a specific subject by ID."""
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Add session count
    subject_dict = subject.dict()
    session_count = db.exec(
        select(func.count()).where(SessionModel.subject_id == subject.id)
    ).one()
    subject_dict["session_count"] = session_count[0]
    
    return subject_dict

@router.put("/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: int,
    subject_update: SubjectUpdate,
    db: Session = Depends(get_db_session)
):
    """Update a specific subject by ID."""
    db_subject = db.get(Subject, subject_id)
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Check if classification exists if being updated
    if subject_update.classification_id is not None:
        classification = db.get(Classification, subject_update.classification_id)
        if not classification and subject_update.classification_id is not None:
            raise HTTPException(
                status_code=404,
                detail=f"Classification with ID {subject_update.classification_id} not found"
            )
    
    # Update attributes from the request
    update_data = subject_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_subject, key, value)
    
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    
    # Add session count
    subject_dict = db_subject.dict()
    session_count = db.exec(
        select(func.count()).where(SessionModel.subject_id == subject_id)
    ).one()
    subject_dict["session_count"] = session_count[0]
    
    return subject_dict

@router.delete("/{subject_id}", status_code=204)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db_session)
):
    """Delete a subject (will fail if it has associated sessions)."""
    db_subject = db.get(Subject, subject_id)
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Check if subject has sessions
    session_count = db.exec(
        select(func.count()).where(SessionModel.subject_id == subject_id)
    ).one()
    if session_count[0] > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete subject with associated sessions. Remove sessions first."
        )
    
    db.delete(db_subject)
    db.commit()
    
    return None
