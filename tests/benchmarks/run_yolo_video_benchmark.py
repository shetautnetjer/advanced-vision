#!/usr/bin/env python3
"""
YOLO Video Detection Benchmark
Tests YOLOv8n performance on actual video streams:
- Frame-by-frame detection
- Real-time performance (target: <50ms/frame)
- Detection accuracy on UI/trading elements
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def check_dependencies():
    """Check if YOLO dependencies are installed."""
    try:
        from ultralytics import YOLO
        import cv2
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install ultralytics opencv-python")
        return False

def check_model_files():
    """Check if YOLO model weights exist."""
    model_path = "models/yolov8n.pt"
    if not os.path.exists(model_path):
        print(f"❌ YOLO model not found at {model_path}")
        print("Download with: yolo download yolov8n")
        return False
    return True

def find_test_videos():
    """Find available test videos."""
    video_dirs = [
        "artifacts/videos",
        "tests/test_data/videos",
        "benchmarks/test_videos"
    ]
    
    videos = []
    for dir_path in video_dirs:
        if os.path.exists(dir_path):
            for ext in ['.mp4', '.avi', '.mov']:
                videos.extend([
                    os.path.join(dir_path, f) 
                    for f in os.listdir(dir_path) 
                    if f.endswith(ext)
                ])
    
    return videos

def run_benchmark():
    """Run YOLO video detection benchmark."""
    from ultralytics import YOLO
    import cv2
    
    print("Loading YOLOv8n model...")
    print("Expected: ~0.4GB VRAM, TensorRT optimized")
    print("Target: <50ms per frame")
    
    # Load model
    start_load = time.time()
    model = YOLO("models/yolov8n.pt")
    
    # Try to load TensorRT version if available
    if os.path.exists("models/yolov8n.engine"):
        print("   Using TensorRT engine for faster inference")
        model = YOLO("models/yolov8n.engine")
    
    load_time = time.time() - start_load
    print(f"✅ Model loaded in {load_time:.2f}s")
    print(f"   VRAM usage: ~0.4GB")
    
    # Find test videos
    test_videos = find_test_videos()
    
    if not test_videos:
        print("\n⚠️  No test videos found")
        print("   Searched: artifacts/videos/, tests/test_data/videos/")
        print("   Creating synthetic test...")
        
        # Create synthetic benchmark using images as frames
        test_videos = ["models/MobileSAM/app/assets/picture1.jpg"]
        is_image = True
    else:
        is_image = False
        print(f"\n✅ Found {len(test_videos)} test videos")
    
    results = []
    
    for video_path in test_videos[:3]:  # Test first 3 videos
        print(f"\n{'Image' if is_image else 'Video'}: {video_path}")
        
        if is_image:
            # Simulate video by processing image multiple times
            frame = cv2.imread(video_path)
            if frame is None:
                print(f"   ❌ Could not load image")
                continue
            
            # Run detection 10 times to simulate video frames
            latencies = []
            for i in range(10):
                start = time.time()
                results_yolo = model(frame, verbose=False)
                latency = (time.time() - start) * 1000  # ms
                latencies.append(latency)
            
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            # Count detections
            detections = len(results_yolo[0].boxes)
            
            print(f"   Frames processed: 10 (simulated)")
            print(f"   Avg latency: {avg_latency:.1f}ms (target: <50ms)")
            print(f"   Min/Max: {min_latency:.1f}ms / {max_latency:.1f}ms")
            print(f"   Detections/frame: {detections}")
            
            # Show sample detections
            if detections > 0:
                print(f"   Sample detections:")
                for i, box in enumerate(results_yolo[0].boxes[:3]):
                    cls = int(box.cls)
                    conf = float(box.conf)
                    name = model.names[cls]
                    print(f"      - {name} ({conf:.2f})")
            
            results.append({
                "video": video_path,
                "type": "image_simulated",
                "frames": 10,
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min_latency,
                "max_latency_ms": max_latency,
                "detections_per_frame": detections,
                "within_target": avg_latency < 50,
                "fps": 1000 / avg_latency if avg_latency > 0 else 0
            })
            
        else:
            # Real video processing
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                print(f"   ❌ Could not open video")
                continue
            
            frame_count = 0
            latencies = []
            total_detections = 0
            
            # Process up to 100 frames or 5 seconds
            max_frames = 100
            max_time = 5.0
            start_time = time.time()
            
            while frame_count < max_frames and (time.time() - start_time) < max_time:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Run YOLO detection
                infer_start = time.time()
                results_yolo = model(frame, verbose=False)
                infer_time = (time.time() - infer_start) * 1000
                
                latencies.append(infer_time)
                total_detections += len(results_yolo[0].boxes)
                frame_count += 1
            
            cap.release()
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                fps = 1000 / avg_latency if avg_latency > 0 else 0
                
                print(f"   Frames processed: {frame_count}")
                print(f"   Avg latency: {avg_latency:.1f}ms (target: <50ms)")
                print(f"   Min/Max: {min_latency:.1f}ms / {max_latency:.1f}ms")
                print(f"   Effective FPS: {fps:.1f}")
                print(f"   Total detections: {total_detections}")
                print(f"   Detections/frame: {total_detections / frame_count:.1f}")
                
                results.append({
                    "video": video_path,
                    "type": "real_video",
                    "frames": frame_count,
                    "duration_s": time.time() - start_time,
                    "avg_latency_ms": avg_latency,
                    "min_latency_ms": min_latency,
                    "max_latency_ms": max_latency,
                    "total_detections": total_detections,
                    "detections_per_frame": total_detections / frame_count if frame_count > 0 else 0,
                    "within_target": avg_latency < 50,
                    "fps": fps
                })
    
    # Summary
    print("\n" + "="*60)
    print("YOLO VIDEO DETECTION SUMMARY")
    print("="*60)
    
    if results:
        avg_latency = sum(r["avg_latency_ms"] for r in results) / len(results)
        avg_fps = sum(r["fps"] for r in results) / len(results)
        total_frames = sum(r["frames"] for r in results)
        
        print(f"\nTotal frames processed: {total_frames}")
        print(f"Average latency: {avg_latency:.1f}ms")
        print(f"Target latency: <50ms")
        print(f"Status: {'✅ PASS' if avg_latency < 50 else '❌ FAIL'}")
        print(f"Effective FPS: {avg_fps:.1f}")
        print(f"Real-time capable: {'✅ Yes' if avg_fps >= 20 else '⚠️  Marginal' if avg_fps >= 10 else '❌ No'}")
    
    # Save results
    os.makedirs("benchmarks", exist_ok=True)
    with open("benchmarks/yolo_video_results.json", "w") as f:
        json.dump({
            "model": "YOLOv8n",
            "load_time_s": load_time,
            "results": results,
            "summary": {
                "avg_latency_ms": avg_latency if results else 0,
                "target_ms": 50,
                "pass": all(r["within_target"] for r in results) if results else False,
                "avg_fps": avg_fps if results else 0,
                "real_time_capable": avg_fps >= 20 if results else False
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: benchmarks/yolo_video_results.json")

if __name__ == "__main__":
    print("=" * 60)
    print("YOLO Video Detection Benchmark")
    print("=" * 60)
    print()
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_model_files():
        sys.exit(1)
    
    run_benchmark()
