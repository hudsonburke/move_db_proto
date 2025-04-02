from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from models.c3d_file import C3DFile
from models.marker import Marker
from models.channel import AnalogChannel
from models.analysis import Analysis
from app import get_db_session
import ezc3d
import numpy as np
import urllib.parse
import json
import math # Import math for isnan
import os

router = APIRouter()

# Helper function to recursively replace NaN with None
def replace_nan_with_none(obj):
    if isinstance(obj, dict):
        return {k: replace_nan_with_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_with_none(elem) for elem in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

# Helper function to get file by ID or raise 404
def get_file_or_404(file_id: int, session: Session) -> C3DFile:
    file = session.get(C3DFile, file_id)
    if not file:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")
    return file

# Route uses file_id query parameter
@router.get("/plot") 
def get_plot_data(
    file_id: int = Query(...),
    plot_name: str = Query(...),
    parameters: Optional[str] = Query(None), # JSON string for parameters
    session: Session = Depends(get_db_session)
):
    """Get plot data for a specific file ID and plot type."""
    try:
        # Import needed here now
        from plots import available_plots
        
        file = get_file_or_404(file_id, session)
        
        plot_class = next((p for p in available_plots if p.__name__ == plot_name), None)
        if not plot_class:
            raise HTTPException(status_code=404, detail=f"Plot '{plot_name}' not found")
        
        decoded_params = {}
        if parameters:
            try:
                # Query parameters are already decoded by FastAPI
                decoded_params = json.loads(parameters) 
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid parameters JSON string.")

        # Get the C3D data
        try:
            # Check if file is already in the local file system
            if os.path.exists(file.filepath):
                filepath = file.filepath
            else:
                # In real-world applications, implement a cache or temp storage for files
                raise HTTPException(status_code=404, detail=f"File not found at {file.filepath}")
                
            # Load the C3D file with ezc3d
            c3d = ezc3d.c3d(filepath)
            c3d_processed_data = {
                'points': c3d['data']['points'],
                'meta_data': c3d['parameters'],
                'analogs': c3d['data']['analogs'],
                'header': c3d['header']
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading C3D file: {str(e)}")
        
        # Create the plot
        try:
            plot_instance = plot_class()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating plot instance: {str(e)}")
        
        if hasattr(plot_instance, 'set_parameters'):
            plot_instance.set_parameters(decoded_params)
        
        if hasattr(plot_instance, 'plot'):
            plot_output = plot_instance.plot(c3d_processed_data)
            
            if not all(k in plot_output for k in ('traces', 'layout', 'config')):
                return {'traces': [], 'layout': {}, 'config': {}}
            return plot_output
        else:
             raise HTTPException(status_code=500, detail=f"Plot class {plot_name} missing 'plot' method.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating plot: {str(e)}")

# Route uses file_id query parameter
@router.get("/plot/markers")
def get_marker_names(
    file_id: int = Query(...),
    session: Session = Depends(get_db_session)
):
    """Get available marker names for a given file ID."""
    try:
        file = get_file_or_404(file_id, session)
        markers = session.exec(select(Marker).where(Marker.file_id == file.id)).all()
        return {'markers': [marker.marker_name for marker in markers]}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading marker data: {str(e)}")

# Route uses file_id query parameter
@router.get("/plot/channels")
def get_channel_names(
    file_id: int = Query(...),
    session: Session = Depends(get_db_session)
):
    """Get available analog channel names for a given file ID."""
    try:
        file = get_file_or_404(file_id, session)
        channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.id)).all()
        return {'channels': [channel.channel_name for channel in channels]}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading channel data: {str(e)}")

@router.get("/plots")
def get_available_plots():
    """Get list of available plot classes."""
    from plots import available_plots
    
    plots_info = []
    seen_plot_names = set() # Keep track of plot names we've added
    
    for plot_class in available_plots:
        # Check if we've already added this plot class name
        if plot_class.__name__ not in seen_plot_names:
            try: # Add try-except around instantiation
                instance = plot_class() # Create instance to access attributes
                plots_info.append({
                    'name': plot_class.__name__, # Class name for backend reference
                    'display_name': instance.name,
                    'description': instance.description,
                    'requires_markers': instance.requires_markers,
                    'requires_channels': instance.requires_channels
                    # Add parameter info if needed later
                })
                seen_plot_names.add(plot_class.__name__) # Mark this name as added
            except Exception as e:
                print(f"Warning: Could not instantiate or get info for plot class {plot_class.__name__}: {e}")
        else:
            print(f"DEBUG: Skipping duplicate plot class entry: {plot_class.__name__}") # Optional debug logging
            
    return {'plots': plots_info} 