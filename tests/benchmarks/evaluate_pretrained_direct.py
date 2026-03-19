#!/usr/bin/env python3
"""
Alternative: Download and Evaluate with Direct Weight Loading
Downloads weights from HF, loads with trusted source flag
"""

import os
import sys
import json
import time
import torch
import warnings

def download_weights_directly():
    """Download model weights directly from Hugging Face."""
    print("="*60)
    print("DOWNLOADING MODEL WEIGHTS")
    print("="*60)
    print()
    
    model_url = "https://huggingface.co/foduucom/web-form-ui-field-detection/resolve/main/best.pt"
    output_path = "models/yolo_ui/best.pt"
    
    os.makedirs("models/yolo_ui", exist_ok=True)
    
    if os.path.exists(output_path):
        print(f"✅ Model already exists: {output_path}")
        return output_path
    
    print(f"Downloading from: {model_url}")
    print(f"Saving to: {output_path}")
    print()
    
    try:
        import urllib.request
        
        def download_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            print(f"\r   Progress: {percent:.1f}% ({downloaded / 1024 / 1024:.1f}MB)", end='')
        
        urllib.request.urlretrieve(model_url, output_path, reporthook=download_progress)
        print()  # New line after progress
        print(f"✅ Download complete")
        return output_path
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None

def load_with_trusted_source(weights_path):
    """Load model with weights_only=False (trusted source)."""
    print("\n" + "="*60)
    print("LOADING MODEL (Trusted Source)")
    print("="*60)
    print("Source: Hugging Face (foduucom)")
    print("Security: weights_only=False for trusted checkpoint")
    print()
    
    try:
        from ultralytics import YOLO
        
        # Temporarily patch torch.load to use weights_only=False
        original_load = torch.load
        
        def patched_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
        
        torch.load = patched_load
        
        # Load model
        start = time.time()
        model = YOLO(weights_path)
        load_time = time.time() - start
        
        # Restore original load
        torch.load = original_load
        
        print(f"✅ Model loaded in {load_time:.1f}s")
        print(f"\nModel Info:")
        print(f"   Classes: {model.names}")
        print(f"   Task: {model.task}")
        
        return model
        
    except Exception as e:
        print(f"❌ Failed to load: {e}")
        import traceback
        traceback.print_exc()
        return None

def evaluate_model(model, max_images=20):
    """Evaluate model on screenshots."""
    print("\n" + "="*60)
    print("EVALUATION ON SCREENSHOTS")
    print("="*60)
    
    screenshot_dir = 'artifacts/screens'
    if not os.path.exists(screenshot_dir):
        print(f"❌ Directory not found: {screenshot_dir}")
        return None
    
    screenshots = sorted([
        os.path.join(screenshot_dir, f)
        for f in os.listdir(screenshot_dir)
        if f.endswith('.png') and os.path.getsize(os.path.join(screenshot_dir, f)) > 100000
    ])
    
    print(f"Found {len(screenshots)} screenshots")
    print(f"Testing on first {max_images}...\n")
    
    results = []
    total_detections = 0
    class_counts = {}
    
    for i, img_path in enumerate(screenshots[:max_images]):
        print(f"Test {i+1}/{max_images}: {os.path.basename(img_path)[:40]}...")
        
        try:
            infer_start = time.time()
            predictions = model(img_path, verbose=False)
            inference_time = (time.time() - infer_start) * 1000
            
            boxes = predictions[0].boxes
            num_detections = len(boxes)
            total_detections += num_detections
            
            detected_classes = []
            for box in boxes:
                cls_id = int(box.cls)
                cls_name = model.names[cls_id]
                detected_classes.append(cls_name)
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
            
            print(f"   Time: {inference_time:.1f}ms | Detections: {num_detections}")
            
            if num_detections > 0:
                confs = [float(box.conf) for box in boxes[:3]]
                for cls, conf in zip(detected_classes[:3], confs):
                    print(f"      - {cls}: {conf:.2f}")
            
            results.append({
                "image": os.path.basename(img_path),
                "latency_ms": inference_time,
                "detections": num_detections,
                "classes": detected_classes
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "image": os.path.basename(img_path),
                "error": str(e)
            })
    
    return results, total_detections, class_counts

