"""Model Manager for Advanced Vision Trading Pipeline.

Manages NVFP4 quantized models with VRAM-aware sequential loading/unloading.
Optimized for RTX 5070 Ti 16GB.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class ModelRole(Enum):
    """Model roles in the trading pipeline."""

    SCOUT = "scout"           # Quick analysis, always resident
    REVIEWER = "reviewer"     # Deep analysis, on-demand
    EXPERT = "expert"         # Complex tasks, rarely used


class ModelState(Enum):
    """Model loading states."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"


@dataclass
class ModelConfig:
    """Configuration for a quantized model."""

    name: str
    path: str
    repo_id: str
    role: ModelRole
    parameters: str
    vram_usage_gb: float
    max_batch_size: int = 16
    max_model_len: int = 32768
    gpu_memory_utilization: float = 0.75
    quantization: str = "nvfp4"
    enable_thinking: bool = True
    
    # Computed properties
    @property
    def full_path(self) -> Path:
        """Resolve model path relative to project root."""
        return Path(self.path).expanduser().resolve()
    
    @property
    def is_downloaded(self) -> bool:
        """Check if model weights exist locally."""
        return (self.full_path / "model.safetensors").exists()


@dataclass
class VRAMStats:
    """VRAM usage statistics."""

    total_gb: float = 16.0
    system_reserve_gb: float = 2.0
    used_gb: float = 0.0
    cached_gb: float = 0.0
    
    @property
    def available_gb(self) -> float:
        """VRAM available for models."""
        return self.total_gb - self.system_reserve_gb - self.used_gb
    
    @property
    def utilization(self) -> float:
        """Current VRAM utilization ratio."""
        if self.total_gb <= 0:
            return 0.0
        return (self.used_gb + self.system_reserve_gb) / self.total_gb


