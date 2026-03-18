"""Eagle2-2B Vision Classification Example - WORKING

This example shows Eagle2 working as the fast vision scout.
Eagle2 uses SigLIP vision encoder + Phi-2 language model.
"""

import torch
from transformers import AutoProcessor, AutoModel
from PIL import Image
import time

print("Loading Eagle2-2B...")
processor = AutoProcessor.from_pretrained(
    "models/Eagle2-2B",
    trust_remote_code=True
)

model = AutoModel.from_pretrained(
    "models/Eagle2-2B",
    torch_dtype=torch.bfloat16,
    device_map="cuda",
    trust_remote_code=True
)

print(f"✅ Eagle2 loaded! VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
print(f"Model type: {type(model).__name__}")

# Test with a screenshot
try:
    from advanced_vision.tools import screenshot_full
    
    print("\n📸 Capturing screenshot...")
    artifact = screenshot_full()
    
    # Load image
    image = Image.open(artifact.path)
    print(f"Image size: {image.size}")
    
    # Eagle2 prompt for trading UI classification
    prompt = """
    What do you see in this image? 
    Is it: a trading chart, a button, a dialog box, a text input, or something else?
    Respond with just the category.
    """
    
    print("\n🔍 Running Eagle2 classification...")
    start = time.time()
    
    # Process
    inputs = processor(text=prompt, images=image, return_tensors="pt").to("cuda")
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            do_sample=False
        )
    
    result = processor.decode(outputs[0], skip_special_tokens=True)
    elapsed = time.time() - start
    
    print(f"\n✅ Eagle2 Result ({elapsed:.2f}s):")
    print(f"Classification: {result}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nNote: Eagle2 requires flash-attn for optimal speed.")
    print("Current: Working but may be slower without flash-attn.")
