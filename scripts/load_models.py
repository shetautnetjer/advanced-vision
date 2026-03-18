#!/usr/bin/env python3
"""
Model Loading Orchestrator

Manages sequential loading of vision models with VRAM budget constraints.
Usage with RTX 5070 Ti 16GB (14GB budget)
Updated for NVFP4 quantized models.
"""

import json
import gc
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from contextlib import contextmanager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a model."""
    id: str
    name: str
    vram_gb: float
    residency: str  # "resident" | "on_demand"
    priority: int
    checkpoint_path: Path
    tensorrt_path: Optional[Path] = None
    loader: Optional[Callable] = None
    quantization: str = "fp16"


class VRAMManager:
    """Manages VRAM budget and model loading order."""
    
    def __init__(self, total_vram_gb: float = 16.0, budget_gb: float = 14.0):
        self.total_vram_gb = total_vram_gb
        self.budget_gb = budget_gb
        self.loaded_models: Dict[str, Any] = {}
        self.model_order: List[str] = []
        
    def get_available_vram_gb(self) -> float:
        """Get available VRAM in GB."""
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1e9
                return self.budget_gb - allocated
        except ImportError:
            pass
        return self.budget_gb
        
    def get_used_vram_gb(self) -> float:
        """Get used VRAM in GB."""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / 1e9
        except ImportError:
            pass
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
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.project_root = Path(__file__).parent.parent
        self.registry_path = registry_path or self.project_root / "config" / "model_registry.json"
        self.vram = VRAMManager()
        self.registry = self._load_registry()
        self.loaded_models: Dict[str, Any] = {}
        
    def _load_registry(self) -> Dict:
        """Load model registry from JSON."""
        try:
            with open(self.registry_path) as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Registry file not found: {self.registry_path}")
            return {"models": {}, "loading_strategies": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in registry: {e}")
            return {"models": {}, "loading_strategies": {}}
            
    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get configuration for a model."""
        if model_id not in self.registry.get("models", {}):
            logger.error(f"Model {model_id} not found in registry")
            return None
            
        model_data = self.registry["models"][model_id]
        models_dir = self.project_root / "models"
        
        # Get VRAM usage (prefer nvfp4, then tensorrt, then fp16)
        vram_data = model_data.get("vram", {})
        vram_gb = (
            vram_data.get("nvfp4_gb") or
            vram_data.get("tensorrt_gb") or
            vram_data.get("fp16_gb", 2.0)
        )
        
        checkpoint_rel = model_data.get("files", {}).get("checkpoint", f"models/{model_id}")
        checkpoint_path = self.project_root / checkpoint_rel
        
        tensorrt_rel = model_data.get("files", {}).get("tensorrt")
        tensorrt_path = self.project_root / tensorrt_rel if tensorrt_rel else None
        
        return ModelConfig(
            id=model_id,
            name=model_data.get("name", model_id),
            vram_gb=vram_gb,
            residency=model_data.get("residency", "on_demand"),
            priority=model_data.get("priority", 99),
            checkpoint_path=checkpoint_path,
            tensorrt_path=tensorrt_path,
            quantization=model_data.get("quantization", "fp16"),
        )
        
    def is_model_available(self, model_id: str) -> bool:
        """Check if model files exist on disk."""
        config = self.get_model_config(model_id)
        if not config:
            return False
        
        if config.checkpoint_path.is_dir():
            # For directory models, check for model files
            return (
                (config.checkpoint_path / "model.safetensors").exists() or
                (config.checkpoint_path / "pytorch_model.bin").exists() or
                any(config.checkpoint_path.glob("*.safetensors"))
            )
        else:
            return config.checkpoint_path.exists()
        
    def load_model(self, model_id: str, force: bool = False) -> Optional[Any]:
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
        if not config:
            logger.error(f"Cannot get config for {model_id}")
            return None
        
        # Check if model files exist
        if not self.is_model_available(model_id):
            logger.error(
                f"Model {model_id} not found on disk. "
                f"Expected at: {config.checkpoint_path}"
            )
            return None
            
        # VRAM check
        if not force and not self.vram.can_load(config.vram_gb):
            available = self.vram.get_available_vram_gb()
            logger.warning(
                f"Cannot load {model_id}: needs {config.vram_gb:.1f}GB, "
                f"only {available:.1f}GB available"
            )
            return None
            
        logger.info(f"Loading {model_id} ({config.name})...")
        
        # Load based on model type
        try:
            model = self._load_by_type(model_id, config)
        except Exception as e:
            logger.error(f"Failed to load {model_id}: {e}")
            return None
        
        if model:
            self.loaded_models[model_id] = model
            logger.info(f"✓ {model_id} loaded successfully")
            self.vram.print_status()
            
        return model
        
    def _load_by_type(self, model_id: str, config: ModelConfig) -> Optional[Any]:
        """Load model based on its type."""
        model_data = self.registry.get("models", {}).get(model_id, {})
        model_type = model_data.get("type")
        
        try:
            if model_type == "detection":
                return self._load_yolo(config)
            elif model_id == "eagle2-2b":
                return self._load_eagle2(config)
            elif model_id.startswith("qwen"):
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
        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error("ultralytics not installed. Install with: pip install ultralytics")
            return None
        
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
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor
            import torch
        except ImportError:
            logger.error("transformers not installed. Install with: pip install transformers")
            return None
        
        if not config.checkpoint_path.exists():
            logger.warning(f"Eagle2 not found at {config.checkpoint_path}")
            return None
            
        model = AutoModelForVision2Seq.from_pretrained(
            str(config.checkpoint_path),
            torch_dtype=torch.float16,
            device_map="cuda:0" if torch.cuda.is_available() else "cpu",
            trust_remote_code=True,
        )
        processor = AutoProcessor.from_pretrained(
            str(config.checkpoint_path),
            trust_remote_code=True,
        )
        
        return {"model": model, "processor": processor}
        
    def _load_qwen(self, config: ModelConfig):
        """Load Qwen model (handles both 2.5 and 3.5 versions)."""
        try:
            import torch
        except ImportError:
            logger.error("torch not installed")
            return None
        
        if not config.checkpoint_path.exists():
            logger.warning(f"Qwen not found at {config.checkpoint_path}")
            return None
        
        # Check if it's Qwen3.5 (NVFP4) or Qwen2.5
        is_nvfp4 = config.quantization == "nvfp4"
        
        try:
            if is_nvfp4:
                # NVFP4 models use AutoModelForCausalLM
                from transformers import AutoModelForCausalLM, AutoProcessor
                
                model = AutoModelForCausalLM.from_pretrained(
                    str(config.checkpoint_path),
                    torch_dtype=torch.float16,
                    device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                    trust_remote_code=True,
                )
            else:
                # Qwen2.5 uses Qwen2_5_VLForConditionalGeneration
                from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
                
                model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    str(config.checkpoint_path),
                    torch_dtype=torch.float16,
                    device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                )
            
            processor = AutoProcessor.from_pretrained(
                str(config.checkpoint_path),
                trust_remote_code=True,
            )
            
            return {"model": model, "processor": processor}
            
        except Exception as e:
            logger.error(f"Error loading Qwen model: {e}")
            return None
        
    def _load_sam(self, config: ModelConfig):
        """Load SAM segmentation model."""
        # SAM loading depends on specific implementation
        logger.info(f"SAM model {config.id} would be loaded here")
        logger.info("Note: Using MobileSAM is recommended for faster inference")
        return None
        
    def unload_model(self, model_id: str):
        """Unload a model and free VRAM."""
        if model_id not in self.loaded_models:
            return
            
        logger.info(f"Unloading {model_id}...")
        del self.loaded_models[model_id]
        
        # Force garbage collection
        try:
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass
        
        logger.info(f"✓ {model_id} unloaded")
        self.vram.print_status()
        
    def load_strategy(self, strategy_name: str):
        """
        Load a predefined strategy from registry.
        
        Strategies: standard_trading, fast_scout, deep_analysis, minimal
        """
        strategy = self.registry.get("loading_strategies", {}).get(strategy_name)
        if not strategy:
            logger.error(f"Unknown strategy: {strategy_name}")
            return
            
        logger.info(f"Loading strategy: {strategy.get('name', strategy_name)}")
        logger.info(f"Description: {strategy.get('description', '')}")
        
        load_order = strategy.get("load_order", [])
        loaded_count = 0
        skipped_count = 0
        
        for model_id in load_order:
            if not self.is_model_available(model_id):
                logger.warning(f"Skipping {model_id} - not available on disk")
                skipped_count += 1
                continue
                
            result = self.load_model(model_id)
            if result:
                loaded_count += 1
            else:
                skipped_count += 1
        
        logger.info(f"✓ Strategy '{strategy_name}' loaded: {loaded_count} models loaded, {skipped_count} skipped")
        
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
        
        for model_id, model_data in self.registry.get("models", {}).items():
            exists = self.is_model_available(model_id)
            results[model_id] = exists
            
            status = "✓" if exists else "✗"
            print(f"{status} {model_id}: {model_data.get('name', model_id)}")
            
        return results
    
    def list_strategies(self):
        """List all available loading strategies."""
        print("\nAvailable Loading Strategies:")
        print("=" * 60)
        
        strategies = self.registry.get("loading_strategies", {})
        for strategy_id, strategy in strategies.items():
            load_order = strategy.get("load_order", [])
            available_count = sum(1 for m in load_order if self.is_model_available(m))
            
            print(f"\n{strategy_id}:")
            print(f"  Name: {strategy.get('name', '')}")
            print(f"  Description: {strategy.get('description', '')}")
            print(f"  Models: {available_count}/{len(load_order)} available")
            print(f"  VRAM: ~{strategy.get('total_vram_nvfp4_gb', 0):.1f}GB")
            
            if load_order:
                print("  Load order:")
                for model_id in load_order:
                    available = "✓" if self.is_model_available(model_id) else "✗"
                    print(f"    {available} {model_id}")


def main():
    """CLI for model orchestration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model loading orchestrator")
    parser.add_argument("action", choices=["load", "unload", "strategy", "verify", "status", "list-strategies"])
    parser.add_argument("--model", help="Model ID for load/unload")
    parser.add_argument("--strategy", help="Strategy name for strategy action")
    
    args = parser.parse_args()
    
    orchestrator = ModelOrchestrator()
    
    if args.action == "load" and args.model:
        result = orchestrator.load_model(args.model)
        exit(0 if result else 1)
        
    elif args.action == "unload" and args.model:
        orchestrator.unload_model(args.model)
        
    elif args.action == "strategy" and args.strategy:
        orchestrator.load_strategy(args.strategy)
        
    elif args.action == "verify":
        results = orchestrator.verify_all()
        all_ok = all(results.values())
        exit(0 if all_ok else 1)
        
    elif args.action == "status":
        orchestrator.vram.print_status()
        
    elif args.action == "list-strategies":
        orchestrator.list_strategies()
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
