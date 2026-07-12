import yaml
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SentinelConfig(BaseModel):
    enabled: bool = False
    type: str = "motion_only"
    confidence_threshold: float = 0.5

class CameraConfig(BaseModel):
    id: str
    name: str
    source: str
    sentinel: Optional[SentinelConfig] = Field(default_factory=SentinelConfig)

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    recordings_dir: str = "./recordings"

class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    clip_length: int = 10
    cameras: List[CameraConfig] = Field(default_factory=list)

def load_config(config_path: str = "config.yaml") -> AppConfig:
    if not os.path.exists(config_path):
        # Return default config if file doesn't exist
        return AppConfig()

    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}

    return AppConfig(**data)
