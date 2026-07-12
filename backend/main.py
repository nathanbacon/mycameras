import os
import signal
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from backend.config_loader import load_config, CameraConfig
from backend.camera_manager import CameraProcessManager

config = load_config()
manager = CameraProcessManager(config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start recording all cameras automatically
    manager.start_all()
    yield
    # Shutdown: Stop all background ffmpeg processes
    manager.stop_all()

app = FastAPI(title="mycameras API", lifespan=lifespan)

# Allow CORS for easy frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for the API response
class CameraStatus(BaseModel):
    id: str
    name: str
    source: str
    status: str
    sentinel: Dict[str, Any]

class ClipInfo(BaseModel):
    filename: str
    filepath: str
    created_at: float
    size_bytes: int

# API Endpoints
@app.get("/api/config")
def get_app_config():
    """Return current loaded global configurations."""
    return {
        "clip_length": config.clip_length,
        "recordings_dir": config.server.recordings_dir
    }

@app.get("/api/cameras", response_model=List[CameraStatus])
def get_cameras():
    """Get all configured cameras and their current recording status."""
    results = []
    for cam in config.cameras:
        status = manager.get_status(cam.id)
        sentinel_info = cam.sentinel.model_dump() if cam.sentinel else {"enabled": False}
        results.append(CameraStatus(
            id=cam.id,
            name=cam.name,
            source=cam.source,
            status=status,
            sentinel=sentinel_info
        ))
    return results

@app.get("/api/cameras/{cam_id}/clips", response_model=List[ClipInfo])
def get_camera_clips(cam_id: str):
    """Get list of recorded video clip files for a specific camera subscription, sorted newest to oldest."""
    # Verify camera exists
    camera = next((c for c in config.cameras if c.id == cam_id), None)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera subscription not found")

    cam_dir = os.path.join(manager.recordings_dir, cam_id)
    if not os.path.exists(cam_dir):
        return []

    clips = []
    for f in os.listdir(cam_dir):
        if f.endswith(".mp4"):
            fpath = os.path.join(cam_dir, f)
            stat = os.stat(fpath)
            # Make sure we don't return files currently being written (e.g., if size is 0 and it was created very recently)
            # But let's return all mp4s since the user might want to see them as soon as they are fully completed.
            clips.append(ClipInfo(
                filename=f,
                filepath=fpath,
                created_at=stat.st_mtime,
                size_bytes=stat.st_size
            ))

    # Sort descending by creation time (newest clips first)
    clips.sort(key=lambda x: x.created_at, reverse=True)
    return clips

@app.get("/api/clips/{cam_id}/{filename}")
def get_clip_file(cam_id: str, filename: str):
    """Serve/Stream the selected MP4 video clip."""
    # Ensure camera exists
    camera = next((c for c in config.cameras if c.id == cam_id), None)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera subscription not found")

    # Prevent directory traversal attacks by basic path sanitization
    filename = os.path.basename(filename)
    if not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    fpath = os.path.join(manager.recordings_dir, cam_id, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(fpath, media_type="video/mp4")

@app.delete("/api/clips/{cam_id}/{filename}")
def delete_clip_file(cam_id: str, filename: str):
    """Delete a recorded video clip manually from the server."""
    # Ensure camera exists
    camera = next((c for c in config.cameras if c.id == cam_id), None)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera subscription not found")

    filename = os.path.basename(filename)
    fpath = os.path.join(manager.recordings_dir, cam_id, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Clip not found")

    try:
        os.remove(fpath)
        return {"status": "success", "message": f"Successfully deleted clip '{filename}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete clip: {str(e)}")

# Placeholder hooks for future Sentinel (Computer Vision) processes
@app.get("/api/sentinel/status")
def get_sentinel_status():
    """Placeholder endpoint checking the status of future sentinel background processes."""
    return {
        "status": "not_implemented",
        "description": "The sentinel process (computer vision for motion/people detection) is a future capability.",
        "supported_features": ["motion_detection", "person_presence_detection"],
        "configuration_placeholders_loaded": [
            {"camera_id": cam.id, "sentinel": cam.sentinel.model_dump() if cam.sentinel else None}
            for cam in config.cameras
        ]
    }

# Serving the static frontend bundle (when built) on the root endpoint.
# We mount this after the API routes so they don't get intercepted.
frontend_dir = os.path.abspath("frontend/dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def index():
        return {
            "message": "Welcome to mycameras API! Frontend build folder not found. Please build frontend first or use Vite development server."
        }
