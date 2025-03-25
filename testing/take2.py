from pathlib import Path
import numpy as np
import ezc3d
from typing import Any
from pydantic import BaseModel, Field, field_validator


class Point3D(BaseModel):
    """Represents a 3D point with x, y, z coordinates."""
    x: float
    y: float
    z: float
    
    @classmethod
    def from_array(cls, array: np.ndarray):
        """Create a Point3D from a numpy array."""
        return cls(x=float(array[0]), y=float(array[1]), z=float(array[2]))


class Marker(BaseModel):
    """Represents a marker with position and optional metadata."""
    name: str
    position: list[Point3D] = Field(default_factory=list)
    residual: list[float] | None = None
    
    @field_validator('position')
    @classmethod
    def validate_positions(cls, v):
        """Ensure we have position data."""
        if not v:
            raise ValueError("Marker must have at least one position")
        return v


class Analog(BaseModel):
    """Represents an analog channel with values and metadata."""
    name: str
    values: list[float] = Field(default_factory=list)
    unit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    
    @field_validator('values')
    @classmethod
    def validate_values(cls, v):
        """Ensure we have analog data."""
        if not v:
            raise ValueError("Analog channel must have at least one value")
        return v


class Event(BaseModel):
    """Represents an event with timestamp and label."""
    label: str
    time: float
    context: str | None = None
    subject: str | None = None
    description: str | None = None


class Metadata(BaseModel):
    """Metadata about the C3D file."""
    points_per_frame: int
    analog_per_frame: int
    first_frame: int
    last_frame: int
    analog_sampling_rate: float
    point_sampling_rate: float
    units: dict[str, str] = Field(default_factory=dict)
    subjects: list[str] = Field(default_factory=list)


