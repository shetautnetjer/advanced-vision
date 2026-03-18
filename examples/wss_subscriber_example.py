#!/usr/bin/env python3
"""Example usage of WSSAgentSubscriber for OpenClaw agents.

This script demonstrates how to use the WebSocket subscriber to receive
vision feeds from various services.
"""

import time
from typing import Dict, Any

from advanced_vision.wss_agent_subscriber import (
    WSSAgentSubscriber,
    subscribe_to_feed,
    FeedPort,
)


def handle_pattern(message: Dict[str, Any]) -> None:
    """Handle trading pattern detection."""
    print(f"🎯 Pattern detected: {message.get('pattern', 'unknown')}")
    if 'confidence' in message:
        print(f"   Confidence: {message['confidence']:.2f}")


def handle_segmentation(message: Dict[str, Any]) -> None:
    """Handle SAM segmentation results."""
    print(f"🔍 Segmentation: {message.get('regions', 0)} regions detected")


def handle_detection(message: Dict[str, Any]) -> None:
    """Handle YOLO object detection."""
    objects = message.get('objects', [])
    print(f"📦 Objects detected: {len(objects)}")
    for obj in objects:
        print(f"   - {obj.get('class', 'unknown')}: {obj.get('confidence', 0):.2f}")


def handle_analysis(message: Dict[str, Any]) -> None:
    """Handle analysis results."""
    print(f"🧠 Analysis: {message.get('summary', 'N/A')}")


def global_handler(port: int, message: Dict[str, Any]) -> None:
    """Global handler receives all messages from all feeds."""
    feed_names = {
        8002: "YOLO",
        8003: "SAM", 
        8004: "Eagle",
        8005: "Analysis"
    }
    feed = feed_names.get(port, f"Port {port}")
    print(f"[GLOBAL] {feed}: {message.get('type', 'message')}")


def example_multiple_feeds():
    """Example: Subscribe to multiple feeds with different schemas."""
    print("=== Example: Multiple Feeds ===\n")
    
    subscriber = WSSAgentSubscriber()
    
    # Trading agent - subscribe to Eagle classifications (trading schema only)
    subscriber.subscribe(
        FeedPort.EAGLE.value,
        schema="trading",
        callback=handle_pattern
    )
    
    # Navigation agent - subscribe to YOLO detections (ui schema only)
    subscriber.subscribe(
        FeedPort.YOLO.value,
        schema="ui",
        callback=handle_detection
    )
    
    # General agent - subscribe to SAM (both schemas)
    subscriber.subscribe(
        FeedPort.SAM.value,
        schema="both",
        callback=handle_segmentation
    )
    
    # Add global callback for all messages
    subscriber.add_global_callback(global_handler)
    
    # Start subscriber (non-blocking)
    subscriber.start()
    
    print("Subscriber running. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            time.sleep(1)
            # Print statistics every 10 seconds
            stats = subscriber.get_statistics()
            print(f"Stats: {stats['total_messages']} messages, "
                  f"{stats['total_errors']} errors")
    except KeyboardInterrupt:
        print("\nStopping...")
        subscriber.stop()


def example_quick_start():
    """Example: Quick start with subscribe_to_feed helper."""
    print("=== Example: Quick Start ===\n")
    
    # Single feed subscription
    subscriber = subscribe_to_feed(
        port=8004,
        schema="trading",
        callback=handle_pattern
    )
    
    print("Quick subscriber running. Press Ctrl+C to stop.\n")
    
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        subscriber.stop()


def example_ring_buffer():
    """Example: Using the ring buffer for recent frames."""
    print("=== Example: Ring Buffer ===\n")
    
    subscriber = WSSAgentSubscriber(buffer_size=50)
    
    # Subscribe without callback - we'll poll the buffer
    subscriber.subscribe(FeedPort.ANALYSIS.value, schema="both")
    subscriber.subscribe(FeedPort.EAGLE.value, schema="trading")
    
    subscriber.start()
    
    print("Collecting messages for 5 seconds...\n")
    time.sleep(5)
    
    # Get recent messages from buffer
    recent = subscriber.get_recent_messages(count=10)
    print(f"Recent messages ({len(recent)}):")
    for msg in recent:
        print(f"  [{msg.get('feed', '?')}] {msg}")
    
    subscriber.stop()


def example_event_filtering():
    """Example: Event filtering for specific conditions."""
    print("=== Example: Event Filtering ===\n")
    
    subscriber = WSSAgentSubscriber()
    
    # Add a filter - only process high-confidence patterns
    def high_confidence_filter(msg: Dict[str, Any]) -> bool:
        confidence = msg.get('confidence', 0)
        return confidence > 0.8
    
    subscriber.add_event_filter("pattern", high_confidence_filter)
    
    subscriber.subscribe(
        FeedPort.EAGLE.value,
        schema="trading",
        callback=handle_pattern
    )
    
    subscriber.start()
    
    print("Filtering for high-confidence patterns. Press Ctrl+C to stop.\n")
    
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        subscriber.stop()


if __name__ == "__main__":
    import sys
    
    examples = {
        "multiple": example_multiple_feeds,
        "quick": example_quick_start,
        "buffer": example_ring_buffer,
        "filter": example_event_filtering,
    }
    
    if len(sys.argv) < 2 or sys.argv[1] not in examples:
        print("Usage: python wss_subscriber_example.py <example>")
        print(f"\nAvailable examples: {', '.join(examples.keys())}")
        print("\nExamples:")
        print("  multiple  - Subscribe to multiple feeds with different schemas")
        print("  quick     - Quick start with single feed")
        print("  buffer    - Demonstrate ring buffer usage")
        print("  filter    - Event filtering demonstration")
        sys.exit(1)
    
    examples[sys.argv[1]]()
