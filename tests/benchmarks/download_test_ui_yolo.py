#!/usr/bin/env python3
"""
Download and Test Specific YOLO Models using ultralyticsplus
Models:
- foduucom/web-form-ui-field-detection (requires ultralyticsplus)
"""

import os
import sys
import json
import time

def install_ultralyticsplus():
    """Install ultralyticsplus package."""
    print("Installing ultralyticsplus...")
    os.system("pip install ultralyticsplus==0.0.28 ultralytics==8.0.43 -q")
    print("✅ ultralyticsplus installed")

def download_ui_model():
    """Download YOLO model trained for UI element detection."""
    try:
        from ultralyticsplus import YOLO
        
        print("\n" + "="*60)
        print("DOWNLOADING UI DETECTION MODEL")
        print("="*60)
        print("Model: foduucom/web-form-ui-field-detection")
        print("Source: Hugging Face via ultralyticsplus")
        print("Classes: Name, Email, Password, Button, Radio, etc.")
        print()
        
        print("Downloading... (this may take a few minutes)")
        model = YOLO('foduucom/web-form-ui-field-detection')
        
        # Save locally
        os.makedirs('models/yolo_ui', exist_ok=True)
        model.save('models/yolo_ui/ui_field_detector.pt')
        
        print("✅ UI model downloaded successfully")
        print(f"   Saved to: models/yolo_ui/ui_field_detector.pt")
        
        # Show model info
        print(f"\nModel Info:")
        print(f"   Classes: {model.names}")
        
        return model
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_on_screenshots(model, model_name, screenshot_dir='artifacts/screens'):
    """Test model on actual screenshots."""
    
    print("\n" + "="*60)
    print(f"TESTING {model_name}")
    print("="*60)
    
    if not os.path.exists(screenshot_dir):
        print(f"❌ Directory not found: {screenshot_dir}")
        return None
    
    # Get large screenshots (real captures)
    screenshots = [
        os.path.join(screenshot_dir, f) 
        for f in os.listdir(screenshot_dir) 
        if f.endswith('.png') and os.path.getsize(os.path.join(screenshot_dir, f)) > 100000
    ]
    
    if not screenshots:
        print("❌ No screenshots found")
        return None
    
    print(f"Found {len(screenshots)} screenshots")
    print(f"Testing on first 5...\n")
    
    results = []
    
    for i, img_path in enumerate(screenshots[:5]):
        print(f"Test {i+1}: {os.path.basename(img_path)}")
        
        try:
            # Run inference
            start = time.time()
            results_pred = model.predict(img_path)
            inference_time = (time.time() - start) * 1000  # ms
            
            # Get detections
            boxes = results_pred[0].boxes
            num_detections = len(boxes)
            
            print(f"   Time: {inference_time:.1f}ms")
            print(f"   Detections: {num_detections}")
            
            if num_detections > 0:
                # Show top detections
                class_names = [model.names[int(box.cls)] for box in boxes[:5]]
                confidences = [float(box.conf) for box in boxes[:5]]
                
                print(f"   Detected classes:")
                for name, conf in zip(class_names, confidences):
                    print(f"      - {name}: {conf:.2f}")
            else:
                print("   No detections")
            
            results.append({
                "image": os.path.basename(img_path),
                "latency_ms": inference_time,
                "detections": num_detections,
                "classes": [model.names[int(box.cls)] for box in boxes[:5]] if num_detections > 0 else []
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "image": os.path.basename(img_path),
                "error": str(e)
            })
    
    return results

def main():
    print("="*60)
    print("YOLO MODEL DOWNLOADER & TESTER")
    print("="*60)
    print()
    
    # Install ultralyticsplus
    install_ultralyticsplus()
    
    # Download and test UI model
    ui_model = download_ui_model()
    
    if ui_model:
        ui_results = test_on_screenshots(ui_model, "UI FIELD DETECTION")
        
        # Summary
        if ui_results:
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            
            valid_results = [r for r in ui_results if "latency_ms" in r]
            if valid_results:
                avg_time = sum(r["latency_ms"] for r in valid_results) / len(valid_results)
                total_detections = sum(r["detections"] for r in valid_results)
                
                print(f"Average latency: {avg_time:.1f}ms")
                print(f"Total detections: {total_detections}")
                print(f"Avg detections/image: {total_detections/len(valid_results):.1f}")
            
            # Save results
            os.makedirs('benchmarks', exist_ok=True)
            with open('benchmarks/ui_yolo_test_results.json', 'w') as f:
                json.dump({
                    "model": "foduucom/web-form-ui-field-detection",
                    "results": ui_results,
                    "summary": {
                        "avg_latency_ms": avg_time if valid_results else 0,
                        "total_detections": total_detections if valid_results else 0
                    }
                }, f, indent=2)
            
            print(f"\nResults saved to: benchmarks/ui_yolo_test_results.json")
    else:
        print("❌ Could not download UI model")
    
    print("\nDone! ✅")

if __name__ == "__main__":
    main()
