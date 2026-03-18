#!/usr/bin/env python3
"""
Model Loading Orchestrator

Manages sequential loading of vision models with VRAM budget constraints.
Usage with RTX 5070 Ti 16GB (14GB budget)
"""

import json
import torch
import gc
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for a model."""
    id: str
    name: str
    vram_tensorrt_gb: float
    residency: str  # "resident" | "on_demand"
    priority: int
    checkpoint_path: Path
    tensorrt_path: Optional[Path] = None
    loader: Optional[Callable] = None

class VRAMManager:
    """Manages VRAM budget and model loading order."""
    
    def __init__(self, total_vram_gb: float = 16.0, budget_gb: float = 14.0):
        self.total_vram_gb = total_vram_gb
        self.budget_gb = budget_gb
        self.loaded_models: Dict[str, torch.nn.Module] = {}
        self.model_order: List[str] = []
        
    def get_available_vram_gb(self) -> float:
        """Get available VRAM in GB."""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1e9
            return self.budget_gb - allocated
        return self.budget_gb
        
    def get_used_vram_gb(self) -> float:
        """Get used VRAM in GB."""
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / 1e9
        return 0.0
        
    def can_load(self, vram_required_gb: float) -> bool:
        """Check if model can fit in remaining VRAM."""
        return self.get_available_vram_gb() >= vram_required_gb
        
    def print_status(self):
        """Print current VRAM status."""
        used = self.get_used_vram_gb()
        available = self.get_available_vram_gb()
        
        print(f"\n{'='*50}")
        print(f"VRAM Status: {used:.1f}/{self.budget_gb:.1f} GB used")
        print(f"Available: {available:.1f} GB")
        print(f"Loaded Models ({len(self.loaded_models)}):")
        for model_id in self.loaded_models:
            print(f"  • {model_id}")
        print(f"{'='*50}\n")

class ModelOrchestrator:
    """
    Orchestrates model loading for the trading pipeline.
    Implements sequential loading strategy for minimal VRAM pressure.
    """
    
    # Standard loading order (small to large)
    LOAD_ORDER = ["yolov8n", "stock-pattern-yolo", "qwen2.5-vl-2b", "eagle2-2b"]
    
    # On-demand models (loaded when needed)
    ON_DEMAND = ["sam2-tiny", "yolov8s", "mobilesam", "sam3"]
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.project_root = Path(__file__).parent.parent
        self.registry_path = registry_path or self.project_root / "config" / "model_registry.json"
        self.vram = VRAMManager()
        self.registry = self._load_registry()
        self.loaded_models: Dict[str, any] = {}
        
    def _load_registry(self) -> Dict:
        """Load model registry from JSON."""
        with open(self.registry_path) as f:
            return json.load(f)
            
    def get_model_config(self, model_id: str) -> ModelConfig:
        """Get configuration for a model."""
        model_data = self.registry["models"][model_id]
        models_dir = self.project_root / "models"
        
        return ModelConfig(
            id=model_id,
            name=model_data["name"],
            vram_tensorrt_gb=model_data["vram"]["tensorrt_gb"],
            residency=model_data["residency"],
            priority=model_data["priority"],
            checkpoint_path=models_dir / model_data["files"]["checkpoint"],
            tensorrt_path=models_dir / model_data["files"].get("tensorrt", "") 
                if model_data["files"].get("tensorrt") else None
        )
        
    def load_model(self, model_id: str, force: bool = False) -> Optional[any]:
        """
        Load a single model with VRAM check.
        
        Args:
            model_id: Model identifier from registry
            force: Load even if over budget (use with caution)
        """
        if model_id in self.loaded_models:
            logger.info(f"Model {model_id} already loaded")
            return self.loaded_models[model_id]
            
        config = self.get_model_config(model_id)
        
        # VRAM check
        if not force and not self.vram.can_load(config.vram_tensorrt_gb):
            available = self.vram.get_available_vram_gb()
            logger.warning(
                f"Cannot load {model_id}: needs {config.vram_tensorrt_gb:.1f}GB, "
                f"only {available:.1f}GB available"
            )
            return None
            
        logger.info(f"Loading {model_id} ({config.name})...")
        
        # Load based on model type
        model = self._load_by_type(model_id, config)
        
        if model:
            self.loaded_models[model_id] = model
            logger.info(f"✓ {model_id} loaded successfully")
            self.vram.print_status()
            
        return model
        
    def _load_by_type(self, model_id: str, config: ModelConfig) -> Optional[any]:
        """Load model based on its type."""
        model_data = self.registry["models"][model_id]
        model_type = model_data.get("type")
        
        try:
            if model_type == "detection":
                return self._load_yolo(config)
            elif model_id == "eagle2-2b":
                return self._load_eagle2(config)
            elif model_id == "qwen2.5-vl-2b":
                return self._load_qwen(config)
            elif model_type == "segmentation":
                return self._load_sam(config)
            else:
                logger.warning(f"Unknown model type for {model_id}")
                return None
        except Exception as e:
            logger.error(f"Failed to load {model_id}: {e}")
            return None
            
    def _load_yolo(self, config: ModelConfig):
        """Load YOLO model."""
        from ultralytics import YOLO
        
        # Prefer TensorRT engine if available
        if config.tensorrt_path and config.tensorrt_path.exists():
            return YOLO(str(config.tensorrt_path))
        elif config.checkpoint_path.exists():
            return YOLO(str(config.checkpoint_path))
        else:
            logger.warning(f"YOLO model not found at {config.checkpoint_path}")
            return None
            
    def _load_eagle2(self, config: ModelConfig):
        """Load Eagle2-2B model."""
        from transformers import AutoModelForVision2Seq, AutoProcessor
        
        if not config.checkpoint_path.exists():
            logger.warning(f"Eagle2 not found at {config.checkpoint_path}")
            return None
            
        model = AutoModelForVision2Seq.from_pretrained(
            str(config.checkpoint_path),
            torch_dtype=torch.float16,
            device_map="cuda:0"
        )
        processor = AutoProcessor.from_pretrained(str(config.checkpoint_path))
        
        return {"model": model, "processor": processor}
        
    def _load_qwen(self, config: ModelConfig):
        """Load Qwen2.5-VL model."""
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        
        if not config.checkpoint_path.exists():
            logger.warning(f"Qwen not found at {config.checkpoint_path}")
            return None
            
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            str(config.checkpoint_path),
            torch_dtype=torch.float16,
            device_map="cuda:0"
        )
        processor = AutoProcessor.from_pretrained(str(config.checkpoint_path))
        
        return {"model": model, "processor": processor}
        
    def _load_sam(self, config: ModelConfig):
        """Load SAM segmentation model."""
        # SAM loading depends on specific implementation
        logger.info(f"SAM model {config.id} would be loaded here")
        return None
        
    def unload_model(self, model_id: str):
        """Unload a model and free VRAM."""
        if model_id not in self.loaded_models:
            return
            
        logger.info(f"Unloading {model_id}...")
        del self.loaded_models[model_id]
        
        # Force garbage collection
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        
        logger.info(f"✓ {model_id} unloaded")
        self.vram.print_status()
        
    def load_strategy(self, strategy_name: str):
        """
        Load a predefined strategy from registry.
        
        Strategies: standard_trading, fast_scout, deep_analysis, minimal
        """
        strategy = self.registry["loading_strategies"].get(strategy_name)
        if not strategy:
            logger.error(f"Unknown strategy: {strategy_name}")
            return
            
        logger.info(f"Loading strategy: {strategy['name']}")
        logger.info(f"Description: {strategy['description']}")
        
        for model_id in strategy["load_order"]:
            self.load_model(model_id)
            
        logger.info(f"✓ Strategy '{strategy_name}' loaded")
        
    @contextmanager
    def on_demand(self, model_id: str, swap_out: List[str] = None):
        """
        Context manager for on-demand model loading.
        
        Usage:
            with orchestrator.on_demand("sam3", swap_out=["stock-pattern-yolo"]) as model:
                result = model.segment(image)
        """
        swap_out = swap_out or []
        swapped = []
        
        try:
            # Swap out models if needed
            for swap_id in swap_out:
                if swap_id in self.loaded_models:
                    self.unload_model(swap_id)
                    swapped.append(swap_id)
                    
            # Load on-demand model
            model = self.load_model(model_id, force=True)
            yield model
            
        finally:
            # Always unload on-demand model
            if model_id in self.loaded_models:
                self.unload_model(model_id)
                
            # Restore swapped models
            for swap_id in swapped:
                self.load_model(swap_id)
                
    def verify_all(self) -> Dict[str, bool]:
        """Verify all models are available."""
        results = {}
        
        for model_id, model_data in self.registry["models"].items():
            checkpoint = self.project_root / "models" / model_data["files"]["checkpoint"]
            exists = checkpoint.exists()
            results[model_id] = exists
            
            status = "✓" if exists else "✗"
            print(f"{status} {model_id}: {model_data['name']}")
            
        return results


def main():
    """CLI for model orchestration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model loading orchestrator")
    parser.add_argument("action", choices=["load", "unload", "strategy", "verify", "status"])
    parser.add_argument("--model", help="Model ID for load/unload")
    parser.add_argument("--strategy", help="Strategy name for strategy action")
    
    args = parser.parse_args()
    
    orchestrator = ModelOrchestrator()
    
    if args.action == "load" and args.model:
        orchestrator.load_model(args.model)
    elif args.action == "unload" and args.model:
        orchestrator.unload_model(args.model)
    elif args.action == "strategy" and args.strategy:
        orchestrator.load_strategy(args.strategy)
    elif args.action == "verify":
        orchestrator.verify_all()
    elif args.action == "status":
        orchestrator.vram.print_status()


if __name__ == "__main__":
    main()
