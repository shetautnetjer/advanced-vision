"""Configuration helpers for advanced_vision."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    repo_root: Path = Field(default=Path(__file__).resolve().parents[2])
    artifacts_dir: Path = Field(default=Path("artifacts"))
    screens_dir_name: str = Field(default="screens")
    logs_dir_name: str = Field(default="logs")

    @property
    def screens_dir(self) -> Path:
        return self.artifacts_dir_path / self.screens_dir_name

    @property
    def logs_dir(self) -> Path:
        return self.artifacts_dir_path / self.logs_dir_name

    @property
    def artifacts_dir_path(self) -> Path:
        if self.artifacts_dir.is_absolute():
            return self.artifacts_dir
        return self.repo_root / self.artifacts_dir


def get_settings() -> Settings:
    settings = Settings()
    settings.screens_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    return settings
