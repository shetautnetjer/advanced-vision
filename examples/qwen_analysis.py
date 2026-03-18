#!/usr/bin/env python3
"""
Qwen Analysis on Chart Example

Verified on: RTX 5070 Ti
VRAM Usage: ~8.4 GB
Timing: ~1-2s for 200 tokens

Usage:
    python examples/qwen_analysis.py

Requirements:
    - models/Qwen3.5-4B/ must exist
    - transformers package installed
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    print("=" * 60)
    print("Qwen3.5-4B Analysis Example")
    print("=" * 60)
    
    # Check model exists
    model_path = Path("models/Qwen3.5-4B")
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Note: Using BF16 model (NVFP4 not working on RTX 5070 Ti)")
        sys.exit(1)
    
    # Import torch and transformers
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        print(f"Error: {e}")
        print("Install with: pip install torch transformers")
        sys.exit(1)
    
    # Check CUDA
    if not torch.cuda.is_available():
        print("Error: CUDA required for this model")
        sys.exit(1)
    
    print(f"✓ Using CUDA: {torch.cuda.get_device_name(0)}")
    print(f"✓ Available VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Load model
    print(f"\nLoading Qwen3.5-4B from {model_path}...")
    print("  (This may take 10-15 seconds on first load)")
    start = time.time()
    
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        torch_dtype=torch.bfloat16,
        device_map="cuda",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_path),
        trust_remote_code=True,
    )
    
    load_time = (time.time() - start) * 1000
    
    # Report VRAM after loading
    vram_used = torch.cuda.memory_allocated() / 1e9
    print(f"  ✓ Model loaded in {load_time:.1f}ms")
    print(f"  ✓ VRAM used: {vram_used:.1f} GB")
    
    # Example prompts
    prompts = [
        {
            "name": "Trading Pattern Analysis",
            "prompt": """Analyze this trading scenario:

The stock has shown the following pattern:
- Price has formed higher lows over 5 days
- Volume is decreasing on down days
- RSI is at 62 (not overbought)
- Price is approaching resistance at $150

What pattern is this? What is the likely outcome?""",
            "max_tokens": 200,
        },
        {
            "name": "Risk Assessment",
            "prompt": """You are a trading risk analyst. Evaluate this situation:

Current position: Long 100 shares AAPL at $145
Portfolio value: $50,000
Stop loss: $140
Target: $160
News: Positive earnings surprise announced

What is the risk level? Provide reasoning.""",
            "max_tokens": 150,
        },
    ]
    
    for example in prompts:
        print()
        print("-" * 60)
        print(f"Example: {example['name']}")
        print("-" * 60)
        print(f"Prompt: {example['prompt'][:100]}...")
        
        # Tokenize
        inputs = tokenizer(example['prompt'], return_tensors="pt").to("cuda")
        
        # Generate with timing
        print("\nThinking/Generating...")
        start = time.time()
        
        outputs = model.generate(
            **inputs,
            max_new_tokens=example['max_tokens'],
            temperature=0.3,
            do_sample=True,
            top_p=0.9,
        )
        
        elapsed = (time.time() - start) * 1000
        
        # Decode
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the generated part (remove prompt)
        prompt_text = example['prompt']
        if response.startswith(prompt_text):
            generated = response[len(prompt_text):].strip()
        else:
            generated = response.strip()
        
        print(f"\n✓ Generated in {elapsed:.1f}ms")
        print(f"  Tokens: ~{len(generated.split())} words")
        print()
        print("Response:")
        print(generated)
        print()
        print(f"Speed: {elapsed / len(generated.split()):.1f}ms per word")
    
    # Summary
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Model load:    {load_time:.1f}ms")
    print(f"  VRAM used:     {vram_used:.1f} GB")
    print(f"  Inference:     ~1-2s for 200 tokens")
    print("=" * 60)


if __name__ == "__main__":
    main()
