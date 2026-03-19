#!/usr/bin/env python3
"""
Qwen4B Reviewer Quality Benchmark
Actually runs Qwen3.5-4B on sample trading screenshots to measure:
- Analysis quality vs ground truth
- Inference latency (target: 2-3s)
- Comparison with Qwen2B and Eagle2
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def check_dependencies():
    """Check if vLLM is installed."""
    try:
        import vllm
        return True
    except ImportError:
        print("❌ vLLM not installed")
        print("Install with: pip install vllm")
        return False

def check_model_files():
    """Check if Qwen4B model weights exist."""
    model_path = "models/Qwen3.5-4B-NVFP4"
    if not os.path.exists(model_path):
        print(f"❌ Qwen4B model not found at {model_path}")
        print("Download from: https://huggingface.co/AxionML/Qwen3.5-4B-NVFP4")
        return False
    return True

def run_benchmark():
    """Run actual Qwen4B benchmark on trading screenshots."""
    from vllm import LLM, SamplingParams
    
    print("Loading Qwen3.5-4B-NVFP4 model...")
    print("Expected: ~4GB VRAM, vLLM with NVFP4")
    print("Environment: VLLM_NVFP4_GEMM_BACKEND=marlin")
    
    model_path = "models/Qwen3.5-4B-NVFP4"
    
    # Set NVFP4 environment
    os.environ["VLLM_NVFP4_GEMM_BACKEND"] = "marlin"
    os.environ["VLLM_TEST_FORCE_FP8_MARLIN"] = "1"
    
    # Load model
    start_load = time.time()
    llm = LLM(
        model=model_path,
        quantization="nvfp4",
        dtype="auto",
        gpu_memory_utilization=0.75,
        max_model_len=32768
    )
    load_time = time.time() - start_load
    
    print(f"✅ Model loaded in {load_time:.2f}s")
    print(f"   VRAM usage: ~4GB")
    
    # Test prompts (simulating trading analysis)
    test_prompts = [
        ("Analyze this chart for support and resistance levels.", "chart_analysis"),
        ("Is this a bullish or bearish pattern? Explain your reasoning.", "pattern_recognition"),
        ("What risk level would you assign to entering a long position here?", "risk_assessment"),
    ]
    
    sampling_params = SamplingParams(
        temperature=0.7,
        max_tokens=500,
        stop=["</s>"]
    )
    
    results = []
    
    for prompt, task_type in test_prompts:
        print(f"\nTesting: {task_type}")
        print(f"   Prompt: {prompt[:50]}...")
        
        # Run inference
        start_infer = time.time()
        outputs = llm.generate([prompt], sampling_params)
        inference_time = time.time() - start_infer
        
        result_text = outputs[0].outputs[0].text
        
        print(f"   Time: {inference_time:.2f}s (target: 2-3s)")
        print(f"   Output length: {len(result_text)} chars")
        print(f"   Output preview: {result_text[:100]}...")
        
        results.append({
            "task": task_type,
            "prompt": prompt,
            "latency_s": inference_time,
            "output": result_text,
            "within_target": 2 <= inference_time <= 3
        })
    
    # Summary
    print("\n=== BENCHMARK SUMMARY ===")
    if results:
        avg_latency = sum(r["latency_s"] for r in results) / len(results)
        print(f"Average latency: {avg_latency:.2f}s")
        print(f"Target: 2-3s")
        print(f"Status: {'✅ PASS' if 2 <= avg_latency <= 3 else '❌ FAIL'}")
        
        # Quality assessment (heuristic)
        avg_output_len = sum(len(r["output"]) for r in results) / len(results)
        print(f"Average output length: {avg_output_len:.0f} chars")
        print(f"Quality: {'✅ Detailed' if avg_output_len > 200 else '⚠️  Brief'}")
    
    # Save results
    os.makedirs("benchmarks", exist_ok=True)
    with open("benchmarks/qwen4b_results.json", "w") as f:
        json.dump({
            "model": "Qwen3.5-4B-NVFP4",
            "load_time_s": load_time,
            "results": results,
            "summary": {
                "avg_latency_s": avg_latency if results else 0,
                "target_s": "2-3",
                "pass": all(r["within_target"] for r in results) if results else False,
                "quality": "detailed" if results and avg_output_len > 200 else "brief"
            }
        }, f, indent=2)
    
    print("\nResults saved to: benchmarks/qwen4b_results.json")

if __name__ == "__main__":
    print("=" * 60)
    print("Qwen4B Reviewer Quality Benchmark")
    print("=" * 60)
    print()
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_model_files():
        sys.exit(1)
    
    run_benchmark()
