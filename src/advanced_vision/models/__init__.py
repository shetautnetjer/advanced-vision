"""Models module for Advanced Vision Trading Pipeline.

Provides VRAM-aware model management for NVFP4 quantized models.
"""

from .model_manager import (
    ModelConfig,
    ModelManager,
    ModelRole,
    ModelState,
    VRAMStats,
)

__all__ = [
    "ModelConfig",
    "ModelManager",
    "ModelRole",
    "ModelState",
    "VRAMStats",
]
