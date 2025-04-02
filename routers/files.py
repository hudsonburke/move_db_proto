from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, delete
from models.c3d_file import C3DFile, C3DFileCreate
from models.marker import Marker, MarkerRead
from models.channel import AnalogChannel, ChannelRead
from models.event import Event, EventRead
from models.response import FileRead
from models.search import FileQuery
from app import get_db_session
from sqlalchemy.sql import func
import urllib.parse
from models.analysis import Analysis
from typing import Optional, Dict, Any

router = APIRouter()

# Add both route patterns to match with and without trailing slash
@router.get("/files/", include_in_schema=True)
@router.get("/files", include_in_schema=True)
def get_files(
    filename: Optional[str] = None,
    filename_regex: bool = False,
    classification: Optional[str] = None,
    classification_regex: bool = False,
    subject: Optional[str] = None,
    subject_regex: bool = False,
    session_name: Optional[str] = None,
    session_regex: bool = False,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
    min_frame_count: Optional[int] = None,
    max_frame_count: Optional[int] = None,
    marker: Optional[str] = None,
    marker_regex: bool = False,
    channel: Optional[str] = None,
    channel_regex: bool = False,
    event: Optional[str] = None,
    event_regex: bool = False,
    analysis_name: Optional[str] = None,
    analysis_params: Optional[str] = None,
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session)
):
    """Get a list of C3D files with pagination and filtering."""
    try:
        # Parse analysis_params if provided as a string
        parsed_analysis_params = None
        if analysis_params:
            try:
                import json
                parsed_analysis_params = json.loads(analysis_params)
            except:
                pass
        
        # If any search parameters are provided, use the search function from search router
        if any([filename, classification, subject, session_name, min_duration, max_duration, 
                min_frame_count, max_frame_count, marker, channel, event, analysis_name]):
            from routers.search import search_files
            
            return search_files(
                filename=filename,
                filename_regex=filename_regex,
                classification=classification,
                classification_regex=classification_regex,
                subject=subject,
                subject_regex=subject_regex,
                session_name=session_name,
                session_regex=session_regex,
                min_duration=min_duration,
                max_duration=max_duration,
                min_frame_count=min_frame_count,
                max_frame_count=max_frame_count,
                marker=marker,
                marker_regex=marker_regex,
                channel=channel,
                channel_regex=channel_regex,
                event=event,
                event_regex=event_regex,
                analysis_name=analysis_name,
                analysis_params=parsed_analysis_params,
                limit=limit,
                offset=offset,
                session=session
            )
        
        # If no search parameters, just return all files with pagination
        query = select(C3DFile).order_by(C3DFile.classification, C3DFile.subject_name, C3DFile.session_name, C3DFile.filename).offset(offset).limit(limit)
        files = session.exec(query).all()
        
        # Get total count of files
        count_query = select(func.count(C3DFile.filepath))
        total_count = session.exec(count_query).one()
        
        result_files = []
        for file in files:
            # Get associated data
            markers = session.exec(select(Marker).where(Marker.file_id == file.filepath)).all()
            channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.filepath)).all()
            events = session.exec(select(Event).where(Event.file_id == file.filepath)).all()
            
            result_files.append(
                FileRead(
                    id=file.id,
                    filename=file.filename,
                    filepath=file.filepath,
                    file_size=file.file_size,
                    date_added=file.date_added,
                    duration=file.frame_count / file.sample_rate if file.sample_rate else 0.0,
                    frame_count=file.frame_count,
                    sample_rate=file.sample_rate,
                    subject_name=file.subject_name,
                    classification=file.classification,
                    session_name=file.session_name,
                    file_metadata=file.file_metadata,
                    markers=[MarkerRead(marker_name=m.marker_name) for m in markers],
                    channels=[ChannelRead(channel_name=c.channel_name) for c in channels],
                    events=[EventRead(event_name=e.event_name, event_time=e.event_time) for e in events]
                )
            )
        
        # Return in the format expected by the frontend - with files and pagination
        return {
            "files": result_files,
            "pagination": {
                "total": total_count,
                "filtered": len(result_files),
                "offset": offset,
                "limit": limit
            }
        }
    except Exception as e:
        print(f"Error in get_files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# The specific filepath route must come AFTER the general route
@router.get("/files/{filepath:path}", response_model=FileRead)
def get_file(filepath: str, session: Session = Depends(get_db_session)):
    """Get a specific C3D file by filepath."""
    # URL decode the filepath
    filepath = urllib.parse.unquote(filepath)
    
    # Get file by filepath
    file = session.get(C3DFile, filepath)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get associated data
    markers = session.exec(select(Marker).where(Marker.file_id == file.id)).all()
    channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.id)).all()
    events = session.exec(select(Event).where(Event.file_id == file.id)).all()
    
    return FileRead(
        id=file.id,
        filename=file.filename,
        filepath=file.filepath,
        file_size=file.file_size,
        date_added=file.date_added,
        duration=file.frame_count / file.sample_rate if file.sample_rate else 0.0,
        frame_count=file.frame_count,
        sample_rate=file.sample_rate,
        subject_name=file.subject_name,
        classification=file.classification,
        session_name=file.session_name,
        file_metadata=file.file_metadata,
        markers=[MarkerRead(marker_name=m.marker_name) for m in markers],
        channels=[ChannelRead(channel_name=c.channel_name) for c in channels],
        events=[EventRead(event_name=e.event_name, event_time=e.event_time) for e in events]
    )