class C3DData(BaseModel):
    """Main container for C3D data."""
    file_path: Path
    metadata: Metadata
    markers: dict[str, Marker] = Field(default_factory=dict)
    analogs: dict[str, Analog] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class C3DParser:
    """Parser for C3D files using ezc3d and Pydantic models."""
    
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.c3d = ezc3d.c3d(str(self.file_path))
        
    def parse(self) -> C3DData:
        """Parse the C3D file and return structured data."""
        # Extract metadata
        metadata = self._extract_metadata()
        
        # Extract markers
        markers = self._extract_markers()
        
        # Extract analog channels
        analogs = self._extract_analogs()
        
        # Extract events
        events = self._extract_events()
        
        # Extract parameters
        parameters = self._extract_parameters()
        
        # Create and return the C3DData object
        return C3DData(
            file_path=self.file_path,
            metadata=metadata,
            markers=markers,
            analogs=analogs,
            events=events,
            parameters=parameters
        )
    
    def _extract_metadata(self) -> Metadata:
        """Extract metadata from the C3D file."""
        header = self.c3d.header()
        parameters = self.c3d.parameters()
        
        # Get basic metadata
        points_per_frame = header['nb3dPoints']
        first_frame = header['firstFrame']
        last_frame = header['lastFrame']
        point_sampling_rate = header['frameRate']
        
        # Get analog related metadata
        analog_per_frame = header['nbAnalogs']
        analog_sampling_rate = header['frameRate'] * header['nbAnalogByFrame']
        
        # Get units
        units = {}
        if 'POINT' in parameters and 'UNITS' in parameters['POINT']:
            units['position'] = parameters['POINT']['UNITS']['value'][0]
        
        if 'ANALOG' in parameters and 'UNITS' in parameters['ANALOG']:
            for i, unit in enumerate(parameters['ANALOG']['UNITS']['value']):
                units[f'analog_{i}'] = unit
        
        # Get subjects if available
        subjects = []
        if 'SUBJECTS' in parameters and 'NAMES' in parameters['SUBJECTS']:
            subjects = parameters['SUBJECTS']['NAMES']['value']
        
        return Metadata(
            points_per_frame=points_per_frame,
            analog_per_frame=analog_per_frame,
            first_frame=first_frame,
            last_frame=last_frame,
            analog_sampling_rate=analog_sampling_rate,
            point_sampling_rate=point_sampling_rate,
            units=units,
            subjects=subjects
        )
    
    def _extract_markers(self) -> dict[str, Marker]:
        """Extract markers from the C3D file."""
        markers = {}
        points_data = self.c3d.point_data()
        point_labels = self.c3d.parameters()['POINT']['LABELS']['value']
        
        for i, label in enumerate(point_labels):
            # Extract position data for this marker
            positions = []
            residuals = []
            
            for frame in range(points_data.shape[2]):
                # Check if this point is valid (not NaN)
                if not np.isnan(points_data[0, i, frame]):
                    position = Point3D.from_array(points_data[0:3, i, frame])
                    positions.append(position)
                    
                    # Some C3D files include residuals
                    if points_data.shape[0] > 3:
                        residuals.append(float(points_data[3, i, frame]))
            
            # Create marker if we have valid data
            if positions:
                marker = Marker(
                    name=label,
                    position=positions,
                    residual=residuals if residuals else None
                )
                markers[label] = marker
        
        return markers
    
    def _extract_analogs(self) -> dict[str, Analog]:
        """Extract analog channels from the C3D file."""
        analogs = {}
        analog_data = self.c3d.analog_data()
        
        # Try to get analog labels
        parameters = self.c3d.parameters()
        if 'ANALOG' in parameters and 'LABELS' in parameters['ANALOG']:
            analog_labels = parameters['ANALOG']['LABELS']['value']
        else:
            # If no labels, create default ones
            analog_labels = [f'Analog_{i}' for i in range(analog_data.shape[0])]
        
        # Try to get scaling factors
        scales = np.ones(len(analog_labels))
        if 'ANALOG' in parameters and 'SCALE' in parameters['ANALOG']:
            scales = parameters['ANALOG']['SCALE']['value']
        
        # Try to get offsets
        offsets = np.zeros(len(analog_labels))
        if 'ANALOG' in parameters and 'OFFSET' in parameters['ANALOG']:
            offsets = parameters['ANALOG']['OFFSET']['value']
        
        # Try to get units
        units = [None] * len(analog_labels)
        if 'ANALOG' in parameters and 'UNITS' in parameters['ANALOG']:
            units = parameters['ANALOG']['UNITS']['value']
        
        for i, label in enumerate(analog_labels):
            # Extract values for this channel
            values = analog_data[i, :].tolist()
            
            # Create analog channel
            analog = Analog(
                name=label,
                values=values,
                unit=units[i] if i < len(units) else None,
                scale=float(scales[i]) if i < len(scales) else 1.0,
                offset=float(offsets[i]) if i < len(offsets) else 0.0
            )
            analogs[label] = analog
        
        return analogs
    
    def _extract_events(self) -> list[Event]:
        """Extract events from the C3D file."""
        events = []
        parameters = self.c3d.parameters()
        
        # Check if we have events
        if 'EVENT' in parameters and 'TIMES' in parameters['EVENT']:
            event_times = parameters['EVENT']['TIMES']['value']
            event_labels = parameters['EVENT']['LABELS']['value'] if 'LABELS' in parameters['EVENT'] else []
            
            for i, time in enumerate(event_times[1]):  # Usually event_times[0] is contexts, event_times[1] is times
                # Create event
                event = Event(
                    label=event_labels[i] if i < len(event_labels) else f"Event_{i}",
                    time=float(time),
                    context=event_times[0][i] if i < len(event_times[0]) else None
                )
                events.append(event)
        
        return events
    
    def _extract_parameters(self) -> dict[str, Any]:
        """Extract all parameters from the C3D file."""
        parameters = self.c3d.parameters()
        # Convert to dict - this is a simplified version as the actual structure is complex
        result = {}
        
        for group_name, group in parameters.items():
            result[group_name] = {}
            for param_name, param in group.items():
                if 'value' in param:
                    # Handle numpy arrays
                    if isinstance(param['value'], np.ndarray):
                        result[group_name][param_name] = param['value'].tolist()
                    else:
                        result[group_name][param_name] = param['value']
        
        return result


# Example usage
def main():
    # Replace with your actual C3D file path
    file_path = "example.c3d"
    
    try:
        parser = C3DParser(file_path)
        data = parser.parse()
        
        # Print some basic information
        print(f"File: {data.file_path}")
        print(f"Frames: {data.metadata.first_frame} to {data.metadata.last_frame}")
        print(f"Point sampling rate: {data.metadata.point_sampling_rate} Hz")
        print(f"Analog sampling rate: {data.metadata.analog_sampling_rate} Hz")
        print(f"Number of markers: {len(data.markers)}")
        print(f"Number of analog channels: {len(data.analogs)}")
        print(f"Number of events: {len(data.events)}")
        
        # Example of accessing a marker
        if data.markers:
            marker_name = next(iter(data.markers))
            marker = data.markers[marker_name]
            print(f"\nSample marker: {marker_name}")
            print(f"  First position: {marker.position[0] if marker.position else 'N/A'}")
        
        # Example of accessing an analog channel
        if data.analogs:
            analog_name = next(iter(data.analogs))
            analog = data.analogs[analog_name]
            print(f"\nSample analog channel: {analog_name}")
            print(f"  Unit: {analog.unit}")
            print(f"  Scale: {analog.scale}")
            print(f"  First few values: {analog.values[:5] if analog.values else 'N/A'}")
        
    except Exception as e:
        print(f"Error processing file: {e}")


if __name__ == "__main__":
    main()