from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from models.c3d_file import C3DFile
from models.marker import Marker
from models.channel import AnalogChannel
from models.analysis import Analysis
from app import get_db_session
import ezc3d
import numpy as np
from plots import available_plots

router = APIRouter()

def get_c3d_data(file: C3DFile) -> Dict[str, Any]:
    """Read data directly from C3D file."""
    c3d = ezc3d.c3d(file.filepath)
    
    # Get time points
    time_points = np.arange(c3d['header']['points']['last_frame']) / c3d['header']['points']['frame_rate']
    
    # Get marker data
    marker_data = {}
    for marker_name in c3d['parameters']['POINT']['LABELS']['value']:
        marker_idx = c3d['parameters']['POINT']['LABELS']['value'].index(marker_name)
        marker_data[marker_name] = {
            'x': c3d['data']['points'][0, marker_idx, :],
            'y': c3d['data']['points'][1, marker_idx, :],
            'z': c3d['data']['points'][2, marker_idx, :]
        }
    
    # Get analog data
    channel_data = {}
    for channel_name in c3d['parameters']['ANALOG']['LABELS']['value']:
        channel_idx = c3d['parameters']['ANALOG']['LABELS']['value'].index(channel_name)
        channel_data[channel_name] = c3d['data']['analogs'][channel_idx, :]
    
    return {
        'time_points': time_points.tolist(),
        'marker_data': marker_data,
        'channel_data': channel_data,
        'frame_rate': c3d['header']['points']['frame_rate'],
        'analog_rate': c3d['header']['analogs']['frame_rate']
    }

@router.get("/plot/{filepath:path}")
def get_plot_data(
    filepath: str,
    plot_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    session: Session = Depends(get_db_session)
):
    """Get plot data from a C3D file using a specified plot class."""
    try:
        # Get file from database
        file = session.get(C3DFile, filepath)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Find the requested plot class
        plot_class = next((p for p in available_plots if p.__name__ == plot_name), None)
        if not plot_class:
            raise HTTPException(status_code=404, detail=f"Plot '{plot_name}' not found")
        
        # Check if we have the required analysis in the database
        analysis = session.exec(
            select(Analysis)
            .where(Analysis.file_id == filepath)
            .where(Analysis.name == plot_name)
        ).first()
        
        if analysis and analysis.data:
            # Use data from database
            c3d_data = analysis.data
        else:
            # Read directly from C3D file
            c3d_data = get_c3d_data(file)
        
        # Create and configure plot
        plot = plot_class()
        if parameters:
            plot.set_parameters(parameters)
        
        # Generate plot data
        return plot.plot(c3d_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating plot: {str(e)}")

@router.get("/plot/{filepath:path}/markers")
def get_marker_names(
    filepath: str,
    session: Session = Depends(get_db_session)
):
    """Get available marker names from a C3D file."""
    try:
        file = session.get(C3DFile, filepath)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # First try to get markers from database
        markers = session.exec(select(Marker).where(Marker.file_id == filepath)).all()
        if markers:
            return {
                'markers': [marker.marker_name for marker in markers]
            }
        
        # If no markers in database, read from C3D file
        c3d = ezc3d.c3d(file.filepath)
        return {
            'markers': c3d['parameters']['POINT']['LABELS']['value']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading marker data: {str(e)}")

@router.get("/plot/{filepath:path}/channels")
def get_channel_names(
    filepath: str,
    session: Session = Depends(get_db_session)
):
    """Get available analog channel names from a C3D file."""
    try:
        file = session.get(C3DFile, filepath)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # First try to get channels from database
        channels = session.exec(select(AnalogChannel).where(AnalogChannel.file_id == filepath)).all()
        if channels:
            return {
                'channels': [channel.channel_name for channel in channels]
            }
        
        # If no channels in database, read from C3D file
        c3d = ezc3d.c3d(file.filepath)
        return {
            'channels': c3d['parameters']['ANALOG']['LABELS']['value']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading channel data: {str(e)}")

@router.get("/plots")
def get_available_plots():
    """Get list of available plot classes."""
    return {
        'plots': [
            {
                'name': plot.__name__,
                'display_name': plot().name,
                'description': plot().description
            }
            for plot in available_plots
        ]
    } 