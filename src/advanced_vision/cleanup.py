#!/usr/bin/env python3
"""
Screenshot Retention Policy
Deletes screenshots after 76 hours (3 days + 4 hours)
Keeps screenshots tagged as 'error', 'issue', or 'data' indefinitely
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

SCREENSHOT_DIR = Path.home() / ".openclaw/workspace/plane-a/projects/advanced-vision/artifacts/screens"
RETENTION_HOURS = 76  # ~3.17 days
KEEP_TAGS = ['error', 'issue', 'data', 'debug', 'evidence']


def parse_timestamp_from_filename(filename: str) -> datetime:
    """Extract timestamp from screenshot filename"""
    # Format: full_2026-03-17T01-05-18.816183+00-00.png
    try:
        # Remove extension and split
        name = filename.replace('.png', '')
        # Extract datetime part
        if '_' in name:
            parts = name.split('_', 1)
            if len(parts) > 1:
                ts_str = parts[1]
                # Parse: 2026-03-17T01-05-18.816183+00-00
                ts_str = ts_str.replace('-', ':', 2)  # Fix time separators
                ts_str = ts_str.replace('T', ' ')
                # Remove microseconds and timezone for parsing
                if '.' in ts_str:
                    ts_str = ts_str.split('.')[0]
                return datetime.fromisoformat(ts_str)
    except Exception as e:
        # Fallback to file mtime
        filepath = SCREENSHOT_DIR / filename
        if filepath.exists():
            mtime = filepath.stat().st_mtime
            return datetime.fromtimestamp(mtime)
    return datetime.now()


def should_keep_screenshot(filepath: Path) -> bool:
    """Check if screenshot should be kept (tagged as error/issue/data)"""
    # Check for companion metadata file
    metadata_file = filepath.with_suffix('.json')
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            tags = metadata.get('tags', [])
            for tag in tags:
                if tag.lower() in KEEP_TAGS:
                    return True
        except:
            pass
    
    # Check filename for tags
    filename_lower = filepath.name.lower()
    for tag in KEEP_TAGS:
        if tag in filename_lower:
            return True
    
    return False


def cleanup_screenshots(dry_run: bool = True) -> dict:
    """Clean up old screenshots based on retention policy"""
    if not SCREENSHOT_DIR.exists():
        return {"status": "no_screenshots_dir", "deleted": 0, "kept": 0}
    
    cutoff = datetime.now() - timedelta(hours=RETENTION_HOURS)
    deleted = 0
    kept = 0
    preserved = []
    removed = []
    
    for screenshot_file in SCREENSHOT_DIR.glob("*.png"):
        # Check if should be kept indefinitely
        if should_keep_screenshot(screenshot_file):
            kept += 1
            preserved.append(screenshot_file.name)
            continue
        
        # Check age
        try:
            file_time = parse_timestamp_from_filename(screenshot_file.name)
            if file_time < cutoff:
                # Delete screenshot and metadata
                if not dry_run:
                    screenshot_file.unlink()
                    metadata_file = screenshot_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                deleted += 1
                removed.append(screenshot_file.name)
            else:
                kept += 1
        except Exception as e:
            print(f"Error processing {screenshot_file}: {e}")
            kept += 1
    
    result = {
        "status": "dry_run" if dry_run else "executed",
        "retention_hours": RETENTION_HOURS,
        "cutoff": cutoff.isoformat(),
        "deleted": deleted,
        "kept": kept,
        "preserved_tags": KEEP_TAGS,
        "removed_files": removed[:10],  # First 10
        "preserved_files": preserved[:10],  # First 10
    }
    
    return result


def tag_screenshot(screenshot_path: str, tags: list) -> bool:
    """Tag a screenshot for preservation"""
    path = Path(screenshot_path)
    if not path.exists():
        return False
    
    metadata_file = path.with_suffix('.json')
    metadata = {}
    
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
        except:
            pass
    
    metadata['tags'] = list(set(metadata.get('tags', []) + tags))
    metadata['tagged_at'] = datetime.now().isoformat()
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Screenshot retention policy")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default is dry-run)")
    parser.add_argument("--tag", help="Tag a screenshot for preservation")
    parser.add_argument("--tags", nargs="+", default=['error'], help="Tags to apply")
    
    args = parser.parse_args()
    
    if args.tag:
        if tag_screenshot(args.tag, args.tags):
            print(f"✅ Tagged {args.tag} with: {args.tags}")
        else:
            print(f"❌ Could not tag {args.tag}")
    else:
        result = cleanup_screenshots(dry_run=not args.execute)
        print(json.dumps(result, indent=2))
        
        if not args.execute:
            print(f"\n⚠️  This was a DRY RUN. Use --execute to actually delete.")
            print(f"   Retention: {RETENTION_HOURS} hours (~3.2 days)")
            print(f"   Preserved tags: {KEEP_TAGS}")