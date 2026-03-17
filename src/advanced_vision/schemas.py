"""Pydantic schemas for the advanced_vision capability layer."""

from __future__ import annotations

from pydantic import BaseModel


class ScreenshotArtifact(BaseModel):
    path: str
    width: int
    height: int
    timestamp: str


class WindowInfo(BaseModel):
    title: str
    app_name: str | None = None
    is_active: bool | None = None


class ActionProposal(BaseModel):
    action_type: str
    x: int | None = None
    y: int | None = None
    text: str | None = None
    keys: list[str] | None = None
    confidence: float | None = None
    rationale: str | None = None


class ActionResult(BaseModel):
    ok: bool
    action_type: str
    message: str
    artifact_path: str | None = None


class VerificationResult(BaseModel):
    changed: bool
    similarity: float | None = None
    message: str


class VideoArtifact(BaseModel):
    """Schema for screen recording video"""
    path: str
    duration: int
    fps: int
    width: int
    height: int
    file_size: int
    timestamp: str


class VideoAnalysisResult(BaseModel):
    """Schema for Kimi video analysis response"""
    video_path: str
    question: str
    answer: str
    model: str
    frames_used: int
    timestamp: str
