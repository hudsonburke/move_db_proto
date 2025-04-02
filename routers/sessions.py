"""
Router for managing Sessions in the hierarchical structure.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as SQLModelSession, select, func
from dependencies import get_db_session
from models import (
    Session, SessionCreate, SessionUpdate, SessionRead,
    Subject, Trial
)

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)

@router.post("/", response_model=SessionRead)
def create_session(
    session: SessionCreate,
    db: SQLModelSession = Depends(get_db_session)
):
    """Create a new session in the database."""
    db_session = Session.from_orm(session)
    
    # Check if subject exists
    subject = db.get(Subject, session.subject_id)
    if not subject:
        raise HTTPException(
            status_code=404,
            detail=f"Subject with ID {session.subject_id} not found"
        )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    # Set trial count to 0 for a new session
    db_session_dict = db_session.dict()
    db_session_dict["trial_count"] = 0
    
    return db_session_dict

@router.get("/", response_model=List[SessionRead])
def get_sessions(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = Query(None, description="Filter by name"),
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    db: SQLModelSession = Depends(get_db_session)
):
    """Get a list of sessions with optional filtering."""
    query = select(Session)
    
    # Apply filters
    if name:
        query = query.where(Session.name.contains(name))
    if subject_id:
        query = query.where(Session.subject_id == subject_id)
    
    sessions = db.exec(query.offset(skip).limit(limit)).all()
    
    # Add trial counts
    result = []
    for session in sessions:
        session_dict = session.dict()
        trial_count = db.exec(
            select(func.count()).where(Trial.session_id == session.id)
        ).one()
        session_dict["trial_count"] = trial_count
        result.append(session_dict)
    
    return result

@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: int,
    db: SQLModelSession = Depends(get_db_session)
):
    """Get a specific session by ID."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add trial count
    session_dict = session.dict()
    trial_count = db.exec(
        select(func.count()).where(Trial.session_id == session.id)
    ).one()
    session_dict["trial_count"] = trial_count[0]
    
    return session_dict

@router.put("/{session_id}", response_model=SessionRead)
def update_session(
    session_id: int,
    session_update: SessionUpdate,
    db: SQLModelSession = Depends(get_db_session)
):
    """Update a specific session by ID."""
    db_session = db.get(Session, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update attributes from the request
    update_data = session_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_session, key, value)
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    # Add trial count
    session_dict = db_session.dict()
    trial_count = db.exec(
        select(func.count()).where(Trial.session_id == session_id)
    ).one()
    session_dict["trial_count"] = trial_count[0]
    
    return session_dict

@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: SQLModelSession = Depends(get_db_session)
):
    """Delete a session (will fail if it has associated trials)."""
    db_session = db.get(Session, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if session has trials
    trial_count = db.exec(
        select(func.count()).where(Trial.session_id == session_id)
    ).one()
    if trial_count[0] > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete session with associated trials. Remove trials first."
        )
    
    db.delete(db_session)
    db.commit()
    
    return None
