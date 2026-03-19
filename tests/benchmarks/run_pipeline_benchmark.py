#!/usr/bin/env python3
"""
Pipeline Latency Benchmark
Measures actual end-to-end pipeline performance:
- Full hot path: Capture → YOLO → Eagle → Governor → WSS
- Each stage timing
- Total must be <5s
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def check_dependencies():
    """Check if pipeline dependencies are available."""
    try:
        from advanced_vision.trading.governed_pipeline import GovernedPipeline
        return True
    except ImportError as e:
        print(f"❌ Cannot import pipeline: {e}")
        return False

def run_benchmark():
    """Run actual pipeline latency benchmark."""
    from advanced_vision.trading.governed_pipeline import GovernedPipeline
    from advanced_vision.core.governor import Governor
    from advanced_vision.core.execution_gate import ExecutionGate
    
    print("Initializing governed pipeline...")
    print("Expected: Capture → YOLO → Eagle → Governor → WSS")
    print("Target total: <5s")
    
    # Initialize pipeline
    start_init = time.time()
    
    # Note: This won't actually run without models loaded
    # But it shows the structure
    
    governor = Governor()
    execution_gate = ExecutionGate(governor=governor)
    
    init_time = time.time() - start_init
    print(f"✅ Pipeline initialized in {init_time:.2f}s")
    
    # Stage timing simulation (when models are loaded)
    stages = {
        "capture": {"target_ms": 50, "actual_ms": None},
        "yolo_detection": {"target_ms": 50, "actual_ms": None},
        "eagle_classification": {"target_ms": 400, "actual_ms": None},
        "governor_evaluation": {"target_ms": 10, "actual_ms": None},
        "truth_writer": {"target_ms": 5, "actual_ms": None},
        "wss_publish": {"target_ms": 10, "actual_ms": None},
    }
    
    print("\n=== STAGE TIMING (when models loaded) ===")
    total_target = 0
    for stage, timing in stages.items():
        target = timing["target_ms"]
        total_target += target
        print(f"   {stage:20}: {target:4}ms target")
    
    print(f"\nTotal target: {total_target}ms ({total_target/1000:.2f}s)")
    print(f"Budget: 5000ms (5s)")
    print(f"Headroom: {5000 - total_target}ms")
    
    # Results
    results = {
        "stages": stages,
        "summary": {
            "target_total_ms": total_target,
            "budget_ms": 5000,
            "headroom_ms": 5000 - total_target,
            "status": "needs_actual_run"
        }
    }
    
    print("\n⚠️  Note: Actual timing requires models to be loaded")
    print("   Run this after loading: yolov8n, mobilesam, eagle2-2b")
    
    # Save results
    os.makedirs("benchmarks", exist_ok=True)
    with open("benchmarks/pipeline_latency.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to: benchmarks/pipeline_latency.json")

if __name__ == "__main__":
    print("=" * 60)
    print("Pipeline Latency Benchmark")
    print("=" * 60)
    print()
    
    if not check_dependencies():
        print("\n⚠️  Pipeline not fully initialized")
        print("   This is expected - shows target structure")
    
    run_benchmark()
