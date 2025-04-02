"""
Router for managing Trials in the hierarchical structure.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from dependencies import get_db_session
from models import (
    Trial, TrialCreate, TrialUpdate, TrialRead,
    Session as SessionModel, C3DFile
)

router = APIRouter(
    prefix="/trials",
    tags=["trials"],
)

@router.post("/", response_model=TrialRead)
def create_trial(
    trial: TrialCreate,
    db: Session = Depends(get_db_session)
):
    """Create a new trial in the database."""
    db_trial = Trial.from_orm(trial)
    
    # Check if session exists
    session = db.get(SessionModel, trial.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {trial.session_id} not found"
        )
    
    # Check if C3D file exists (now required)
    c3d_file = db.get(C3DFile, trial.c3d_file_id)
    if not c3d_file:
        raise HTTPException(
            status_code=404,
            detail=f"C3D file with ID {trial.c3d_file_id} not found"
        )
    
    db.add(db_trial)
    db.commit()
    db.refresh(db_trial)
    
    return db_trial.dict()

@router.get("/", response_model=List[TrialRead])
def get_trials(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = Query(None, description="Filter by name"),
    session_id: Optional[int] = Query(None, description="Filter by session ID"),
    c3d_file_id: Optional[int] = Query(None, description="Filter by C3D file ID"),
    has_results: Optional[bool] = Query(None, description="Filter by presence of results"),
    db: Session = Depends(get_db_session)
):
    """Get a list of trials with optional filtering."""
    query = select(Trial)
    
    # Apply filters
    if name:
        query = query.where(Trial.name.contains(name))
    if session_id:
        query = query.where(Trial.session_id == session_id)
    if c3d_file_id:
        query = query.where(Trial.c3d_file_id == c3d_file_id)
    if has_results is not None:
        if has_results:
            query = query.where(func.json_array_length(Trial.results) > 0)
        else:
            query = query.where(func.json_array_length(Trial.results) == 0)
    
    trials = db.exec(query.offset(skip).limit(limit)).all()
    
    return [trial.dict() for trial in trials]

@router.get("/{trial_id}", response_model=TrialRead)
def get_trial(
    trial_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a specific trial by ID."""
    trial = db.get(Trial, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    
    return trial.dict()

@router.put("/{trial_id}", response_model=TrialRead)
def update_trial(
    trial_id: int,
    trial_update: TrialUpdate,
    db: Session = Depends(get_db_session)
):
    """Update a specific trial by ID."""
    db_trial = db.get(Trial, trial_id)
    if not db_trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    
    # Check if C3D file exists if being updated
    if trial_update.c3d_file_id is not None:
        c3d_file = db.get(C3DFile, trial_update.c3d_file_id)
        if not c3d_file:
            raise HTTPException(
                status_code=404,
                detail=f"C3D file with ID {trial_update.c3d_file_id} not found"
            )
    
    # Update attributes from the request
    update_data = trial_update.dict(exclude_unset=True)
    
    # Special handling for nested JSON fields (parameters, results)
    if "parameters" in update_data and update_data["parameters"] is not None:
        # Merge existing parameters with new ones
        if db_trial.parameters is None:
            db_trial.parameters = {}
        db_trial.parameters.update(update_data["parameters"])
        del update_data["parameters"]
        
    if "results" in update_data and update_data["results"] is not None:
        # Merge existing results with new ones
        if db_trial.results is None:
            db_trial.results = {}
        db_trial.results.update(update_data["results"])
        del update_data["results"]
    
    # Update remaining fields
    for key, value in update_data.items():
        setattr(db_trial, key, value)
    
    db.add(db_trial)
    db.commit()
    db.refresh(db_trial)
    
    return db_trial.dict()

@router.patch("/{trial_id}/results", response_model=TrialRead)
def update_trial_results(
    trial_id: int,
    results: Dict[str, Any],
    db: Session = Depends(get_db_session)
):
    """Update just the results field of a trial (for user code to update)."""
    db_trial = db.get(Trial, trial_id)
    if not db_trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    
    # Merge existing results with new ones
    if db_trial.results is None:
        db_trial.results = {}
    db_trial.results.update(results)
    
    db.add(db_trial)
    db.commit()
    db.refresh(db_trial)
    
    return db_trial.dict()

@router.delete("/{trial_id}", status_code=204)
def delete_trial(
    trial_id: int,
    db: Session = Depends(get_db_session)
):
    """Delete a trial."""
    db_trial = db.get(Trial, trial_id)
    if not db_trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    
    db.delete(db_trial)
    db.commit()
    
    return None 