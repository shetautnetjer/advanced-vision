#!/usr/bin/env python3
"""
Controlled Evaluation of Pre-trained UI YOLO Model
Tests foduucom/web-form-ui-field-detection on our screenshots
Safe loading with torch.serialization.add_safe_globals
"""

import os
import sys
import json
import time
import warnings

def setup_safe_loading():
    """Configure PyTorch for safe loading of older weights."""
    import torch
    import ultralytics.nn.tasks
    
    # Allow the specific class needed for this model
    torch.serialization.add_safe_globals([
        ultralytics.nn.tasks.DetectionModel,
    ])
    
    print("✅ PyTorch safe globals configured")
    print("   Allowed: ultralytics.nn.tasks.DetectionModel")
    return True

def load_model_safely():
    """Load the UI detection model with safe globals."""
    try:
        from ultralyticsplus import YOLO
        
        print("\n" + "="*60)
        print("LOADING PRE-TRAINED UI MODEL")
        print("="*60)
        print("Model: foduucom/web-form-ui-field-detection")
        print("Source: Hugging Face (trusted)")
        print("Loading with add_safe_globals protection...")
        print()
        
        # Load model - should work with safe globals configured
        start = time.time()
        model = YOLO('foduucom/web-form-ui-field-detection')
        load_time = time.time() - start
        
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

def evaluate_on_screenshots(model, max_images=20):
    """Evaluate model on our screenshots."""
    
    print("\n" + "="*60)
    print("EVALUATION ON REAL SCREENSHOTS")
    print("="*60)
    
    screenshot_dir = 'artifacts/screens'
    if not os.path.exists(screenshot_dir):
        print(f"❌ Directory not found: {screenshot_dir}")
        return None
    
    # Get large screenshots
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
        print(f"Test {i+1}/{max_images}: {os.path.basename(img_path)}")
        
        try:
            # Run inference
            infer_start = time.time()
            predictions = model.predict(img_path, verbose=False)
            inference_time = (time.time() - infer_start) * 1000
            
            # Get detections
            boxes = predictions[0].boxes
            num_detections = len(boxes)
            total_detections += num_detections
            
            # Count classes
            detected_classes = []
            for box in boxes:
                cls_id = int(box.cls)
                cls_name = model.names[cls_id]
                detected_classes.append(cls_name)
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
            
            print(f"   Time: {inference_time:.1f}ms")
            print(f"   Detections: {num_detections}")
            
            if num_detections > 0:
                # Show top 3 by confidence
                confs = [float(box.conf) for box in boxes[:3]]
                print(f"   Top detections:")
                for cls, conf in zip(detected_classes[:3], confs):
                    print(f"      - {cls}: {conf:.2f}")
            else:
                print("   No UI elements detected")
            
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

def analyze_results(results, total_detections, class_counts, num_images):
    """Analyze evaluation results."""
    
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    
    valid_results = [r for r in results if "latency_ms" in r]
    
    if not valid_results:
        print("❌ No valid results to analyze")
        return
    
    # Performance metrics
    avg_latency = sum(r["latency_ms"] for r in valid_results) / len(valid_results)
    avg_detections = total_detections / len(valid_results)
    
    print(f"\nPerformance:")
    print(f"   Images tested: {len(valid_results)}")
    print(f"   Avg latency: {avg_latency:.1f}ms")
    print(f"   Avg detections/image: {avg_detections:.1f}")
    print(f"   Total detections: {total_detections}")
    
    # Detection quality
    print(f"\nDetection Distribution:")
    for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_detections * 100) if total_detections > 0 else 0
        print(f"   {cls}: {count} ({pct:.1f}%)")
    
    # Agent loop assessment
    print(f"\nAgent Loop Assessment:")
    
    if avg_latency < 100:
        print(f"   ✅ Latency: Fast enough for real-time ({avg_latency:.0f}ms)")
    elif avg_latency < 200:
        print(f"   ⚠️  Latency: Acceptable but not ideal ({avg_latency:.0f}ms)")
    else:
        print(f"   ❌ Latency: Too slow for hot path ({avg_latency:.0f}ms)")
    
    if avg_detections > 0:
        print(f"   ✅ Detecting UI elements consistently")
    else:
        print(f"   ❌ Not detecting expected UI elements")
    
    # Key classes for trading
    trading_relevant = ['button', 'text_input', 'dropdown']
    found_trading = [cls for cls in trading_relevant if cls in class_counts]
    
    if found_trading:
        print(f"   ✅ Trading-relevant classes detected: {found_trading}")
    else:
        print(f"   ⚠️  Missing trading-relevant classes in detections")
    
    # Recommendation
    print(f"\nRecommendation:")
    
    if avg_latency < 100 and avg_detections > 2:
        print(f"   ✅ Model shows promise for agent loop")
        print(f"      Next: Fine-tune on trading-specific UI if needed")
    elif avg_detections == 0:
        print(f"   ❌ Model not detecting on our screenshots")
        print(f"      Next: Train custom model on our data")
    else:
        print(f"   ⚠️  Model works but may need optimization")
        print(f"      Next: Evaluate vs custom training trade-off")
    
    return {
        "avg_latency_ms": avg_latency,
        "avg_detections": avg_detections,
        "total_detections": total_detections,
        "class_distribution": class_counts
    }

def save_results(results, summary):
    """Save evaluation results."""
    os.makedirs('benchmarks', exist_ok=True)
    
    output = {
        "model": "foduucom/web-form-ui-field-detection",
        "test_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "pytorch_version": "2.6+ (weights_only=True default)",
        "loading_method": "torch.serialization.add_safe_globals",
        "results": results,
        "summary": summary
    }
    
    with open('benchmarks/ui_yolo_evaluation.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Results saved to: benchmarks/ui_yolo_evaluation.json")

def main():
    print("="*60)
    print("CONTROLLED UI YOLO MODEL EVALUATION")
    print("="*60)
    print()
    print("Testing: foduucom/web-form-ui-field-detection")
    print("Safety: torch.serialization.add_safe_globals")
    print("Goal: Determine if model helps agent loop")
    print()
    
    # Step 1: Setup safe loading
    if not setup_safe_loading():
        print("❌ Failed to configure safe loading")
        sys.exit(1)
    
    # Step 2: Load model
    model = load_model_safely()
    if not model:
        print("\n❌ Cannot proceed without model")
        print("   Try: pip install --upgrade ultralytics ultralyticsplus")
        sys.exit(1)
    
    # Step 3: Evaluate
    results, total_detections, class_counts = evaluate_on_screenshots(model, max_images=20)
    
    if not results:
        print("❌ Evaluation failed")
        sys.exit(1)
    
    # Step 4: Analyze
    summary = analyze_results(results, total_detections, class_counts, len(results))
    
    # Step 5: Save
    save_results(results, summary)
    
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print("\nNext steps based on results:")
    print("   1. Review benchmarks/ui_yolo_evaluation.json")
    print("   2. If promising: Fine-tune on trading-specific data")
    print("   3. If poor: Proceed with custom training pipeline")

if __name__ == "__main__":
    # Suppress warnings for cleaner output
    warnings.filterwarnings('ignore')
    main()
