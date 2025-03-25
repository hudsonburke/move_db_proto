from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models.c3d_file import C3DFile
from app import get_db_session

router = APIRouter()

@router.get("/classifications/")
def get_classifications(session: Session = Depends(get_db_session)):
    """Get all available classifications in the database."""
    query = select(C3DFile.classification).distinct()
    classifications = session.exec(query).all()
    
    # Filter out empty classifications and sort
    valid_classifications = sorted([c for c in classifications if c])
    
    # Add "Uncategorized" for files with no classification
    if "" in classifications:
        valid_classifications.append("Uncategorized")
        
    return {"classifications": valid_classifications}
