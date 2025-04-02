from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select, delete
from typing import List
from datetime import datetime

# Import models
from models.group import TrialGroup, TrialGroupCreate, TrialGroupUpdate, TrialGroupRead, GroupFileLink
from models.c3d_file import C3DFile
from models.response import FileRead # Assuming you have a FileRead model for file details
from models.marker import MarkerRead
from models.channel import ChannelRead
from models.event import EventRead

# Import database session dependency
from app import get_db_session

# For counting files
from sqlalchemy.sql import func

router = APIRouter()

def get_group_or_404(group_id: int, session: Session) -> TrialGroup:
    """Helper function to get a group by ID or raise 404."""
    group = session.get(TrialGroup, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group

def get_file_or_404(file_id: int, session: Session) -> C3DFile:
    """Helper function to get a file by ID or raise 404."""
    file = session.get(C3DFile, file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with id {file_id} not found")
    return file

@router.get("/groups/", response_model=List[TrialGroupRead], tags=["Groups"])
def get_groups(
    session: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """Get all trial groups with file count."""
    groups = session.exec(select(TrialGroup).offset(skip).limit(limit)).all()
    
    result = []
    for group in groups:
        # Count files in this group efficiently
        file_count = session.exec(
            select(func.count(GroupFileLink.file_id))
            .where(GroupFileLink.group_id == group.id)
        ).one()
        
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

@router.post("/groups/", response_model=TrialGroupRead, status_code=status.HTTP_201_CREATED, tags=["Groups"])
def create_group(
    group_data: TrialGroupCreate,
    session: Session = Depends(get_db_session)
):
    """Create a new trial group, optionally adding initial files."""
    db_group = TrialGroup(
        name=group_data.name, 
        description=group_data.description
    )
    session.add(db_group)
    session.commit()
    session.refresh(db_group) # Get the generated ID
    
    file_count = 0
    if group_data.file_ids:
        for file_id in group_data.file_ids:
            file = get_file_or_404(file_id, session) # Ensure file exists
            link = GroupFileLink(group_id=db_group.id, file_id=file_id)
            session.add(link)
            file_count += 1
        session.commit()
    
    return TrialGroupRead(
        id=db_group.id,
        name=db_group.name,
        description=db_group.description,
        date_created=db_group.date_created,
        date_modified=db_group.date_modified,
        file_count=file_count
    )

@router.get("/groups/{group_id}", response_model=TrialGroupRead, tags=["Groups"])
def get_group(
    group_id: int,
    session: Session = Depends(get_db_session)
):
    """Get a specific trial group by ID."""
    group = get_group_or_404(group_id, session)
    
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

@router.put("/groups/{group_id}", response_model=TrialGroupRead, tags=["Groups"])
def update_group(
    group_id: int,
    group_update: TrialGroupUpdate,
    session: Session = Depends(get_db_session)
):
    """Update a trial group's name or description."""
    db_group = get_group_or_404(group_id, session)
    
    update_data = group_update.dict(exclude_unset=True)
    updated = False
    for key, value in update_data.items():
        setattr(db_group, key, value)
        updated = True
        
    if updated:
        db_group.date_modified = datetime.now()
        session.add(db_group)
        session.commit()
        session.refresh(db_group)
    
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

@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Groups"])
def delete_group(
    group_id: int,
    session: Session = Depends(get_db_session)
):
    """Delete a trial group (does not delete the files, only the group and associations)."""
    db_group = get_group_or_404(group_id, session)
    
    # Delete associations first
    session.exec(delete(GroupFileLink).where(GroupFileLink.group_id == group_id))
    
    # Delete the group
    session.delete(db_group)
    session.commit()
    
    return None # Return None for 204 No Content

# --- Group File Management Endpoints ---

@router.get("/groups/{group_id}/files", response_model=List[FileRead], tags=["Groups"])
def get_group_files(
    group_id: int,
    session: Session = Depends(get_db_session)
):
    """Get all files associated with a specific group."""
    group = get_group_or_404(group_id, session) # Ensure group exists
    
    # Query files linked to this group
    files = session.exec(
        select(C3DFile)
        .join(GroupFileLink)
        .where(GroupFileLink.group_id == group_id)
    ).all()
    
    # Prepare the response using FileRead model
    response_files = []
    for file in files:
        # Efficiently load related data if needed for FileRead
        markers = file.markers # Assuming relationship loading works
        channels = file.analog_channels
        events = file.events
        
        response_files.append(
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
    return response_files

@router.post("/groups/{group_id}/files", status_code=status.HTTP_200_OK, tags=["Groups"])
def add_files_to_group(
    group_id: int,
    file_ids: List[int], # Expect a list of file IDs in the request body
    session: Session = Depends(get_db_session)
):
    """Add multiple files to a trial group."""
    group = get_group_or_404(group_id, session)
    
    added_count = 0
    skipped_count = 0
    not_found_ids = []

    # Get existing links for this group to avoid duplicates efficiently
    existing_file_ids = set(session.exec(
        select(GroupFileLink.file_id).where(GroupFileLink.group_id == group_id)
    ).all())

    for file_id in file_ids:
        if file_id in existing_file_ids:
            skipped_count += 1
            continue
            
        file = session.get(C3DFile, file_id) # Check if file exists
        if not file:
            not_found_ids.append(file_id)
            continue
            
        # Create new link
        link = GroupFileLink(group_id=group_id, file_id=file_id)
        session.add(link)
        added_count += 1
    
    if added_count > 0:
        group.date_modified = datetime.now()
        session.add(group)
        session.commit()
    
    response_detail = f"Added {added_count} files to group '{group.name}'. Skipped {skipped_count} duplicates."
    if not_found_ids:
        response_detail += f" Files not found: {not_found_ids}."
        
    if added_count == 0 and skipped_count == 0 and not not_found_ids:
         response_detail = "No new files were added (list might be empty or contain only duplicates/invalid IDs)."

    return {"detail": response_detail, "added_count": added_count, "skipped_count": skipped_count, "not_found_ids": not_found_ids}

@router.delete("/groups/{group_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Groups"])
def remove_file_from_group(
    group_id: int,
    file_id: int,
    session: Session = Depends(get_db_session)
):
    """Remove a specific file from a trial group."""
    group = get_group_or_404(group_id, session)
    file = get_file_or_404(file_id, session)
    
    # Find the link
    link = session.exec(
        select(GroupFileLink)
        .where(GroupFileLink.group_id == group_id, GroupFileLink.file_id == file_id)
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"File {file_id} not found in group {group_id}"
        )
    
    session.delete(link)
    group.date_modified = datetime.now() # Update modification time
    session.add(group)
    session.commit()
    
    return None # Return None for 204 No Content 