def print_summary(results, total_detections, class_counts):
    """Print evaluation summary."""
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    
    valid_results = [r for r in results if "latency_ms" in r]
    
    if not valid_results:
        print("❌ No valid results")
        return None
    
    avg_latency = sum(r["latency_ms"] for r in valid_results) / len(valid_results)
    avg_detections = total_detections / len(valid_results)
    
    print(f"\nPerformance:")
    print(f"   Images: {len(valid_results)}")
    print(f"   Avg latency: {avg_latency:.1f}ms")
    print(f"   Avg detections/image: {avg_detections:.1f}")
    
    print(f"\nClass Distribution:")
    for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_detections * 100) if total_detections > 0 else 0
        print(f"   {cls}: {count} ({pct:.1f}%)")
    
    # Assessment
    print(f"\nAgent Loop Assessment:")
    
    if avg_latency < 50:
        print(f"   ✅ Latency: Excellent ({avg_latency:.0f}ms)")
    elif avg_latency < 100:
        print(f"   ✅ Latency: Good ({avg_latency:.0f}ms)")
    elif avg_latency < 200:
        print(f"   ⚠️  Latency: Acceptable ({avg_latency:.0f}ms)")
    else:
        print(f"   ❌ Latency: Poor ({avg_latency:.0f}ms)")
    
    if avg_detections > 3:
        print(f"   ✅ Rich detections (avg {avg_detections:.1f})")
    elif avg_detections > 0:
        print(f"   ⚠️  Sparse detections (avg {avg_detections:.1f})")
    else:
        print(f"   ❌ No detections")
    
    # Trading relevance
    trading_classes = ['button', 'text_input', 'dropdown', 'checkbox']
    found = [c for c in trading_classes if c in class_counts]
    if found:
        print(f"   ✅ Trading-relevant: {found}")
    
    # Recommendation
    print(f"\nRecommendation:")
    if avg_latency < 100 and avg_detections > 2:
        print(f"   ✅ Model is PROMISING for agent loop")
        print(f"      Action: Fine-tune on trading screenshots")
    elif avg_detections == 0:
        print(f"   ❌ Model not working on our data")
        print(f"      Action: Train custom model")
    else:
        print(f"   ⚠️  Model works but needs optimization")
        print(f"      Action: Evaluate fine-tuning vs custom")
    
    return {
        "avg_latency_ms": avg_latency,
        "avg_detections": avg_detections,
        "class_distribution": class_counts
    }

def main():
    print("="*60)
    print("PRE-TRAINED UI YOLO EVALUATION")
    print("="*60)
    print("Model: foduucom/web-form-ui-field-detection")
    print("Approach: Direct download + trusted source loading")
    print()
    
    warnings.filterwarnings('ignore')
    
    # Download
    weights_path = download_weights_directly()
    if not weights_path:
        print("❌ Cannot download weights")
        sys.exit(1)
    
    # Load
    model = load_with_trusted_source(weights_path)
    if not model:
        print("❌ Cannot load model")
        sys.exit(1)
    
    # Evaluate
    results, total_detections, class_counts = evaluate_model(model, max_images=20)
    
    if results:
        summary = print_summary(results, total_detections, class_counts)
        
        # Save
        os.makedirs('benchmarks', exist_ok=True)
        with open('benchmarks/pretrained_ui_yolo_eval.json', 'w') as f:
            json.dump({
                "model": "foduucom/web-form-ui-field-detection",
                "weights_path": weights_path,
                "results": results,
                "summary": summary
            }, f, indent=2)
        
        print(f"\n✅ Results saved to: benchmarks/pretrained_ui_yolo_eval.json")
    
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
