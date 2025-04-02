"""
Dependency injection utilities for FastAPI.
"""
from sqlmodel import Session
from typing import Generator

# Reference to the engine (set by app.py at startup)
# This avoids circular imports
engine = None

def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    
    Yields:
        Session: A SQLModel database session
    """
    with Session(engine) as session:
        yield session