class ModelManager:
    """Manages NVFP4 models with VRAM-aware sequential loading.
    
    Features:
    - Sequential model loading based on VRAM constraints
    - Automatic model swapping when VRAM is constrained
    - Dry-run mode for testing without GPU
    - Integration with vLLM for serving
    
    Example:
        >>> manager = ModelManager(dry_run=False)
        >>> manager.load_model("qwen3.5-2b-nvfp4")
        >>> result = manager.inference("qwen3.5-2b-nvfp4", "Analyze this chart")
        >>> manager.unload_model("qwen3.5-2b-nvfp4")
    """

    # Default model configurations
    DEFAULT_MODELS: dict[str, ModelConfig] = {
        "qwen3.5-2b-nvfp4": ModelConfig(
            name="Qwen3.5-2B-NVFP4",
            path="models/Qwen3.5-2B-NVFP4",
            repo_id="AxionML/Qwen3.5-2B-NVFP4",
            role=ModelRole.SCOUT,
            parameters="2B",
            vram_usage_gb=2.5,
            max_batch_size=16,
            max_model_len=32768,
            gpu_memory_utilization=0.70,
            quantization="nvfp4",
            enable_thinking=True,
        ),
        "qwen3.5-4b-nvfp4": ModelConfig(
            name="Qwen3.5-4B-NVFP4",
            path="models/Qwen3.5-4B-NVFP4",
            repo_id="AxionML/Qwen3.5-4B-NVFP4",
            role=ModelRole.REVIEWER,
            parameters="4B",
            vram_usage_gb=4.0,
            max_batch_size=8,
            max_model_len=32768,
            gpu_memory_utilization=0.75,
            quantization="nvfp4",
            enable_thinking=True,
        ),
        "qwen3.5-7b-nvfp4": ModelConfig(
            name="Qwen3.5-7B-NVFP4",
            path="models/Qwen3.5-7B-NVFP4",
            repo_id="AxionML/Qwen3.5-7B-NVFP4",
            role=ModelRole.EXPERT,
            parameters="7B",
            vram_usage_gb=7.0,
            max_batch_size=4,
            max_model_len=16384,
            gpu_memory_utilization=0.80,
            quantization="nvfp4",
            enable_thinking=True,
        ),
    }

    def __init__(
        self,
        project_root: str | Path | None = None,
        dry_run: bool = False,
        simulated_vram_gb: float = 16.0,
        auto_swap: bool = True,
        default_resident: str = "qwen3.5-2b-nvfp4",
    ):
        """Initialize the model manager.
        
        Args:
            project_root: Root directory of the project
            dry_run: If True, simulate GPU operations without actual loading
            simulated_vram_gb: VRAM to simulate in dry-run mode
            auto_swap: Automatically unload models when VRAM is constrained
            default_resident: Model to keep always loaded (scout)
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.dry_run = dry_run
        self.auto_swap = auto_swap
        self.default_resident = default_resident
        
        # VRAM tracking
        self.vram = VRAMStats(total_gb=simulated_vram_gb if dry_run else 16.0)
        
        # Model state tracking
        self._models: dict[str, ModelConfig] = dict(self.DEFAULT_MODELS)
        self._state: dict[str, ModelState] = {
            name: ModelState.UNLOADED for name in self._models
        }
        self._last_used: dict[str, float] = {}
        self._residency_timeout: float = 300  # 5 minutes
        
        # vLLM process tracking
        self._vllm_process: subprocess.Popen | None = None
        self._vllm_port: int = 8000
        
        # Callbacks for state changes
        self._callbacks: list[Callable[[str, ModelState, ModelState], None]] = []
        
        logger.info(f"ModelManager initialized (dry_run={dry_run})")

    # ==========================================================================
    # Model Registry
    # ==========================================================================

    def register_model(self, model_id: str, config: ModelConfig) -> None:
        """Register a new model configuration."""
        self._models[model_id] = config
        self._state[model_id] = ModelState.UNLOADED
        logger.debug(f"Registered model: {model_id}")

    def get_model(self, model_id: str) -> ModelConfig | None:
        """Get model configuration by ID."""
        return self._models.get(model_id)

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered models with their status."""
        return [
            {
                "id": model_id,
                "name": config.name,
                "role": config.role.value,
                "parameters": config.parameters,
                "vram_gb": config.vram_usage_gb,
                "state": self._state[model_id].value,
                "downloaded": config.is_downloaded,
                "last_used": self._last_used.get(model_id),
            }
            for model_id, config in self._models.items()
        ]

    # ==========================================================================
    # VRAM Management
    # ==========================================================================

    def get_vram_stats(self) -> VRAMStats:
        """Get current VRAM statistics."""
        if not self.dry_run:
            # Try to get real VRAM stats from nvidia-smi
            try:
                self.vram = self._query_nvidia_smi()
            except Exception as e:
                logger.warning(f"Failed to query nvidia-smi: {e}")
        return self.vram

    def _query_nvidia_smi(self) -> VRAMStats:
        """Query nvidia-smi for VRAM usage."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
            )
            total_mb, used_mb = map(float, result.stdout.strip().split(","))
            return VRAMStats(
                total_gb=total_mb / 1024,
                used_gb=used_mb / 1024,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return self.vram

    def can_fit_model(self, model_id: str) -> bool:
        """Check if a model can fit in available VRAM."""
        config = self._models.get(model_id)
        if not config:
            return False
        
        vram = self.get_vram_stats()
        return vram.available_gb >= config.vram_usage_gb

    def required_vram_for(self, *model_ids: str) -> float:
        """Calculate total VRAM required for a set of models."""
        total = 0.0
        for model_id in model_ids:
            if config := self._models.get(model_id):
                total += config.vram_usage_gb
        return total

    # ==========================================================================
    # Model Loading / Unloading
    # ==========================================================================

    def load_model(
        self,
        model_id: str,
        force: bool = False,
        timeout: float = 120.0,
    ) -> bool:
        """Load a model into VRAM.
        
        Args:
            model_id: ID of the model to load
            force: Force load even if VRAM is constrained
            timeout: Maximum time to wait for loading
            
        Returns:
            True if model is loaded successfully
        """
        if model_id not in self._models:
            logger.error(f"Unknown model: {model_id}")
            return False
        
        config = self._models[model_id]
        
        # Check if already loaded
        if self._state[model_id] == ModelState.LOADED:
            self._last_used[model_id] = time.time()
            logger.debug(f"Model {model_id} already loaded")
            return True
        
        # Check if downloaded
        if not config.is_downloaded:
            logger.error(f"Model not downloaded: {model_id}")
            return False
        
        # Check VRAM availability
        if not force and not self.can_fit_model(model_id):
            if self.auto_swap:
                logger.info(f"VRAM constrained, unloading other models to make room for {model_id}")
                self._make_room_for(config.vram_usage_gb, keep=model_id)
            else:
                logger.warning(f"Insufficient VRAM for {model_id} (need {config.vram_usage_gb}GB)")
                return False
        
        # Load the model
        old_state = self._state[model_id]
        self._set_state(model_id, ModelState.LOADING)
        
        try:
            if self.dry_run:
                # Simulate loading
                logger.info(f"[DRY-RUN] Loading model: {model_id}")
                time.sleep(0.5)  # Simulate delay
                self.vram.used_gb += config.vram_usage_gb
            else:
                # Real loading via vLLM
                self._load_with_vllm(model_id, config)
            
            self._set_state(model_id, ModelState.LOADED)
            self._last_used[model_id] = time.time()
            logger.info(f"Model loaded: {model_id}")
            return True
            
        except Exception as e:
            self._set_state(model_id, ModelState.ERROR)
            logger.error(f"Failed to load model {model_id}: {e}")
            return False

    def unload_model(self, model_id: str) -> bool:
        """Unload a model from VRAM.
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            True if model is unloaded successfully
        """
        if model_id not in self._models:
            logger.error(f"Unknown model: {model_id}")
            return False
        
        # Check if loaded
        if self._state[model_id] != ModelState.LOADED:
            logger.debug(f"Model {model_id} not loaded")
            return True
        
        config = self._models[model_id]
        old_state = self._state[model_id]
        self._set_state(model_id, ModelState.UNLOADING)
        
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Unloading model: {model_id}")
                self.vram.used_gb = max(0, self.vram.used_gb - config.vram_usage_gb)
            else:
                self._unload_from_vllm(model_id)
            
            self._set_state(model_id, ModelState.UNLOADED)
            self._last_used.pop(model_id, None)
            logger.info(f"Model unloaded: {model_id}")
            return True
            
        except Exception as e:
            self._set_state(model_id, ModelState.ERROR)
            logger.error(f"Failed to unload model {model_id}: {e}")
            return False

    def _make_room_for(self, required_gb: float, keep: str | None = None) -> None:
        """Unload models to make room for required VRAM.
        
        Args:
            required_gb: Amount of VRAM needed in GB
            keep: Model ID to keep loaded (don't unload)
        """
        # Get loaded models sorted by last used (LRU eviction)
        loaded = [
            (model_id, self._last_used.get(model_id, 0))
            for model_id, state in self._state.items()
            if state == ModelState.LOADED and model_id != keep
        ]
        loaded.sort(key=lambda x: x[1])  # Sort by last used time
        
        vram = self.get_vram_stats()
        freed_gb = 0.0
        
        for model_id, _ in loaded:
            if vram.available_gb + freed_gb >= required_gb:
                break
            
            # Don't unload the default resident model unless forced
            if model_id == self.default_resident:
                continue
            
            config = self._models[model_id]
            logger.info(f"Evicting model to make room: {model_id}")
            if self.unload_model(model_id):
                freed_gb += config.vram_usage_gb

    def _set_state(self, model_id: str, new_state: ModelState) -> None:
        """Update model state and notify callbacks."""
        old_state = self._state.get(model_id, ModelState.UNLOADED)
        self._state[model_id] = new_state
        
        for callback in self._callbacks:
            try:
                callback(model_id, old_state, new_state)
            except Exception as e:
                logger.warning(f"State change callback error: {e}")

    # ==========================================================================
    # vLLM Integration
    # ==========================================================================

    def _load_with_vllm(self, model_id: str, config: ModelConfig) -> None:
        """Load model using vLLM."""
        # In a real implementation, this would start vLLM or use the vLLM Python API
        # For now, we assume vLLM is managed externally via scripts/start_vllm.sh
        logger.info(f"vLLM load requested for {model_id}")
        # Placeholder for actual vLLM integration

    def _unload_from_vllm(self, model_id: str) -> None:
        """Unload model from vLLM."""
        logger.info(f"vLLM unload requested for {model_id}")
        # Placeholder for actual vLLM integration

    def start_vllm_server(
        self,
        model_id: str,
        port: int = 8000,
        background: bool = False,
    ) -> subprocess.Popen | None:
        """Start vLLM server for a model.
        
        Args:
            model_id: Model to serve
            port: Port for the server
            background: Run in background
            
        Returns:
            Subprocess handle if background=True, None otherwise
        """
        config = self._models.get(model_id)
        if not config:
            raise ValueError(f"Unknown model: {model_id}")
        
        script_path = self.project_root / "scripts" / "start_vllm.sh"
        cmd = [str(script_path), model_id, "--port", str(port)]
        
        if background:
            cmd.append("--detach")
        
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would start vLLM: {' '.join(cmd)}")
            return None
        
        logger.info(f"Starting vLLM server for {model_id} on port {port}")
        
        if background:
            process = subprocess.Popen(cmd)
            self._vllm_process = process
            self._vllm_port = port
            return process
        else:
            subprocess.run(cmd, check=True)
            return None

    def stop_vllm_server(self) -> None:
        """Stop the running vLLM server."""
        if self._vllm_process:
            self._vllm_process.terminate()
            self._vllm_process.wait(timeout=30)
            self._vllm_process = None
            logger.info("vLLM server stopped")

    # ==========================================================================
    # Inference
    # ==========================================================================

    def inference(
        self,
        model_id: str,
        prompt: str,
        images: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run inference on a loaded model.
        
        Args:
            model_id: Model to use for inference
            prompt: Text prompt
            images: Optional list of image paths for vision tasks
            **kwargs: Additional inference parameters
            
        Returns:
            Inference result
        """
        if self._state.get(model_id) != ModelState.LOADED:
            logger.info(f"Auto-loading model for inference: {model_id}")
            if not self.load_model(model_id):
                raise RuntimeError(f"Failed to load model: {model_id}")
        
        self._last_used[model_id] = time.time()
        
        if self.dry_run:
            return {
                "model": model_id,
                "prompt": prompt,
                "dry_run": True,
                "output": f"[DRY-RUN] Response from {model_id}",
            }
        
        # Real inference via vLLM API
        # This would connect to the vLLM server
        raise NotImplementedError("Inference via vLLM API not yet implemented")

    # ==========================================================================
    # Utility
    # ==========================================================================

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive manager status."""
        vram = self.get_vram_stats()
        
        return {
            "dry_run": self.dry_run,
            "vram": {
                "total_gb": vram.total_gb,
                "available_gb": vram.available_gb,
                "used_gb": vram.used_gb,
                "utilization": f"{vram.utilization:.1%}",
            },
            "models": self.list_models(),
            "vllm_running": self._vllm_process is not None,
            "vllm_port": self._vllm_port if self._vllm_process else None,
        }

    def print_status(self) -> None:
        """Print current status to console."""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("Model Manager Status")
        print("=" * 60)
        print(f"Mode: {'DRY-RUN' if status['dry_run'] else 'LIVE'}")
        print(f"VRAM: {status['vram']['used_gb']:.1f}GB / {status['vram']['total_gb']:.1f}GB "
              f"({status['vram']['utilization']} used)")
        print(f"Available: {status['vram']['available_gb']:.1f}GB")
        print(f"vLLM Server: {'Running' if status['vllm_running'] else 'Stopped'}")
        print("-" * 60)
        print("Models:")
        for m in status["models"]:
            state_icon = {
                "unloaded": "○",
                "loading": "⟳",
                "loaded": "●",
                "unloading": "↻",
                "error": "✗",
            }.get(m["state"], "?")
            dl_icon = "✓" if m["downloaded"] else "✗"
            print(f"  {state_icon} {m['id']:<20} [{m['role']:<8}] "
                  f"VRAM:{m['vram_gb']:>4.1f}GB DL:{dl_icon}")
        print("=" * 60 + "\n")

    def on_state_change(
        self,
        callback: Callable[[str, ModelState, ModelState], None],
    ) -> None:
        """Register a callback for model state changes."""
        self._callbacks.append(callback)

    def cleanup(self) -> None:
        """Unload all models and cleanup resources."""
        logger.info("Cleaning up ModelManager...")
        
        for model_id in list(self._models.keys()):
            if self._state[model_id] == ModelState.LOADED:
                self.unload_model(model_id)
        
        if self._vllm_process:
            self.stop_vllm_server()
        
        logger.info("Cleanup complete")

    def __enter__(self) -> "ModelManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.cleanup()


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI for model management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Model Manager for Advanced Vision Trading Pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operations without GPU",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    subparsers.add_parser("status", help="Show current status")
    
    # List command
    subparsers.add_parser("list", help="List all models")
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Load a model")
    load_parser.add_argument("model", help="Model ID to load")
    
    # Unload command
    unload_parser = subparsers.add_parser("unload", help="Unload a model")
    unload_parser.add_argument("model", help="Model ID to unload")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start vLLM server")
    serve_parser.add_argument("model", help="Model ID to serve")
    serve_parser.add_argument("--port", type=int, default=8000, help="Server port")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ModelManager(
        project_root=args.project_root,
        dry_run=args.dry_run,
    )
    
    if args.command == "status" or args.command is None:
        manager.print_status()
    
    elif args.command == "list":
        for model in manager.list_models():
            print(f"{model['id']}: {model['name']} [{model['state']}]")
    
    elif args.command == "load":
        success = manager.load_model(args.model)
        exit(0 if success else 1)
    
    elif args.command == "unload":
        success = manager.unload_model(args.model)
        exit(0 if success else 1)
    
    elif args.command == "serve":
        manager.start_vllm_server(args.model, port=args.port)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
