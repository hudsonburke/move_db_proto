import os
import time
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import Session, create_engine, select
from datetime import datetime
from models.c3d_file import C3DFile
from models.marker import Marker
from models.channel import AnalogChannel
from models.event import Event
from app import DATABASE_URL
from models.analysis import C3DDataExtractor, Analysis
# Import hierarchy models
from models.hierarchy import (
    Classification, ClassificationCreate, 
    Subject, SubjectCreate,
    Session as SessionModel, SessionCreate,
    Trial, TrialCreate
)

router = APIRouter()

# Define request model
class DirectoryScanRequest(BaseModel):
    root_directory: str

# Create a separate engine for background tasks
background_engine = create_engine(DATABASE_URL)

@router.post("/directory-scan")
async def scan_directory(request: DirectoryScanRequest, background_tasks: BackgroundTasks):
    """Scan a directory and its subdirectories for C3D files and index their metadata."""
    if not os.path.exists(request.root_directory):
        raise HTTPException(status_code=404, detail="Root directory not found")
    
    # Start the scanning in a background task to prevent hanging the web interface
    background_tasks.add_task(scan_directory_background, request.root_directory)
    
    return {"detail": "Directory scan started in background", "status": "processing"}

def scan_directory_background(root_directory: str):
    """Background task to scan a directory for C3D files."""
    # Create a new session specifically for the background task
    with Session(background_engine) as session:
        indexed_files = []
        skipped_files = []
        
        # File processing timeout (10 seconds per file)
        file_timeout = 10  
        
        # Directory traversal timeout (5 minutes total)
        dir_timeout_seconds = 300
        start_time = time.time()
        
        # Maximum files to process in one batch
        max_files = 1000
        files_processed = 0
        
        for root, _, files in os.walk(root_directory):
            # Check if we've exceeded the directory traversal timeout
            if time.time() - start_time > dir_timeout_seconds:
                print(f"Directory scan timed out after {dir_timeout_seconds} seconds")
                break
                
            # Check if we've exceeded the maximum file count
            if files_processed >= max_files:
                print(f"Directory scan stopped after processing {max_files} files")
                break
                
            for file in files:
                if file.lower().endswith(".c3d"):
                    filepath = os.path.join(root, file)
                    
                    try:
                        # Check file size before processing (skip if > 100MB)
                        file_size = os.path.getsize(filepath)
                        if file_size > 100 * 1024 * 1024:  # 100MB
                            skipped_files.append(file)
                            continue
                        
                        # Set a timeout for processing this file
                        file_start = time.time()
                        
                        # Extract data and create entries
                        extractor = C3DDataExtractor()
                        c3d_data = extractor.analyze(filepath)
                        
                        # Check if file processing took too long
                        if time.time() - file_start > file_timeout:
                            skipped_files.append(file)
                            continue
                        
                        # Parse directory structure for classification/subject/session
                        rel_path = os.path.relpath(root, root_directory)
                        path_parts = rel_path.split(os.path.sep)
                        
                        classification_name = "Default"
                        subject_name = c3d_data["subject_name"] or "Unknown Subject"
                        session_name = "Default Session"
                        trial_name = os.path.splitext(file)[0]  # Filename without extension as trial name
                        
                        # If path follows expected structure: Classification/Subject/Session/*.c3d
                        if len(path_parts) >= 3 and path_parts[0] != '.':
                            classification_name = path_parts[0]
                            if not c3d_data["subject_name"]:  # Only override if not already set from C3D metadata
                                subject_name = path_parts[1]
                            session_name = path_parts[2]
                        elif len(path_parts) == 2 and path_parts[0] != '.':
                            classification_name = path_parts[0]
                            if not c3d_data["subject_name"]:
                                subject_name = path_parts[1]
                        elif len(path_parts) == 1 and path_parts[0] != '.':
                            classification_name = path_parts[0]
                        
                        # --- Convert ezc3d Parameters to Dict --- 
                        metadata_dict = {}
                        if "metadata" in c3d_data and hasattr(c3d_data["metadata"], 'groups'):
                            try:
                                for group_name, group_data in c3d_data["metadata"].groups():
                                    metadata_dict[group_name] = {}
                                    if hasattr(group_data, 'parameters'):
                                        for param_name, param_data in group_data.parameters():
                                            # Attempt to get serializable value, handle potential issues
                                            try:
                                                value = param_data.values
                                                # Basic check for numpy arrays or other non-serializable types
                                                if hasattr(value, 'tolist'): 
                                                    value = value.tolist()
                                                elif isinstance(value, (int, float, str, bool, list, dict, type(None))):
                                                    pass # Already serializable
                                                else:
                                                    value = str(value) # Fallback to string representation
                                                metadata_dict[group_name][param_name] = value
                                            except Exception as param_err:
                                                metadata_dict[group_name][param_name] = f"Error serializing"
                            except Exception:
                                 pass
                        # --- End Conversion ---

                        # Create database entry with id as primary key and filepath as unique identifier
                        db_file = C3DFile(
                            filename=file,
                            filepath=filepath,  # unique identifier
                            file_size=file_size,
                            # Use date_added from file stats if available, else now
                            date_added=datetime.fromtimestamp(os.path.getctime(filepath)), 
                            date_modified=datetime.fromtimestamp(os.path.getmtime(filepath)),
                            # Removed duration - calculate on read
                            frame_count=c3d_data["frame_count"],
                            sample_rate=c3d_data["sample_rate"],
                            subject_name=subject_name,
                            classification=classification_name,
                            session_name=session_name,
                            file_metadata=metadata_dict, # Use the converted dict
                            has_marker_data=bool(c3d_data["markers"]),
                            has_analog_data=bool(c3d_data["channels"]),
                            has_event_data=bool(c3d_data["events"])
                        )
                        
                        try:
                            # Start transaction for adding the file and creating hierarchy
                            session.add(db_file)
                            session.commit()
                            session.refresh(db_file)  # Refresh to get the assigned id
                            
                            # Add markers using the file id
                            for marker_name in c3d_data["markers"]:
                                marker = Marker(
                                    file_id=db_file.id,  # Use id instead of filepath
                                    marker_name=marker_name
                                )
                                session.add(marker)
                            
                            # Add channels using the file id
                            for channel_name in c3d_data["channels"]:
                                channel = AnalogChannel(
                                    file_id=db_file.id,  # Use id instead of filepath
                                    channel_name=channel_name
                                )
                                session.add(channel)
                            
                            # Add events using the file id
                            for event_name, event_time in c3d_data["events"]:
                                event = Event(
                                    file_id=db_file.id,  # Use id instead of filepath
                                    event_name=event_name,
                                    event_time=event_time
                                )
                                session.add(event)
                            
                            # Now create or get the classification > subject > session > trial hierarchy
                            
                            # 1. Find or create Classification
                            classification_query = select(Classification).where(Classification.name == classification_name)
                            classification = session.exec(classification_query).first()
                            if not classification:
                                classification = Classification(
                                    name=classification_name,
                                    description=f"Auto-created from directory scan: {classification_name}"
                                )
                                session.add(classification)
                                session.commit()
                                session.refresh(classification)
                            
                            # 2. Find or create Subject (within Classification)
                            subject_query = select(Subject).where(
                                (Subject.name == subject_name) & 
                                (Subject.classification_id == classification.id)
                            )
                            subject = session.exec(subject_query).first()
                            if not subject:
                                subject = Subject(
                                    name=subject_name,
                                    description=f"Auto-created from directory scan",
                                    classification_id=classification.id,
                                    demographics={"source": "filesystem_import"}
                                )
                                session.add(subject)
                                session.commit()
                                session.refresh(subject)
                            
                            # 3. Find or create Session (within Subject)
                            session_query = select(SessionModel).where(
                                (SessionModel.name == session_name) & 
                                (SessionModel.subject_id == subject.id)
                            )
                            db_session = session.exec(session_query).first()
                            if not db_session:
                                db_session = SessionModel(
                                    name=session_name,
                                    description=f"Auto-created from directory scan",
                                    subject_id=subject.id,
                                    date=datetime.fromtimestamp(os.path.getctime(filepath)),
                                    conditions={"source": "filesystem_import"}
                                )
                                session.add(db_session)
                                session.commit()
                                session.refresh(db_session)
                            
                            # 4. Create Trial (within Session) linked to C3D file
                            trial = Trial(
                                name=trial_name,
                                description=f"Auto-created from file: {file}",
                                session_id=db_session.id,
                                c3d_file_id=db_file.id,
                                parameters={"source": "filesystem_import"},
                                results={}
                            )
                            session.add(trial)
                            
                            # Apply selected analyses to the C3D file
                            selected_analyses = session.exec(select(Analysis).where(Analysis.file_id == db_file.id)).all()
                            for analysis in selected_analyses:
                                result = analysis.analyze(filepath)
                                analysis_result = Analysis(
                                    file_id=db_file.id,
                                    name=analysis.name,
                                    description=analysis.description,
                                    version=analysis.version,
                                    parameters=analysis.parameters,
                                    result=result["result"],
                                    details=result["details"],
                                    value=result["value"]
                                )
                                session.add(analysis_result)
                            
                            # Commit all changes together
                            session.commit()
                            
                            indexed_files.append(file)
                            files_processed += 1
                            
                        except Exception as e:
                            # Handle unique constraint violations (file already exists)
                            session.rollback()
                            skipped_files.append(file)
                        
                    except Exception as e:
                        # Skip problematic files but continue
                        skipped_files.append(file)
        
        print(f"Indexed {len(indexed_files)} files, skipped {len(skipped_files)} files")
