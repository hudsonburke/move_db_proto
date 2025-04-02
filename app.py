from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, create_engine, SQLModel
from contextlib import asynccontextmanager
import dependencies

# --- Database Setup ---
DATABASE_URL = "sqlite:///c3d_database.db"
engine = create_engine(DATABASE_URL)

# Set the engine in dependencies module to avoid circular imports
dependencies.engine = engine

# Note: Keeping this legacy function for backward compatibility with routers
def get_db_session():
    with Session(engine) as session:
        yield session

# --- Helper Functions ---
def load_analyses():
    """Load only the analysis classes from the available_analyses list in the analyses package"""
    analyses = {}
    
    # Import the available_analyses list
    from analyses import available_analyses
    
    # Only load the analyses in the available_analyses list
    for analysis_class in available_analyses:
        analyses[analysis_class.__name__] = analysis_class
    
    return analyses

# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    SQLModel.metadata.create_all(engine)
    yield

# --- FastAPI App ---
app = FastAPI(
    title="C3D Database API",
    description="API for managing and searching C3D motion capture files",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from routers import directory_scan, files, search, classifications, subjects, sessions, analyses, groups, files_list, plotting, trials

# Important: Include files_list router before files router to ensure it gets matched first
app.include_router(directory_scan.router, prefix="/api")
app.include_router(files_list.router, prefix="/api")  # Add this before files router
app.include_router(files.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(classifications.router, prefix="/api")
app.include_router(subjects.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(trials.router, prefix="/api")  # Add the trials router
app.include_router(analyses.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(plotting.router, prefix="/api")

# Mount static files for the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# For development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)