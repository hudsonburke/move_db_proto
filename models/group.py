"""
Group models for organizing C3D files into collections.
"""
from typing import List, Optional, TYPE_CHECKING, Callable, Type
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

# Import from base models
from .base import TrialGroupBase, GroupFileLink

# Use TYPE_CHECKING to avoid runtime imports
if TYPE_CHECKING:
    from .c3d_file import C3DFile

class TrialGroup(TrialGroupBase, table=True):
    """Model for groups of C3D trials."""
    id: int | None = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.now)
    date_modified: datetime = Field(default_factory=datetime.now)
    
    # Use string references to avoid circular imports
    c3d_files: list["C3DFile"] = Relationship(
        back_populates="groups", 
        link_model=GroupFileLink
    )
    
    @classmethod
    def get_c3d_file_class(cls) -> Type["C3DFile"]:
        """Get the C3DFile class dynamically to avoid import issues.
        
        This factory method allows for better dependency management.
        """
        from .c3d_file import C3DFile
        return C3DFile

class TrialGroupCreate(TrialGroupBase):
    """Model for creating a new trial group."""
    file_ids: list[int] = []

class TrialGroupUpdate(SQLModel):
    """Model for updating a trial group."""
    name: str | None = None
    description: str | None = None
    
class TrialGroupRead(TrialGroupBase):
    """Pydantic model for reading group data."""
    id: int
    date_created: datetime
    date_modified: datetime
    file_count: int

# Keep the legacy Group class below
from datetime import datetime
import json

class Group:
    """Represents a group of C3D files that have been collected together."""

    def __init__(self, id=None, name=None, description=None, date_created=None, date_modified=None):
        self.id = id
        self.name = name
        self.description = description
        self.date_created = date_created or datetime.now().isoformat()
        self.date_modified = date_modified or datetime.now().isoformat()
        self.file_count = 0  # Will be populated when needed

    @staticmethod
    def create_table(conn):
        """Create the group table in the database if it doesn't exist."""
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            date_created TEXT NOT NULL,
            date_modified TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_files (
            group_id INTEGER,
            file_id INTEGER,
            date_added TEXT NOT NULL,
            PRIMARY KEY (group_id, file_id),
            FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
        )
        ''')
        conn.commit()

    @staticmethod
    def from_row(row):
        """Create a Group object from a database row."""
        if not row:
            return None
        return Group(
            id=row[0],
            name=row[1],
            description=row[2],
            date_created=row[3],
            date_modified=row[4]
        )

    def to_dict(self):
        """Convert the Group object to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'date_created': self.date_created,
            'date_modified': self.date_modified,
            'file_count': self.file_count
        }

    @staticmethod
    def create(conn, name, description=None):
        """Create a new group in the database."""
        now = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO groups (name, description, date_created, date_modified) VALUES (?, ?, ?, ?)',
            (name, description, now, now)
        )
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def update(conn, group_id, name=None, description=None):
        """Update an existing group in the database."""
        cursor = conn.cursor()
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
            
        if description is not None:
            updates.append('description = ?')
            params.append(description)
            
        if updates:
            updates.append('date_modified = ?')
            params.append(datetime.now().isoformat())
            params.append(group_id)
            
            cursor.execute(
                f'UPDATE groups SET {", ".join(updates)} WHERE id = ?',
                params
            )
            conn.commit()
            return True
        return False

    @staticmethod
    def delete(conn, group_id):
        """Delete a group from the database."""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def get(conn, group_id):
        """Get a group by ID."""
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, date_created, date_modified FROM groups WHERE id = ?', (group_id,))
        row = cursor.fetchone()
        group = Group.from_row(row)
        
        if group:
            # Get file count for this group
            cursor.execute('SELECT COUNT(*) FROM group_files WHERE group_id = ?', (group_id,))
            group.file_count = cursor.fetchone()[0]
            
        return group

    @staticmethod
    def get_all(conn):
        """Get all groups."""
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, date_created, date_modified FROM groups ORDER BY name')
        groups = [Group.from_row(row) for row in cursor.fetchall()]
        
        # Get file counts for all groups
        for group in groups:
            cursor.execute('SELECT COUNT(*) FROM group_files WHERE group_id = ?', (group.id,))
            group.file_count = cursor.fetchone()[0]
            
        return groups

    @staticmethod
    def add_files(conn, group_id, file_ids):
        """Add files to a group."""
        if not file_ids:
            return 0
            
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        added = 0
        
        # Check if the group exists
        cursor.execute('SELECT id FROM groups WHERE id = ?', (group_id,))
        if not cursor.fetchone():
            return 0
            
        # Add each file, ignoring duplicates
        for file_id in file_ids:
            try:
                cursor.execute(
                    'INSERT OR IGNORE INTO group_files (group_id, file_id, date_added) VALUES (?, ?, ?)',
                    (group_id, file_id, now)
                )
                if cursor.rowcount > 0:
                    added += 1
            except Exception as e:
                print(f"Error adding file {file_id} to group {group_id}: {e}")
                
        # Update the group's modification date
        if added > 0:
            cursor.execute(
                'UPDATE groups SET date_modified = ? WHERE id = ?',
                (now, group_id)
            )
            
        conn.commit()
        return added

    @staticmethod
    def remove_file(conn, group_id, file_id):
        """Remove a file from a group."""
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM group_files WHERE group_id = ? AND file_id = ?',
            (group_id, file_id)
        )
        
        if cursor.rowcount > 0:
            # Update the group's modification date
            now = datetime.now().isoformat()
            cursor.execute(
                'UPDATE groups SET date_modified = ? WHERE id = ?',
                (now, group_id)
            )
            conn.commit()
            return True
            
        return False

    @staticmethod
    def get_group_files(conn, group_id):
        """Get all files in a group."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.id, f.filename, f.filepath, f.classification, f.subject_name, 
                   f.session_name, f.frame_count, f.duration, f.sample_rate, 
                   f.date_added, f.file_size
            FROM files f
            JOIN group_files gf ON f.id = gf.file_id
            WHERE gf.group_id = ?
            ORDER BY f.filename
        ''', (group_id,))
        
        files = []
        for row in cursor.fetchall():
            file_dict = {
                'id': row[0],
                'filename': row[1],
                'filepath': row[2],
                'classification': row[3],
                'subject_name': row[4],
                'session_name': row[5],
                'frame_count': row[6],
                'duration': row[7],
                'sample_rate': row[8],
                'date_added': row[9],
                'file_size': row[10]
            }
            files.append(file_dict)
            
        return files