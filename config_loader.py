import json
import os
from typing import Dict, Any
from pydantic import BaseModel, Field

class ConfidenceThresholds(BaseModel):
    high: int = Field(default=90, ge=0, le=100)
    medium: int = Field(default=70, ge=0, le=100)
    low: int = Field(default=0, ge=0, le=100)

class ProcessingConfig(BaseModel):
    batch_size: int = Field(default=100, ge=1)
    max_retries: int = Field(default=3, ge=0)
    cache_duration_days: int = Field(default=7, ge=1)

class ReportingConfig(BaseModel):
    sample_size_percent: int = Field(default=10, ge=1, le=100)
    report_format: str = "markdown"

class Config(BaseModel):
    version: str = "1.0.0"
    base_directory: str
    rubric_path: str
    confidence_thresholds: ConfidenceThresholds = ConfidenceThresholds()
    processing: ProcessingConfig = ProcessingConfig()
    reporting: ReportingConfig = ReportingConfig()

class ConfigLoader:
    def __init__(self):
        self.config = None

    def load_config(self) -> Config:
        if self.config is not None:
            return self.config

        # Load from environment or default config file
        config_path = os.getenv("GDRIVE_CLASSIFIER_CONFIG", "config.json")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        else:
            # Use default configuration
            config_data = {
                "version": "1.0.0",
                "base_directory": os.getcwd(),
                "rubric_path": os.getenv("GDRIVE_CLASSIFIER_RUBRIC", "rubric.json"),
                "confidence_thresholds": {
                    "high": 90,
                    "medium": 70,
                    "low": 0
                },
                "processing": {
                    "batch_size": 100,
                    "max_retries": 3,
                    "cache_duration_days": 7
                },
                "reporting": {
                    "sample_size_percent": 10,
                    "report_format": "markdown"
                }
            }

        self.config = Config(**config_data)
        return self.config