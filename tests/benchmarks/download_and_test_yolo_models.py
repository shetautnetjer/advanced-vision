#!/usr/bin/env python3
"""
Download and Test Specific YOLO Models for UI and Trading
Models from research:
- UI: foduucom/web-form-ui-field-detection
- Trading: foduucom/stockmarket-pattern-detection-yolov8
"""

import os
import sys
import json
import time

def check_ultralytics():
    """Check if ultralytics is installed."""
    try:
        from ultralytics import YOLO
        print("✅ Ultralytics installed")
        return True
    except ImportError:
        print("❌ Ultralytics not installed")
        print("Run: pip install ultralytics")
        return False

def download_ui_model():
    """Download YOLO model trained for UI element detection."""
    from ultralytics import YOLO
    
    print("\n" + "="*60)
    print("DOWNLOADING UI DETECTION MODEL")
    print("="*60)
    print("Model: foduucom/web-form-ui-field-detection")
    print("Source: GitHub/foduucom")
    print("Classes: Form fields, buttons, inputs, etc.")
    print()
    
    try:
        # Download from Hugging Face or GitHub
        print("Downloading... (this may take a few minutes)")
        model = YOLO('foduucom/web-form-ui-field-detection')
        
        # Save locally
        os.makedirs('models/yolo_ui', exist_ok=True)
        model.save('models/yolo_ui/ui_field_detector.pt')
        
        print("✅ UI model downloaded successfully")
        print(f"   Saved to: models/yolo_ui/ui_field_detector.pt")
        return model
        
    except Exception as e:
        print(f"❌ Failed to download UI model: {e}")
        print("   Will try alternative sources...")
        return None

def download_trading_model():
    """Download YOLO model trained for trading pattern detection."""
    from ultralytics import YOLO
    
    print("\n" + "="*60)
    print("DOWNLOADING TRADING PATTERN MODEL")
    print("="*60)
    print("Model: foduucom/stockmarket-pattern-detection-yolov8")
    print("Source: Hugging Face")
    print("Patterns: Head & Shoulders, Triangles, Double Top/Bottom")
    print()
    
    try:
        print("Downloading... (this may take a few minutes)")
        model = YOLO('foduucom/stockmarket-pattern-detection-yolov8')
        
        # Save locally
        os.makedirs('models/yolo_trading', exist_ok=True)
        model.save('models/yolo_trading/pattern_detector.pt')
        
        print("✅ Trading model downloaded successfully")
        print(f"   Saved to: models/yolo_trading/pattern_detector.pt")
        return model
        
    except Exception as e:
        print(f"❌ Failed to download trading model: {e}")
        return None

def test_model_on_screenshots(model, model_name, screenshot_dir='artifacts/screens'):
    """Test downloaded model on actual screenshots."""
    
    print("\n" + "="*60)
    print(f"TESTING {model_name.upper()} MODEL")
    print("="*60)
    
    if not os.path.exists(screenshot_dir):
        print(f"❌ Screenshot directory not found: {screenshot_dir}")
        return None
    
    # Get screenshots
    screenshots = [
        os.path.join(screenshot_dir, f) 
        for f in os.listdir(screenshot_dir) 
        if f.endswith('.png') and os.path.getsize(os.path.join(screenshot_dir, f)) > 100000
    ]
    
    if not screenshots:
        print("❌ No screenshots found")
        return None
    
    print(f"Found {len(screenshots)} screenshots")
    print(f"Testing on first 5...")
    print()
    
    results = []
    
    for i, img_path in enumerate(screenshots[:5]):
        print(f"\nTest {i+1}: {os.path.basename(img_path)}")
        
        try:
            # Run inference
            start = time.time()
            detections = model(img_path, verbose=False)
            inference_time = (time.time() - start) * 1000  # ms
            
            # Count detections
            num_detections = len(detections[0].boxes)
            
            # Get class names if available
            if hasattr(model, 'names'):
                class_names = [model.names[int(box.cls)] for box in detections[0].boxes[:3]]
            else:
                class_names = [f"class_{int(box.cls)}" for box in detections[0].boxes[:3]]
            
            print(f"   Time: {inference_time:.1f}ms")
            print(f"   Detections: {num_detections}")
            
            if num_detections > 0:
                print(f"   Top classes: {', '.join(class_names)}")
                
                # Show confidence scores
                confidences = [float(box.conf) for box in detections[0].boxes[:3]]
                for name, conf in zip(class_names, confidences):
                    print(f"      - {name}: {conf:.2f}")
            else:
                print("   No detections")
            
            results.append({
                "image": os.path.basename(img_path),
                "latency_ms": inference_time,
                "detections": num_detections,
                "classes": class_names if num_detections > 0 else []
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "image": os.path.basename(img_path),
                "error": str(e)
            })
    
    return results

def compare_with_baseline(ui_results, trading_results, baseline_results=None):
    """Compare specialized models vs baseline YOLOv8n."""
    
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    
    if ui_results:
        avg_ui_time = sum(r["latency_ms"] for r in ui_results if "latency_ms" in r) / len([r for r in ui_results if "latency_ms" in r])
        total_ui_detections = sum(r["detections"] for r in ui_results if "detections" in r)
        print(f"\nUI Model:")
        print(f"   Avg latency: {avg_ui_time:.1f}ms")
        print(f"   Total detections: {total_ui_detections}")
        print(f"   Detections/image: {total_ui_detections/len(ui_results):.1f}")
    
    if trading_results:
        avg_trading_time = sum(r["latency_ms"] for r in trading_results if "latency_ms" in r) / len([r for r in trading_results if "latency_ms" in r])
        total_trading_detections = sum(r["detections"] for r in trading_results if "detections" in r)
        print(f"\nTrading Model:")
        print(f"   Avg latency: {avg_trading_time:.1f}ms")
        print(f"   Total detections: {total_trading_detections}")
        print(f"   Detections/image: {total_trading_detections/len(trading_results):.1f}")
    
    print("\n✅ Comparison complete")

def main():
    print("="*60)
    print("YOLO MODEL DOWNLOADER & TESTER")
    print("="*60)
    print()
    
    # Check dependencies
    if not check_ultralytics():
        sys.exit(1)
    
    # Download models
    ui_model = download_ui_model()
    trading_model = download_trading_model()
    
    # Test models
    ui_results = None
    trading_results = None
    
    if ui_model:
        ui_results = test_model_on_screenshots(ui_model, "UI")
    
    if trading_model:
        trading_results = test_model_on_screenshots(trading_model, "Trading")
    
    # Compare
    if ui_results or trading_results:
        compare_with_baseline(ui_results, trading_results)
    
    # Save results
    os.makedirs('benchmarks', exist_ok=True)
    with open('benchmarks/yolo_model_comparison.json', 'w') as f:
        json.dump({
            "ui_model": ui_results,
            "trading_model": trading_results,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2)
    
    print(f"\nResults saved to: benchmarks/yolo_model_comparison.json")
    print("\nDone! ✅")

if __name__ == "__main__":
    main()
