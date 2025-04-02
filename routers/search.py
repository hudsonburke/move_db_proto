from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import Any
from models.search import SearchQuery
from models.response import FileRead
from app import get_db_session, load_analyses
from models.c3d_file import C3DFile
from models.marker import Marker, MarkerRead
from models.channel import AnalogChannel, ChannelRead
from models.event import Event, EventRead
from sqlmodel import select, col
from sqlalchemy.sql import func
import re

router = APIRouter()

@router.post("/search/", response_model=dict)
def advanced_search(
    search_query: SearchQuery,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session)
):
    """Advanced search with request body."""
    return search_files(
        filename=search_query.filename,
        filename_regex=search_query.filename_regex,
        subject=search_query.subject,
        subject_regex=search_query.subject_regex,
        classification=search_query.classification,
        classification_regex=search_query.classification_regex,
        session_name=search_query.session_name,
        session_regex=search_query.session_regex,
        min_duration=search_query.min_duration,
        max_duration=search_query.max_duration,
        min_frame_count=search_query.min_frame_count,
        max_frame_count=search_query.max_frame_count,
        marker=search_query.marker,
        marker_regex=search_query.marker_regex,
        channel=search_query.channel,
        channel_regex=search_query.channel_regex,
        event=search_query.event,
        event_regex=search_query.event_regex,
        analysis_name=search_query.analysis_name,
        analysis_params=search_query.analysis_params,
        limit=limit,
        offset=offset,
        session=session
    )

@router.get("/files/", response_model=dict)
def get_search_files(
    filename: str | None = None,
    filename_regex: bool = False,
    subject: str | None = None,
    subject_regex: bool = False,
    classification: str | None = None,
    classification_regex: bool = False,
    session_name: str | None = None,
    session_regex: bool = False,
    min_duration: float | None = None,
    max_duration: float | None = None,
    min_frame_count: int | None = None,
    max_frame_count: int | None = None,
    marker: str | None = None,
    marker_regex: bool = False,
    channel: str | None = None,
    channel_regex: bool = False,
    event: str | None = None,
    event_regex: bool = False,
    analysis_name: str | None = None,
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    count_only: bool = False,
    session: Session = Depends(get_db_session)
):
    """Search for C3D files with various filters via GET endpoint."""
    return search_files(
        filename=filename,
        filename_regex=filename_regex,
        subject=subject,
        subject_regex=subject_regex,
        classification=classification,
        classification_regex=classification_regex,
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
        analysis_params=None,  # No analysis params for GET request
        limit=limit,
        offset=offset,
        count_only=count_only,
        session=session
    )

def search_files(
    filename: str | None = None,
    filename_regex: bool = False,
    subject: str | None = None,
    subject_regex: bool = False,
    classification: str | None = None,
    classification_regex: bool = False,
    session_name: str | None = None,
    session_regex: bool = False,
    min_duration: float | None = None,
    max_duration: float | None = None,
    min_frame_count: int | None = None,
    max_frame_count: int | None = None,
    marker: str | None = None,
    marker_regex: bool = False,
    channel: str | None = None,
    channel_regex: bool = False,
    event: str | None = None,
    event_regex: bool = False,
    analysis_name: str | None = None,
    analysis_params: dict[str, Any] | None = None,
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    count_only: bool = False,
    session: Session = Depends(get_db_session)
):
    """Search for C3D files with various filters."""
    query = select(C3DFile)
    print(f"Query: {query}")
    
    # Handle text search filters
    if filename:
        if filename_regex:
            query = query.where(C3DFile.filename.regexp_match(filename))
        else:
            query = query.where(col(C3DFile.filename).contains(filename))
    if subject:
        # Special handling for 'Unknown' subject
        if subject == "Unknown":
            query = query.where(C3DFile.subject_name == "")
        else:
            if subject_regex:
                query = query.where(C3DFile.subject_name.regexp_match(subject))
            else:
                query = query.where(col(C3DFile.subject_name).contains(subject))
    if classification:
        # Special handling for 'Uncategorized' classification
        if classification == "Uncategorized":
            query = query.where(C3DFile.classification == "")
        else:
            if classification_regex:
                query = query.where(C3DFile.classification.regexp_match(classification))
            else:
                query = query.where(col(C3DFile.classification).contains(classification))
    if session_name:
        # Special handling for 'Default' session
        if session_name == "Default":
            query = query.where(C3DFile.session_name == "")
        else:
            if session_regex:
                query = query.where(C3DFile.session_name.regexp_match(session_name))
            else:
                query = query.where(col(C3DFile.session_name).contains(session_name))
    
    # Handle numeric range filters
    if min_frame_count is not None:
        query = query.where(C3DFile.frame_count >= min_frame_count)
    if max_frame_count is not None:
        query = query.where(C3DFile.frame_count <= max_frame_count)
    
    # If count_only is True, return just the count
    count_query = select(func.count(C3DFile.filepath)).filter(*query._where_criteria)
    total_count = session.exec(count_query).one()
    
    if count_only:
        return {"total": total_count}
    
    # Execute base query with pagination
    files = session.exec(query.order_by(C3DFile.classification, C3DFile.subject_name, C3DFile.session_name, C3DFile.filename).offset(offset).limit(limit)).all()
    
    # For marker, channel, event, and duration filters, we need to post-process
    result_files = []
    filtered_count = 0
    
    for file in files:
        # Calculate duration
        duration = file.frame_count / file.sample_rate if file.sample_rate else 0.0
        
        # Apply duration filters
        if min_duration is not None and duration < min_duration:
            continue
        if max_duration is not None and duration > max_duration:
            continue
        
        # Get associated data
        markers = session.exec(select(Marker).where(Marker.file_id == file.filepath)).all()
        channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.filepath)).all()
        events = session.exec(select(Event).where(Event.file_id == file.filepath)).all()
        
        # Apply marker filter
        if marker:
            if marker_regex:
                pattern = re.compile(marker, re.IGNORECASE)
                if not any(bool(pattern.search(m.marker_name)) for m in markers):
                    continue
            elif not any(marker.lower() in m.marker_name.lower() for m in markers):
                continue
            
        # Apply channel filter
        if channel:
            if channel_regex:
                pattern = re.compile(channel, re.IGNORECASE)
                if not any(bool(pattern.search(c.channel_name)) for c in channels):
                    continue
            elif not any(channel.lower() in c.channel_name.lower() for c in channels):
                continue
            
        # Apply event filter
        if event:
            if event_regex:
                pattern = re.compile(event, re.IGNORECASE)
                if not any(bool(pattern.search(e.event_name)) for e in events):
                    continue
            elif not any(event.lower() in e.event_name.lower() for e in events):
                continue
        
        # # Apply analysis filter
        # if analysis_name:
        #     analyses = load_analyses()
        #     if analysis_name not in analyses:
        #         continue
        #     analysis_class = analyses[analysis_name]
        #     analysis = analysis_class(parameters=analysis_params or {})
        #     c3d = ezc3d.c3d(file.filepath)
        #     result = analysis.analyze(c3d)
        #     if not result["result"]:
        #         continue
        
        filtered_count += 1
        
        # Include file in results with its related data
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
    
    # Return pagination metadata along with results
    return {
        "files": result_files,
        "pagination": {
            "total": total_count,
            "filtered": filtered_count,
            "offset": offset,
            "limit": limit
        }
    }
