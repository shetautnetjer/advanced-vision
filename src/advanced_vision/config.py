"""Configuration helpers for advanced_vision."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    artifacts_dir: Path = Field(default=Path("artifacts"))
    screens_dir_name: str = Field(default="screens")
    logs_dir_name: str = Field(default="logs")

    @property
    def screens_dir(self) -> Path:
        return self.artifacts_dir / self.screens_dir_name

    @property
    def logs_dir(self) -> Path:
        return self.artifacts_dir / self.logs_dir_name


def get_settings() -> Settings:
    settings = Settings()
    settings.screens_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    return settings
