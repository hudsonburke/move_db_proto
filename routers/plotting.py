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
    print(f"DEBUG: get_plot_data received file_id={file_id}, plot_name={plot_name}, parameters={parameters!r}")
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

        # --- Read C3D data directly --- 
        try:
            c3d = ezc3d.c3d(file.filepath)
            # Process time points - handle potential NaN?
            raw_time = np.arange(c3d['header']['points']['last_frame']) / c3d['header']['points']['frame_rate']
            time_points = replace_nan_with_none(raw_time.tolist())
            
            marker_data = {}
            for marker_name in c3d['parameters']['POINT']['LABELS']['value']:
                marker_idx = c3d['parameters']['POINT']['LABELS']['value'].index(marker_name)
                # Process and sanitize marker coordinates
                marker_data[marker_name] = {
                    'x': replace_nan_with_none(c3d['data']['points'][0, marker_idx, :].tolist()),
                    'y': replace_nan_with_none(c3d['data']['points'][1, marker_idx, :].tolist()),
                    'z': replace_nan_with_none(c3d['data']['points'][2, marker_idx, :].tolist())
                }
                
            channel_data = {}
            analog_labels = c3d['parameters'].get('ANALOG', {}).get('LABELS', {}).get('value', [])
            if len(analog_labels) > 0 and c3d['data']['analogs'].shape[1] > 0: # Check if analog data exists
                 for channel_name in analog_labels:
                    try:
                        channel_idx = analog_labels.index(channel_name)
                        # Ensure index is within bounds and process/sanitize channel data
                        if channel_idx < c3d['data']['analogs'].shape[1]: 
                             raw_channel_data = c3d['data']['analogs'][0, channel_idx, :]
                             channel_data[channel_name] = replace_nan_with_none(raw_channel_data.tolist())
                        else:
                             print(f"Warning: Channel index {channel_idx} out of bounds for channel {channel_name} in file {file.filepath}")
                             channel_data[channel_name] = [] # Assign empty list if index is bad
                    except ValueError: # Handle case where channel_name might not be in labels (shouldn't happen with this loop structure but good practice)
                         print(f"Warning: Channel name {channel_name} not found in labels for file {file.filepath}")
                         channel_data[channel_name] = []
            
            c3d_processed_data = {
                'time_points': time_points,
                'marker_data': marker_data, # Already sanitized
                'channel_data': channel_data, # Already sanitized
                'frame_rate': c3d['header']['points']['frame_rate'],
                'analog_rate': c3d['header']['analogs']['frame_rate']
            }
        except Exception as read_err:
             print(f"ERROR reading or processing C3D file {file.filepath}: {read_err}")
             raise HTTPException(status_code=500, detail=f"Error reading/processing C3D file: {read_err}")
        # --- End C3D Read/Process --- 

        plot_instance = plot_class()
        if hasattr(plot_instance, 'set_parameters'):
            plot_instance.set_parameters(decoded_params)
        
        if hasattr(plot_instance, 'plot'):
            plot_output = plot_instance.plot(c3d_processed_data)
            
            # --- REMOVE TEMPORARY DEBUG BLOCK --- 
            # if plot_name == "MarkerTrajectoryPlot":
            #     print(f"DEBUG: Overriding {plot_name} output with dummy data")
            #     dummy_plot_output = { ... } 
            #     if all(k in dummy_plot_output for k in ('traces', 'layout', 'config')):
            #         plot_output = dummy_plot_output
            #     else:
            #         print("Warning: Dummy plot data structure is invalid!")
            # --- END REMOVE TEMPORARY DEBUG ---
            
            if not all(k in plot_output for k in ('traces', 'layout', 'config')):
                 print(f"Warning: Plot {plot_name} output missing keys.")
                 return {'traces': [], 'layout': {}, 'config': {}}
            return plot_output
        else:
             raise HTTPException(status_code=500, detail=f"Plot class {plot_name} missing 'plot' method.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"ERROR in get_plot_data for file_id {file_id}, plot {plot_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating plot: {str(e)}")

# Route uses file_id query parameter
@router.get("/plot/markers")
def get_marker_names(
    file_id: int = Query(...),
    session: Session = Depends(get_db_session)
):
    """Get available marker names for a given file ID."""
    print(f"DEBUG: get_marker_names received file_id: {file_id}") 
    try:
        file = get_file_or_404(file_id, session)
        markers = session.exec(select(Marker).where(Marker.file_id == file.id)).all()
        return {'markers': [marker.marker_name for marker in markers]}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"ERROR in get_marker_names for file_id {file_id}: {e}") 
        raise HTTPException(status_code=500, detail=f"Error reading marker data: {str(e)}")

# Route uses file_id query parameter
@router.get("/plot/channels")
def get_channel_names(
    file_id: int = Query(...),
    session: Session = Depends(get_db_session)
):
    """Get available analog channel names for a given file ID."""
    print(f"DEBUG: get_channel_names received file_id: {file_id}") 
    try:
        file = get_file_or_404(file_id, session)
        channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == file.id)).all()
        return {'channels': [channel.channel_name for channel in channels]}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"ERROR in get_channel_names for file_id {file_id}: {e}")
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