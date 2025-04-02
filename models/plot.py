from abc import ABC, abstractmethod
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any

class BasePlot(ABC):
    """Base class for all plotting implementations."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters: Dict[str, Any] = {}
    
    @abstractmethod
    def plot(self, c3d_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate plot data from C3D file data.
        
        Args:
            c3d_data: Dictionary containing the C3D file data with keys:
                - time_points: List of time points
                - marker_data: Dictionary of marker data
                - channel_data: Dictionary of channel data
                - frame_rate: Frame rate of the data
                - analog_rate: Analog data rate
        
        Returns:
            Dictionary containing:
                - traces: List of plot traces
                - layout: Plot layout configuration
                - config: Plot configuration options
        """
        pass
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set plot parameters."""
        self.parameters = parameters

class MarkerTrajectoryPlot(BasePlot):
    """Example plot showing marker trajectories."""
    
    def __init__(self):
        super().__init__(
            name="Marker Trajectories",
            description="Plot marker positions over time"
        )
    
    def plot(self, c3d_data: Dict[str, Any]) -> Dict[str, Any]:
        traces = []
        
        # Get selected markers from parameters
        selected_markers = self.parameters.get('markers', [])
        
        for marker_name in selected_markers:
            if marker_name in c3d_data['marker_data']:
                data = c3d_data['marker_data'][marker_name]
                for axis, label in [('x', 'X'), ('y', 'Y'), ('z', 'Z')]:
                    traces.append(
                        go.Scatter(
                            name=f"{marker_name} {label}",
                            x=c3d_data['time_points'],
                            y=data[axis],
                            mode='lines'
                        )
                    )
        
        layout = {
            'title': 'Marker Trajectories',
            'xaxis': {'title': 'Time (s)'},
            'yaxis': {'title': 'Position (mm)'},
            'showlegend': True,
            'height': 600
        }
        
        return {
            'traces': traces,
            'layout': layout,
            'config': {'responsive': True}
        }

class AnalogChannelPlot(BasePlot):
    """Example plot showing analog channel data."""
    
    def __init__(self):
        super().__init__(
            name="Analog Channels",
            description="Plot analog channel data over time"
        )
    
    def plot(self, c3d_data: Dict[str, Any]) -> Dict[str, Any]:
        traces = []
        
        # Get selected channels from parameters
        selected_channels = self.parameters.get('channels', [])
        
        for channel_name in selected_channels:
            if channel_name in c3d_data['channel_data']:
                traces.append(
                    go.Scatter(
                        name=channel_name,
                        x=c3d_data['time_points'],
                        y=c3d_data['channel_data'][channel_name],
                        mode='lines'
                    )
                )
        
        layout = {
            'title': 'Analog Channel Data',
            'xaxis': {'title': 'Time (s)'},
            'yaxis': {'title': 'Value'},
            'showlegend': True,
            'height': 600
        }
        
        return {
            'traces': traces,
            'layout': layout,
            'config': {'responsive': True}
        } 