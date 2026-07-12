import unittest
import os
import shutil
import time
from backend.config_loader import AppConfig, CameraConfig, ServerConfig, SentinelConfig
from backend.camera_manager import CameraProcessManager

class TestCameraProcessManager(unittest.TestCase):
    def setUp(self):
        # Create a mock config
        self.config = AppConfig(
            server=ServerConfig(host="127.0.0.1", port=8001, recordings_dir="./test_recordings"),
            clip_length=2,
            cameras=[
                CameraConfig(
                    id="test-cam",
                    name="Test Cam",
                    source="dummy",
                    sentinel=SentinelConfig(enabled=False)
                )
            ]
        )
        self.manager = CameraProcessManager(self.config)

    def tearDown(self):
        # Clean up any active processes
        self.manager.stop_all()
        # Delete test recordings dir
        test_dir = os.path.abspath("./test_recordings")
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_start_and_stop_camera(self):
        # Test status before starting
        status = self.manager.get_status("test-cam")
        self.assertEqual(status, "inactive")

        # Start camera process
        self.manager.start_camera(self.config.cameras[0])
        status = self.manager.get_status("test-cam")
        self.assertEqual(status, "active")

        # Stop camera process
        self.manager.stop_camera("test-cam")
        status = self.manager.get_status("test-cam")
        self.assertEqual(status, "inactive")

    def test_clip_generation(self):
        # Start camera recording and wait a few seconds to verify video clip files are generated
        self.manager.start_camera(self.config.cameras[0])
        time.sleep(3.5) # Wait long enough to allow segmenting (clip_length=2)

        cam_dir = os.path.join(os.path.abspath("./test_recordings"), "test-cam")
        self.assertTrue(os.path.exists(cam_dir))

        # Verify if any mp4 clips have been created
        files = [f for f in os.listdir(cam_dir) if f.endswith(".mp4")]
        self.assertGreaterEqual(len(files), 1, "Should have created at least one video segment")

        # Stop process
        self.manager.stop_camera("test-cam")

if __name__ == "__main__":
    unittest.main()
