import os
import subprocess
import logging
import signal
import time
from typing import Dict, List, Optional
from backend.config_loader import AppConfig, CameraConfig

logger = logging.getLogger("camera_manager")
logging.basicConfig(level=logging.INFO)

class CameraProcessManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.processes: Dict[str, subprocess.Popen] = {}
        self.recordings_dir = os.path.abspath(config.server.recordings_dir)
        os.makedirs(self.recordings_dir, exist_ok=True)

    def start_camera(self, camera: CameraConfig):
        cam_id = camera.id
        if cam_id in self.processes and self.processes[cam_id].poll() is None:
            logger.info(f"Camera process for '{cam_id}' is already running.")
            return

        cam_dir = os.path.join(self.recordings_dir, cam_id)
        os.makedirs(cam_dir, exist_ok=True)

        segment_time = self.config.clip_length

        # We'll generate segments: recordings/<cam_id>/clip_%Y%m%d_%H%M%S.mp4
        output_pattern = os.path.join(cam_dir, "clip_%Y%m%d_%H%M%S.mp4")

        # ffmpeg commands for static segment splitting
        if camera.source == "dummy":
            # For testing in sandbox, generate a dummy stream of synthetic testsrc video & sine audio
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi", "-i", "testsrc=size=640x480:rate=15",
                "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=8000",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-f", "segment",
                "-segment_time", str(segment_time),
                "-reset_timestamps", "1",
                "-strftime", "1",
                output_pattern
            ]
        else:
            # Standard RTSP camera command
            # Using tcp transport for reliability, and copy codecs to avoid heavy CPU transcoding
            cmd = [
                "ffmpeg",
                "-y",
                "-rtsp_transport", "tcp",
                "-i", camera.source,
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "segment",
                "-segment_time", str(segment_time),
                "-reset_timestamps", "1",
                "-strftime", "1",
                output_pattern
            ]

        logger.info(f"Starting ffmpeg for camera '{cam_id}' with command: {' '.join(cmd)}")
        try:
            # Run in a new process group so we can manage/terminate nicely
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            self.processes[cam_id] = p
            logger.info(f"Started ffmpeg process (PID {p.pid}) for camera '{cam_id}'")
        except Exception as e:
            logger.error(f"Failed to start camera process for '{cam_id}': {e}")

    def start_all(self):
        logger.info("Starting all camera subscriptions...")
        for camera in self.config.cameras:
            self.start_camera(camera)

    def stop_camera(self, cam_id: str):
        if cam_id not in self.processes:
            return

        p = self.processes[cam_id]
        if p.poll() is None:
            logger.info(f"Stopping ffmpeg process (PID {p.pid}) for camera '{cam_id}'")
            try:
                # Terminate process group to stop ffmpeg gracefully and avoid orphans
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                # Give it a tiny bit to stop
                for _ in range(10):
                    if p.poll() is not None:
                        break
                    time.sleep(0.1)
                if p.poll() is None:
                    logger.warning(f"Process {p.pid} did not exit on SIGTERM. Sending SIGKILL.")
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.error(f"Error stopping process for camera '{cam_id}': {e}")

        # Ensure we tidy up
        p.wait()
        del self.processes[cam_id]

    def stop_all(self):
        logger.info("Stopping all camera processes...")
        # Materialize keys list as we delete on the fly
        for cam_id in list(self.processes.keys()):
            self.stop_camera(cam_id)

    def get_status(self, cam_id: str) -> str:
        if cam_id not in self.processes:
            return "inactive"
        p = self.processes[cam_id]
        if p.poll() is None:
            return "active"
        return "failed"
