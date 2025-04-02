"""
Router for managing Classifications in the hierarchical structure.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from dependencies import get_db_session
from models import (
    Classification, ClassificationCreate, ClassificationUpdate, ClassificationRead,
    Subject
)

router = APIRouter(
    prefix="/classifications",
    tags=["classifications"],
)

@router.post("/", response_model=ClassificationRead)
def create_classification(
    classification: ClassificationCreate,
    db: Session = Depends(get_db_session)
):
    """Create a new classification in the database."""
    db_classification = Classification.from_orm(classification)
    db.add(db_classification)
    db.commit()
    db.refresh(db_classification)
    
    # Set subject count to 0 for a new classification
    db_classification_dict = db_classification.dict()
    db_classification_dict["subject_count"] = 0
    
    return db_classification_dict

@router.get("/", response_model=List[ClassificationRead])
def get_classifications(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = Query(None, description="Filter by name"),
    db: Session = Depends(get_db_session)
):
    """Get a list of classifications with optional filtering."""
    query = select(Classification)
    
    if name:
        query = query.where(Classification.name.contains(name))
    
    classifications = db.exec(query.offset(skip).limit(limit)).all()
    
    # Add subject counts
    result = []
    for classification in classifications:
        classification_dict = classification.dict()
        subject_count = db.exec(
            select(func.count()).where(Subject.classification_id == classification.id)
        ).one()
        classification_dict["subject_count"] = subject_count
        result.append(classification_dict)
    
    return result

@router.get("/{classification_id}", response_model=ClassificationRead)
def get_classification(
    classification_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a specific classification by ID."""
    classification = db.get(Classification, classification_id)
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Add subject count
    classification_dict = classification.dict()
    subject_count = db.exec(
        select(func.count()).where(Subject.classification_id == classification.id)
    ).one()
    classification_dict["subject_count"] = subject_count
    
    return classification_dict

@router.put("/{classification_id}", response_model=ClassificationRead)
def update_classification(
    classification_id: int,
    classification_update: ClassificationUpdate,
    db: Session = Depends(get_db_session)
):
    """Update a specific classification by ID."""
    db_classification = db.get(Classification, classification_id)
    if not db_classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Update attributes from the request
    update_data = classification_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_classification, key, value)
    
    db.add(db_classification)
    db.commit()
    db.refresh(db_classification)
    
    # Add subject count
    classification_dict = db_classification.dict()
    subject_count = db.exec(
        select(func.count()).where(Subject.classification_id == db_classification.id)
    ).one()
    classification_dict["subject_count"] = subject_count
    
    return classification_dict

@router.delete("/{classification_id}", status_code=204)
def delete_classification(
    classification_id: int,
    db: Session = Depends(get_db_session)
):
    """Delete a classification (will fail if it has associated subjects)."""
    db_classification = db.get(Classification, classification_id)
    if not db_classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Check if classification has subjects
    subject_count = db.exec(
        select(func.count()).where(Subject.classification_id == classification_id)
    ).one()
    if subject_count > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete classification with associated subjects. Remove subjects first."
        )
    
    db.delete(db_classification)
    db.commit()
    
    return None
