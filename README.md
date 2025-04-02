# C3D Database Manager

A web application for managing and searching C3D biomechanics files, built with FastAPI, SQLModel, and ezc3d.

## Features

- Scan directories to index C3D files (without copying them)
- Search files by filename, subject, duration, frame count, and more
- Filter by markers, analog channels, and events
- Download original C3D files from their original locations
- View detailed metadata for each file
- RESTful API for programmatic access

## Architecture Overview

This application is designed with a layered architecture to separate concerns and facilitate extensibility:

1.  **File System:**
    *   Stores the original `.c3d` files and any large derived data files (e.g., motion files from OpenSim).
    *   Organizes these files in a user-defined hierarchy.
    *   The application *references* these files but does not store their raw data directly in the database.
2.  **Database (SQLModel/SQLite):**
    *   Stores metadata extracted from the files (e.g., markers, events, duration, parameters).
    *   Holds information about the file structure and relationships (subjects, sessions, groups).
    *   Enables efficient querying and filtering without needing to load large C3D files.
    *   Can store metadata related to user-generated analyses and links to derived files.
3.  **API (FastAPI):**
    *   Provides a RESTful interface to interact with the system.
    *   Handles scanning the file system to populate the database.
    *   Offers endpoints for querying/managing metadata (files, subjects, groups, etc.).
    *   Serves as the backend for both the Web App and external User Code.
4.  **Web App (HTML/JS/CSS served via StaticFiles):**
    *   Provides a graphical user interface (GUI) for interacting with the API.
    *   Allows users to browse, search, and manage the C3D metadata visually.
5.  **User Code (External Scripts/Applications):**
    *   Separate scripts or applications written by users (e.g., in Python).
    *   Interacts with the **API** to retrieve file paths, metadata, and group information.
    *   Performs custom analyses (e.g., biomechanical calculations using OpenSim, custom plotting).
    *   Can use the **API** to store results (e.g., paths to generated files, calculated metrics) back into the database, associating them with the original data.

This separation allows the core application (API and Web App) to remain focused on data management and presentation, while complex or user-specific computations are handled externally.

## Installation

### Prerequisites

- Python 3.8+
- pip or conda
- ezc3d library

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/c3d-database-manager.git
   cd c3d-database-manager
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install fastapi uvicorn sqlmodel python-multipart ezc3d
   ```

4. Create the necessary directories:
   ```bash
   mkdir static
   ```

5. Copy the frontend files to the static directory:
   - Place `index.html` in the `static` directory
   - Place `script.js` in the `static` directory

## Usage

### Starting the Application

1. Start the FastAPI server:
   ```bash
   uvicorn app:app --reload
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8000/
   ```

### API Endpoints

The application provides the following API endpoints:

- `GET /files/` - Search for C3D files with various filters
- `GET /files/{file_id}` - Get a specific C3D file by ID
- `DELETE /files/{file_id}` - Delete a C3D file reference from the database
- `GET /files/{file_id}/download` - Download the original C3D file from its location
- `POST /search/` - Advanced search with request body
- `POST /directory-scan/` - Scan a directory for C3D files and index their metadata

### Interactive API Documentation

FastAPI automatically generates interactive API documentation. You can access it at:

```
http://localhost:8000/docs
```

## Using the Web Interface

### Scanning Directories

1. Enter the full path to a directory containing C3D files in the "Scan Directory" form.
2. Click "Scan Directory" to start the process.
3. The application will recursively scan the directory, extracting metadata from all C3D files it finds.
4. The original files will remain in place; only their metadata and paths are stored in the database.

### Searching Files

1. Use the search form to filter files by:
   - Filename
   - Subject name
   - Duration range
   - Marker name
   - Channel name
   - Event name
2. Results appear in the right panel.

### File Details

1. Click "View Details" on any file card to see all metadata.
2. The details modal shows:
   - Basic file information
   - Complete lists of markers, channels, and events
   - A download button for the original file

## Data Structure

The application uses SQLModel to manage the following data structure:

- **File** - Main file information (filename, path, size, date, duration, etc.)
- **Marker** - 3D point markers in the C3D file (linked to File)
- **AnalogChannel** - Analog channels in the C3D file (linked to File)
- **Event** - Events defined in the C3D file with timestamps (linked to File)

## File Storage Approach

This application serves as a metadata index for your C3D files:
- Files are **not** copied or moved from their original locations
- The database stores absolute paths to the original files
- When you view or download a file, it's accessed from its original location
- This approach conserves disk space and simplifies file management

## Customization

### Database

By default, the application uses SQLite with the database file named `c3d_database.db`. You can modify the `DATABASE_URL` in `app.py` to use a different database system like PostgreSQL or MySQL.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.