from sqlmodel import SQLModel, Field as SQLField
from pydantic import BaseModel 
from numpydantic import NDArray, Shape
from typing import Any
from ezc3d import c3d

class Context(BaseModel):
    """
    Event data for a single context (most commonly left or right).
    """
    foot_strike: list[int]
    foot_off: list[int]
    general: list[int]
    other: dict[str, list[int]]  # Other events can be added as needed


class Events(BaseModel):
    """
    All of the event data from a trial.
    """
    units: str
    total_frames: int
    region_of_interest: tuple[int, int]
    left: Context
    right: Context
    general: Context

    def from_c3d(self, c3d_data: c3d) -> None:
        """
        Populate the Events object from a C3D object.
        """
        self.total_frames = c3d_data['header']['nFrames']
        self.region_of_interest = () 
        self.left = Context(**c3d_data['events']['left'])
        self.right = Context(**c3d_data['events']['right'])
        self.general = Context(**c3d_data['events']['general'])

class EMG(BaseModel):
    """
    A single EMG channel and its data from a trial.
    """
    data: NDArray
    frequency: float

    def from_c3d(self, c3d_data: c3d, channel: str) -> None:
        """
        Populate the EMG object from a C3D object for a given channel.
        """
        self.data = c3d_data['data']['analogs'][channel]
        self.frequency = c3d_data['header']['frameRate']


class ForcePlate(BaseModel):
    """
    A single force plate and its data from a trial.
    """
    data: NDArray
    columns: list[str]
    context: str
    frequency: float
    local_r: NDArray[Shape["3, 3"]]
    local_t: NDArray[Shape["3, 1"]]
    world_r: NDArray[Shape["3, 3"]]
    world_t: NDArray[Shape["3, 1"]]
    lower_bounds: float # TODO: Check this type
    upper_bounds: float

    def from_c3d():
        """
        Populate the ForcePlate object from a C3D object.
        """
        # Placeholder for actual loading logic
        pass

class ModelOutput(BaseModel):
    """
    A single model output from a trial.
    """
    group: str
    components: list[str]
    types: list[str]
    data: NDArray

    def __post_init__(self):
        # Check that Components and Types are the same length
        assert len(self.components) == len(self.types), "Components and Types must be the same length."
        # Check that Data has the same number of columns as Components
        assert self.data.shape[1] == len(self.components), "Data must have the same number of columns as Components."

class AnalysisOutput(BaseModel):
    """
    A single analysis output from a trial.
    """
    value: Any
    units: str

class TrialBase(SQLModel):
    """
    Base class for a trial, used for SQLModel.
    """
    name: str 
    classification: str
    subject_name: str
    session_name: str

class Trial(TrialBase, table=True):
    id: int = SQLField(primary_key=True, index=True)

    # Paths to stored data instead of actual arrays
    markers_path: str
    analog_path: str
    model_outputs_path: str
    events_path: str

    # Methods to load data, etc.
    def load_markers(self) -> dict[str, NDArray[Shape["*, 3"]]]:
        """Load marker data from the specified path."""
        # Placeholder for actual loading logic
        pass


class ViconTrial(TrialBase):
    """
    All of the data from a single trial.
    """

    frame_rate: float
    events: Events
    subject_parameters: dict[str, Any]
    markers: dict[str, NDArray[Shape["*, 3"]]] 
    analog: dict[str, ForcePlate | EMG]
    model_outputs: dict[str, ModelOutput]
    analysis_outputs: dict[str, AnalysisOutput]

    def from_c3d(self, c3d_path: str | c3d) -> None:
        """
        Load data from a C3D file and populate the trial attributes.
        """
        if isinstance(c3d_path, str):
            # Load C3D data from file
            import os
            if not os.path.exists(c3d_path):
                raise FileNotFoundError(f"C3D file not found: {c3d_path}")
            from ezc3d import c3d
            c3d_data = c3d(c3d_path)
        else:
            # Assume c3d_path is already a c3d object
            c3d_data = c3d_path
        # Load frame rate
        self.frame_rate = c3d_data['header']['frameRate']
        
        # Load markers
        self.markers = {marker: c3d_data['data']['points'][marker] for marker in c3d_data['data']['points']}
        
        # Load analog data (EMG and Force Plates)
        self.analog = {}
        for channel in c3d_data['data']['analogs']:
            if 'force' in channel.lower():
                self.analog[channel] = ForcePlate(data=c3d_data['data']['analogs'][channel], frequency=self.frame_rate)
            else:
                self.analog[channel] = EMG(data=c3d_data['data']['analogs'][channel], frequency=self.frame_rate)
        
        # Load events
        self.events = Events(
            total_frames=c3d_data['header']['nFrames'],
            region_of_interest=(0, c3d_data['header']['nFrames']),
            left=Context(**c3d_data['events']['left']),
            right=Context(**c3d_data['events']['right']),
            general=Context(**c3d_data['events']['general'])
        )
        
        # Load model outputs and analysis outputs as needed
        # Placeholder for actual loading logic
        self.model_outputs = {}
        self.analysis_outputs = {}


