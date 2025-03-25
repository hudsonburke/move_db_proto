"""
Package for user-defined C3D file analyses.

Add your custom analysis classes here by creating new Python modules.
Each analysis class should inherit from models.analysis.AnalysisBase.
"""

# Import all analyses for easy discovery
from .marker_gaps import MarkerGapsAnalysis

# List of available analysis classes for registration
available_analyses = [
    # MarkerGapsAnalysis  # Commented out to prevent app hang
]