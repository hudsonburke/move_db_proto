from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from typing import Any
from models.analysis import Analysis
from models.c3d_file import C3DFile  # Add missing import
from app import load_analyses, get_db_session
import ezc3d

router = APIRouter()

@router.post("/files/{file_id}/analyze/{analysis_name}")
def run_analysis(
    file_id: int,
    analysis_name: str,
    parameters: dict[str, Any],
    session: Session = Depends(get_db_session)
):
    """Run a specific analysis on a file"""
    
    # Get available analyses
    analyses = load_analyses()
    if analysis_name not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Get the file
    file = session.get(C3DFile, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Create analysis instance
        analysis_class = analyses[analysis_name]
        analysis = analysis_class(parameters=parameters)
        
        # Load C3D file and run analysis
        c3d = ezc3d.c3d(file.filepath)
        result = analysis.analyze(c3d)
        
        # Store results
        db_result = Analysis(
            file_id=file_id,
            name=analysis.name,
            description=analysis.description,
            version=analysis.version,
            parameters=parameters,
            result=result["result"],
            details=result["details"],
            value=result["value"]
        )
        
        session.add(db_result)
        session.commit()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")

@router.get("/analyses/")
def get_analyses():
    """Get all available analyses with their parameters information"""
    analyses = load_analyses()
    analyses_info = []
    
    for name, analysis_class in analyses.items():
        # Create an instance to get its attributes
        instance = analysis_class()
        analyses_info.append({
            "name": name,
            "display_name": instance.name,
            "description": instance.description,
            "version": instance.version,
            "parameters": {k: str(v) for k, v in instance.parameters.items()}
        })
    
    return {"analyses": analyses_info}
