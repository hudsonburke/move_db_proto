from typing import Any
from models.analysis import AnalysisBase
import numpy as np
import ezc3d

class MarkerGapsAnalysis(AnalysisBase):
    name: str = "Marker Gaps Analysis"
    description: str = "Checks for gaps in marker data between events"
    parameters: dict[str, Any] = {
        "marker_name": str,
        "start_event": str,
        "end_event": str,
        "max_gap_size": int
    }

    def analyze(self, c3d: ezc3d.c3d) -> dict[str, Any]:
        points = c3d['data']['points']
        events = c3d['parameters']['EVENT']
        
        # Find event frames
        start_frame = next(i for i, e in enumerate(events['LABELS']['value']) 
                         if e == self.parameters['start_event'])
        end_frame = next(i for i, e in enumerate(events['LABELS']['value']) 
                        if e == self.parameters['end_event'])
        
        # Get marker data
        marker_data = points[self.parameters['marker_name']][start_frame:end_frame]
        gaps = np.where(np.isnan(marker_data))[0]
        
        # Find continuous gaps
        gap_sizes = []
        if len(gaps) > 0:
            gap_start = gaps[0]
            current_size = 1
            for i in range(1, len(gaps)):
                if gaps[i] == gaps[i-1] + 1:
                    current_size += 1
                else:
                    gap_sizes.append(current_size)
                    gap_start = gaps[i]
                    current_size = 1
            gap_sizes.append(current_size)
        
        max_gap = max(gap_sizes) if gap_sizes else 0
        
        return {
            "result": max_gap <= self.parameters["max_gap_size"],
            "details": {
                "gaps_found": len(gaps),
                "max_gap_size": max_gap,
                "gap_locations": gaps.tolist()
            },
            "value": max_gap
        }