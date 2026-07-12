# mycameras

A personal webcam subscription and video recording gallery app.

## Project Structure

- `config.yaml`: YAML configuration defining camera subscriptions, clip segment length, and future sentinel placeholders.
- `recordings/`: Directory containing subdirectories for each camera subscription where N-second MP4 clips are recorded.
- `backend/`: Python (FastAPI + PyYAML) server that manages background ffmpeg processes and serves the API and video gallery.
- `frontend/`: React + TypeScript (Vite) single-page application. Serves as the modern dashboard/gallery interface.

## Getting Started

1. Set up and start the application from the root directory.
