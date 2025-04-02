from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select
from models.c3d_file import C3DFile
from models.marker import Marker, MarkerRead
from models.channel import AnalogChannel, ChannelRead
from models.event import Event, EventRead
from models.response import FileRead
from app import get_db_session
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.get("/files/", include_in_schema=True)
@router.get("/files", include_in_schema=True)
def list_files(
    filename: Optional[str] = None,
    filename_regex: bool = False,
    classification: Optional[str] = None,
    classification_regex: bool = False,
    subject: Optional[str] = None,
    subject_regex: bool = False,
    session_name: Optional[str] = None,
    session_regex: bool = False,
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
        # If any search parameters are provided, use the search function from search router
        if any([filename, classification, subject, session_name, 
                min_frame_count, max_frame_count, marker, channel, event, analysis_name]):
            from routers.search import search_files
            
            # Parse analysis_params if provided as a string
            parsed_analysis_params = None
            if analysis_params:
                try:
                    import json
                    parsed_analysis_params = json.loads(analysis_params)
                except Exception as e:
                    print(f"Error parsing analysis_params: {e}")
            
            # Note: Removed duration parameters as they're not in the model
            return search_files(
                filename=filename,
                filename_regex=filename_regex,
                classification=classification,
                classification_regex=classification_regex,
                subject=subject,
                subject_regex=subject_regex,
                session_name=session_name,
                session_regex=session_regex,
                min_duration=None,  # Set to None since not in C3DFile model
                max_duration=None,  # Set to None since not in C3DFile model
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
        query = select(C3DFile).order_by(C3DFile.classification, C3DFile.subject_name, C3DFile.session_name, C3DFile.filepath).offset(offset).limit(limit)
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
            
            # Calculate duration based on frame count and sample rate if available
            duration = None
            if hasattr(file, 'frame_count') and hasattr(file, 'sample_rate') and file.sample_rate:
                duration = file.frame_count / file.sample_rate
            
            # Get date_created or use current date if not available
            date_created = getattr(file, 'date_created', datetime.now()) if hasattr(file, 'date_created') else datetime.now()
            
            # Get filename from filepath if not available
            filename = getattr(file, 'filename', file.filepath.split('/')[-1]) if hasattr(file, 'filename') else file.filepath.split('/')[-1]
            
            # Get file_size or use 0 if not available
            file_size = getattr(file, 'file_size', 0) if hasattr(file, 'file_size') else 0
            
            # Get file_metadata or use empty dict if not available
            file_metadata = getattr(file, 'file_metadata', {}) if hasattr(file, 'file_metadata') else {}
            
            result_files.append(
                FileRead(
                    id=file.id,
                    filename=filename,
                    filepath=file.filepath,
                    file_size=file_size,
                    date_added=date_created,
                    duration=duration if duration is not None else 0.0,
                    frame_count=getattr(file, 'frame_count', 0),
                    sample_rate=getattr(file, 'sample_rate', 0.0),
                    subject_name=getattr(file, 'subject_name', None),
                    classification=getattr(file, 'classification', None),
                    session_name=getattr(file, 'session_name', None),
                    file_metadata=file_metadata,
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
        print(f"Error in list_files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")