@router.delete("/files/{filepath:path}")
def delete_file(filepath: str, session: Session = Depends(get_db_session)):
    """Delete a C3D file database entry."""
    # URL decode the filepath
    filepath = urllib.parse.unquote(filepath)
    
    file = session.get(C3DFile, filepath)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete associated data
    session.exec(delete(Marker).where(Marker.file_id == filepath))
    session.exec(delete(AnalogChannel).where(AnalogChannel.file_id == filepath))
    session.exec(delete(Event).where(Event.file_id == filepath))
    
    # Delete file record
    session.delete(file)
    session.commit()
    
    return {"detail": "File deleted successfully"}

@router.post("/files/")
def create_file(file: C3DFileCreate, analyses: list[int], session: Session = Depends(get_db_session)):
    """Create a new C3D file record."""
    db_file = C3DFile.model_validate(file)
    session.add(db_file)
    session.commit()
    session.refresh(db_file)
    
    # Link selected analyses to the C3D file
    for analysis_id in analyses:
        analysis = session.get(Analysis, analysis_id)
        if analysis:
            db_file.analyses.append(analysis)
    session.commit()
    
    return db_file

@router.put("/files/{file_id}")
def update_file(file_id: int, file: C3DFileCreate, analyses: list[int], session: Session = Depends(get_db_session)):
    """Update an existing C3D file record."""
    db_file = session.get(C3DFile, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    for key, value in file.dict().items():
        setattr(db_file, key, value)
    session.commit()
    
    # Update linked analyses
    db_file.analyses.clear()
    for analysis_id in analyses:
        analysis = session.get(Analysis, analysis_id)
        if analysis:
            db_file.analyses.append(analysis)
    session.commit()
    
    return db_file

@router.get("/files/id/{file_id}", response_model=FileRead)
def get_file_by_id(file_id: int, session: Session = Depends(get_db_session)):
    """Get a specific C3D file by ID."""
    file = session.get(C3DFile, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get associated data
    markers = session.exec(select(Marker).where(Marker.file_id == file.id)).all()
    channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.id)).all()
    events = session.exec(select(Event).where(Event.file_id == file.id)).all()
    
    return FileRead(
        id=file.id,
        filename=file.filename,
        filepath=file.filepath,
        file_size=file.file_size,
        date_added=file.date_added,
        duration=file.frame_count / file.sample_rate if file.sample_rate else 0.0,
        frame_count=file.frame_count,
        sample_rate=file.sample_rate,
        subject_name=file.subject_name,
        classification=file.classification,
        session_name=file.session_name,
        file_metadata=file.file_metadata,
        markers=[MarkerRead(marker_name=m.marker_name) for m in markers],
        channels=[ChannelRead(channel_name=c.channel_name) for c in channels],
        events=[EventRead(event_name=e.event_name, event_time=e.event_time) for e in events]
    )
