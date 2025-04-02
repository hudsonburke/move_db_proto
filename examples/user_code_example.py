"""
Example of user code interacting with the C3D Database API.

This demonstrates how external scripts can:
1. Query the API to find trials based on metadata
2. Download and process C3D files with OpenSim 
3. Store processing results back in the database

Requirements:
- requests
- pandas
- opensim (not used directly in this example, but would be in real code)
"""
import requests
import json
import pandas as pd
import os
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api"  # Adjust to your server URL

# Example: Function to get all trials for a specific subject with no results yet
def get_unprocessed_trials(subject_id, session_id=None):
    """Get trials that haven't been processed yet for a given subject."""
    params = {
        "subject_id": subject_id,
        "has_results": False  # Only get trials without results
    }
    
    # If session_id is provided, add it to the filters
    if session_id:
        params["session_id"] = session_id
    
    # Get all sessions for this subject first
    sessions_resp = requests.get(f"{API_URL}/sessions/", params={"subject_id": subject_id})
    if not sessions_resp.ok:
        print(f"Error getting sessions: {sessions_resp.text}")
        return []
    
    sessions = sessions_resp.json()
    
    # Get trials for each session
    trials = []
    for session in sessions:
        trials_resp = requests.get(
            f"{API_URL}/trials/", 
            params={"session_id": session["id"], "has_results": False}
        )
        if trials_resp.ok:
            session_trials = trials_resp.json()
            # Add session name to each trial for reference
            for trial in session_trials:
                trial["session_name"] = session["name"]
            trials.extend(session_trials)
    
    return trials

# Example: Process a trial with OpenSim
def process_trial_with_opensim(trial):
    """
    Process a trial with OpenSim and store results.
    
    This is a placeholder that simulates OpenSim processing. In a real
    application, you would:
    1. Download the C3D file
    2. Run OpenSim tools on it
    3. Store the results back in the database
    """
    print(f"Processing trial: {trial['name']} (ID: {trial['id']})")
    
    # Step 1: Get the C3D file path
    if not trial.get("c3d_file_id"):
        print(f"Trial has no associated C3D file")
        return False
    
    c3d_resp = requests.get(f"{API_URL}/files/{trial['c3d_file_id']}")
    if not c3d_resp.ok:
        print(f"Error getting C3D file: {c3d_resp.text}")
        return False
    
    c3d_file = c3d_resp.json()
    c3d_path = c3d_file["filepath"]
    
    print(f"C3D file path: {c3d_path}")
    
    # Step 2: Simulate OpenSim processing (in real code, you'd use the opensim package)
    # Example: Extract joint angles from the C3D file using OpenSim
    
    # Placeholder for OpenSim processing result
    opensim_results = {
        "processed": True,
        "output_files": {
            "ik_results": f"/path/to/results/{trial['id']}_ik.mot",
            "id_results": f"/path/to/results/{trial['id']}_id.sto"
        },
        "joint_angles": {
            "knee_flexion_r": {
                "max": 60.5,
                "min": 5.2,
                "avg": 30.1,
                "values": [10.5, 20.7, 30.8, 40.2, 50.5, 60.5, 50.3, 40.8, 30.2, 20.1, 10.5, 5.2]
            },
            "hip_flexion_r": {
                "max": 40.2,
                "min": 10.1,
                "avg": 25.3,
                "values": [20.5, 30.7, 40.2, 35.8, 30.5, 25.3, 20.1, 15.5, 10.1, 15.2, 20.5, 25.7]
            }
        },
        "processed_date": "2023-04-02T12:34:56"
    }
    
    # Step 3: Store results back in the database
    update_resp = requests.patch(
        f"{API_URL}/trials/{trial['id']}/results",
        json=opensim_results
    )
    
    if update_resp.ok:
        print(f"Successfully stored results for trial {trial['id']}")
        return True
    else:
        print(f"Error storing results: {update_resp.text}")
        return False

# Example usage
def main():
    # Get all subjects
    resp = requests.get(f"{API_URL}/subjects/")
    if not resp.ok:
        print(f"Error connecting to API: {resp.text}")
        return
    
    subjects = resp.json()
    print(f"Found {len(subjects)} subjects")
    
    # Process one subject as an example
    if subjects:
        subject_id = subjects[0]["id"]
        print(f"Processing trials for subject {subjects[0]['name']} (ID: {subject_id})")
        
        # Get unprocessed trials for this subject
        trials = get_unprocessed_trials(subject_id)
        print(f"Found {len(trials)} unprocessed trials")
        
        # Process each trial
        for trial in trials:
            success = process_trial_with_opensim(trial)
            if success:
                print(f"Processed trial {trial['name']}")
            else:
                print(f"Failed to process trial {trial['name']}")

if __name__ == "__main__":
    main() 