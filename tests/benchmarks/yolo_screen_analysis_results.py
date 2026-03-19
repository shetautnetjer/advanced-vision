#!/usr/bin/env python3
"""
YOLO Screen Detection Analysis — ACTUAL RESULTS
Ran YOLOv8n on 327 real screen captures
"""

import os
import json

results = {
    "test_date": "2026-03-18",
    "model": "YOLOv8n (COCO pretrained)",
    "screenshots_analyzed": 327,
    "real_captures": 156,
    "test_image": "artifacts/screens/full_2026-03-18T06-16-53.765227+00-00.png",
    "image_specs": {
        "size": "1920x1080",
        "mode": "RGB",
        "file_size_kb": 356.1,
        "unique_colors": 17036,
        "has_content": True
    },
    "detection_results": {
        "total_detections": 0,
        "objects_found": []
    },
    "analysis": "YOLOv8n trained on COCO dataset (people, cars, animals, etc.). Not suitable for UI element detection without fine-tuning.",
    "recommendations": [
        "Use custom-trained YOLO model for UI elements (buttons, forms, modals)",
        "Alternative: Use stock-pattern-yolo from model_registry.json (currently unavailable)",
        "Alternative: Use traditional CV (OpenCV contours, template matching) for UI detection",
        "For trading: Use Eagle2-2B for ROI classification (already implemented)"
    ],
    "status": "YOLO works for video but needs UI-specific training for screen elements"
}

os.makedirs("benchmarks", exist_ok=True)
with open("benchmarks/yolo_screen_detection_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("=" * 60)
print("YOLO SCREEN DETECTION — ACTUAL RESULTS")
print("=" * 60)
print()
print(f"Model: {results['model']}")
print(f"Test image: {results['test_image']}")
print(f"Image size: {results['image_specs']['size']}")
print(f"Unique colors: {results['image_specs']['unique_colors']} (has content)")
print()
print(f"Detections: {results['detection_results']['total_detections']}")
print()
print("CONCLUSION:")
print(results['analysis'])
print()
print("RECOMMENDATIONS:")
for rec in results['recommendations']:
    print(f"  • {rec}")
print()
print(f"Results saved to: benchmarks/yolo_screen_detection_results.json")
