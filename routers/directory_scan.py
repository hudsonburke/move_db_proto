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
                            print(f"Skipping large file {filepath} ({file_size / (1024*1024):.2f} MB)")
                            skipped_files.append(file)
                            continue
                        
                        # Set a timeout for processing this file
                        file_start = time.time()
                        
                        # Extract data and create entries
                        extractor = C3DDataExtractor()
                        c3d_data = extractor.analyze(filepath)
                        # print(f"Analyzed {file}: {c3d_data}")
                        
                        # Check if file processing took too long
                        if time.time() - file_start > file_timeout:
                            print(f"Processing {file} took too long, skipping")
                            skipped_files.append(file)
                            continue
                        
                        # Parse directory structure for classification/subject/session
                        rel_path = os.path.relpath(root, root_directory)
                        path_parts = rel_path.split(os.path.sep)
                        
                        classification = ""
                        session_name = ""
                        subject_name = c3d_data["subject_name"] or ""
                        
                        # If path follows expected structure: Classification/Subject/Session/*.c3d
                        if len(path_parts) >= 3:
                            classification = path_parts[0]
                            if not subject_name:  # Only override if not already set from C3D metadata
                                subject_name = path_parts[1]
                            session_name = path_parts[2]
                        elif len(path_parts) == 2:
                            classification = path_parts[0]
                            if not subject_name:
                                subject_name = path_parts[1]
                        elif len(path_parts) == 1 and path_parts[0] != '.':
                            classification = path_parts[0]
                        
                        # Create database entry with id as primary key and filepath as unique identifier
                        db_file = C3DFile(
                            filename=file,
                            filepath=filepath,  # unique identifier
                            file_size=file_size,
                            date_created=datetime.now(),
                            date_modified=datetime.now(),
                            duration=c3d_data["duration"],
                            frame_count=c3d_data["frame_count"],
                            sample_rate=c3d_data["sample_rate"],
                            subject_name=subject_name,
                            classification=classification,
                            session_name=session_name,
                            description=c3d_data["metadata"],
                            has_marker_data=bool(c3d_data["markers"]),
                            has_analog_data=bool(c3d_data["channels"]),
                            has_event_data=bool(c3d_data["events"])
                        )
                        
                        try:
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
                            session.commit()
                            
                            indexed_files.append(file)
                            files_processed += 1
                        except Exception as e:
                            # Handle unique constraint violations (file already exists)
                            session.rollback()
                            print(f"File already exists or error occurred: {str(e)}")
                            skipped_files.append(file)
                        
                    except Exception as e:
                        # Skip problematic files but continue
                        print(f"Error indexing {file}: {str(e)}")
                        skipped_files.append(file)
        
        print(f"Indexed {len(indexed_files)} files, skipped {len(skipped_files)} files")
