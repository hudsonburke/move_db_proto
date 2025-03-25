from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, delete
from typing import List
from models.group import TrialGroup, TrialGroupCreate, TrialGroupUpdate, TrialGroupRead, GroupFileLink
from models.c3d_file import C3DFile
from models.response import FileRead
from models.marker import Marker, MarkerRead
from models.channel import AnalogChannel, ChannelRead
from models.event import Event, EventRead
from app import get_db_session
from sqlalchemy.sql import func

router = APIRouter()

@router.get("/groups/", response_model=list[TrialGroupRead])
def get_groups(
    session: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """Get all trial groups with file count for each group."""
    groups = session.exec(select(TrialGroup).offset(skip).limit(limit)).all()
    
    result = []
    for group in groups:
        # Count files in this group
        file_count = session.exec(
            select(func.count(GroupFileLink.file_id))
            .where(GroupFileLink.group_id == group.id)
        ).one()
        
        # Add to result with file count
        result.append(
            TrialGroupRead(
                id=group.id,
                name=group.name,
                description=group.description,
                date_created=group.date_created,
                date_modified=group.date_modified,
                file_count=file_count
            )
        )
    
    return result

@router.post("/groups/", response_model=TrialGroupRead)
def create_group(
    group: TrialGroupCreate,
    session: Session = Depends(get_db_session)
):
    """Create a new trial group with optional initial files."""
    db_group = TrialGroup(
        name=group.name, 
        description=group.description
    )
    session.add(db_group)
    session.commit()
    session.refresh(db_group)
    
    # Add any initial files to the group
    file_count = 0
    for file_id in group.file_ids:
        file = session.get(C3DFile, file_id)
        if file:
            link = GroupFileLink(group_id=db_group.id, file_id=file_id)
            session.add(link)
            file_count += 1
    
    if file_count > 0:
        session.commit()
    
    return TrialGroupRead(
        id=db_group.id,
        name=db_group.name,
        description=db_group.description,
        date_created=db_group.date_created,
        date_modified=db_group.date_modified,
        file_count=file_count
    )

@router.get("/groups/{group_id}", response_model=TrialGroupRead)
def get_group(
    group_id: int,
    session: Session = Depends(get_db_session)
):
    """Get a specific trial group by ID with file count."""
    group = session.get(TrialGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Count files in this group
    file_count = session.exec(
        select(func.count(GroupFileLink.file_id))
        .where(GroupFileLink.group_id == group_id)
    ).one()
    
    return TrialGroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        date_created=group.date_created,
        date_modified=group.date_modified,
        file_count=file_count
    )

@router.put("/groups/{group_id}", response_model=TrialGroupRead)
def update_group(
    group_id: int,
    group_update: TrialGroupUpdate,
    session: Session = Depends(get_db_session)
):
    """Update a trial group's metadata."""
    db_group = session.get(TrialGroup, group_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Update fields if provided
    group_data = group_update.dict(exclude_unset=True)
    for key, value in group_data.items():
        setattr(db_group, key, value)
        
    # Update modification date
    db_group.date_modified = datetime.now()
    
    session.add(db_group)
    session.commit()
    session.refresh(db_group)
    
    # Count files in this group
    file_count = session.exec(
        select(func.count(GroupFileLink.file_id))
        .where(GroupFileLink.group_id == group_id)
    ).one()
    
    return TrialGroupRead(
        id=db_group.id,
        name=db_group.name,
        description=db_group.description,
        date_created=db_group.date_created,
        date_modified=db_group.date_modified,
        file_count=file_count
    )

@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    session: Session = Depends(get_db_session)
):
    """Delete a trial group and its file associations."""
    db_group = session.get(TrialGroup, group_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Delete all file links
    session.exec(delete(GroupFileLink).where(GroupFileLink.group_id == group_id))
    
    # Delete the group
    session.delete(db_group)
    session.commit()
    
    return {"detail": "Group deleted successfully"}

@router.get("/groups/{group_id}/files", response_model=list[FileRead])
def get_group_files(
    group_id: int,
    session: Session = Depends(get_db_session)
):
    """Get all files in a specific group."""
    # Check if group exists
    group = session.get(TrialGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get all file IDs in this group
    file_links = session.exec(
        select(GroupFileLink.file_id)
        .where(GroupFileLink.group_id == group_id)
    ).all()
    
    # Get the files
    files = []
    for file_id in file_links:
        file = session.get(C3DFile, file_id)
        if file:
            # Get associated data
            markers = session.exec(select(Marker).where(Marker.file_id == file.id)).all()
            channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.id)).all()
            events = session.exec(select(Event).where(Event.file_id == file.id)).all()
            
            files.append(
                FileRead(
                    id=file.id,
                    filename=file.filename,
                    filepath=file.filepath,
                    file_size=file.file_size,
                    date_added=file.date_added,
                    duration=file.duration,
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
    
    return files

@router.post("/groups/{group_id}/files")
def add_files_to_group(
    group_id: int,
    file_ids: list[int],
    session: Session = Depends(get_db_session)
):
    """Add files to a trial group."""
    # Check if group exists
    group = session.get(TrialGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    added_count = 0
    for file_id in file_ids:
        # Check if file exists
        file = session.get(C3DFile, file_id)
        if not file:
            continue
            
        # Check if link already exists
        existing_link = session.exec(
            select(GroupFileLink)
            .where(GroupFileLink.group_id == group_id, GroupFileLink.file_id == file_id)
        ).first()
        
        if not existing_link:
            # Create new link
            link = GroupFileLink(group_id=group_id, file_id=file_id)
            session.add(link)
            added_count += 1
    
    # Update group modification date
    group.date_modified = datetime.now()
    session.add(group)
    
    if added_count > 0:
        session.commit()
    
    return {"detail": f"Added {added_count} files to group"}

@router.delete("/groups/{group_id}/files/{file_id}")
def remove_file_from_group(
    group_id: int,
    file_id: int,
    session: Session = Depends(get_db_session)
):
    """Remove a file from a trial group."""
    # Check if link exists
    link = session.exec(
        select(GroupFileLink)
        .where(GroupFileLink.group_id == group_id, GroupFileLink.file_id == file_id)
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="File not found in group")
    
    # Remove the link
    session.delete(link)
    
    # Update group modification date
    group = session.get(TrialGroup, group_id)
    if group:
        group.date_modified = datetime.now()
        session.add(group)
    
    session.commit()
    
    return {"detail": "File removed from group"}
