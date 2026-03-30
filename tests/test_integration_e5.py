"""Integration tests for OpenClaw/advanced-vision interaction.

These tests verify that external agents can call advanced-vision tools
via the expected interfaces (mcporter, subprocess, etc.).
"""

import json
import subprocess
from pathlib import Path

import pytest

# Skip mcporter-only tests unless the binary exists and this server is actually registered.
MCPorter_AVAILABLE = False
ADVANCED_VISION_REGISTERED = False
try:
    result = subprocess.run(["mcporter", "list"], capture_output=True, text=True, timeout=5)
    MCPorter_AVAILABLE = result.returncode == 0
    ADVANCED_VISION_REGISTERED = MCPorter_AVAILABLE and "advanced-vision" in result.stdout
except (subprocess.TimeoutExpired, FileNotFoundError):
    pass


# =============================================================================
# Phase E5: OpenClaw Integration Tests
# =============================================================================


@pytest.mark.skipif(not ADVANCED_VISION_REGISTERED, reason="advanced-vision not registered in mcporter")
def test_mcporter_screenshot_full():
    """E5.1: Call screenshot_full via mcporter."""
    result = subprocess.run(
        ["mcporter", "call", "advanced-vision.screenshot_full"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    
    assert result.returncode == 0, f"mcporter failed: {result.stderr}"
    
    output = json.loads(result.stdout)
    assert "path" in output
    assert "width" in output
    assert "height" in output
    assert Path(output["path"]).exists()


@pytest.mark.skipif(not ADVANCED_VISION_REGISTERED, reason="advanced-vision not registered in mcporter")
def test_mcporter_move_mouse_dry_run():
    """E5.2: Call move_mouse via mcporter with dry_run."""
    result = subprocess.run(
        ["mcporter", "call", "advanced-vision.move_mouse", "x=100", "y=200", "dry_run=true"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    
    assert result.returncode == 0
    
    output = json.loads(result.stdout)
    assert output["ok"] is True
    assert output["action_type"] == "move_mouse"
    assert "DRY RUN" in output["message"]


@pytest.mark.skipif(not ADVANCED_VISION_REGISTERED, reason="advanced-vision not registered in mcporter")
def test_mcporter_verify_screen_change():
    """E5.3: Call verify_screen_change via mcporter."""
    # First get a screenshot
    screenshot_result = subprocess.run(
        ["mcporter", "call", "advanced-vision.screenshot_full"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    
    screenshot = json.loads(screenshot_result.stdout)
    
    # Verify against itself (should be no change)
    result = subprocess.run(
        [
            "mcporter",
            "call",
            "advanced-vision.verify_screen_change",
            f"previous_screenshot_path={screenshot['path']}",
            f"current_screenshot_path={screenshot['path']}",
            "threshold=0.99",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    
    assert result.returncode == 0
    
    output = json.loads(result.stdout)
    assert "changed" in output
    assert "similarity" in output
    # Same image should have high similarity
    assert output["similarity"] is None or output["similarity"] > 0.99


# =============================================================================
# Phase E5: Python API Integration
# =============================================================================


def test_python_api_screenshot():
    """E5.4: Use Python API directly (no mcporter)."""
    from advanced_vision.tools import screenshot_full
    
    artifact = screenshot_full()
    
    assert artifact.path is not None
    assert artifact.width > 0
    assert artifact.height > 0
    assert Path(artifact.path).exists()


def test_python_api_action_workflow():
    """E5.5: Complete workflow via Python API."""
    from advanced_vision.tools import (
        screenshot_full,
        verify_screen_change,
    )
    
    # Before
    before = screenshot_full()
    
    # After (immediately, so minimal change)
    after = screenshot_full()
    
    # Verify
    result = verify_screen_change(before.path, after.path)
    
    assert result.changed is not None
    assert result.similarity is None or 0 <= result.similarity <= 1


def test_python_api_dry_run_safety():
    """E5.6: Verify dry_run doesn't execute actions."""
    from advanced_vision.tools import move_mouse, click, type_text
    
    # All should work without actually doing anything
    result1 = move_mouse(100, 100, dry_run=True)
    result2 = click(100, 100, dry_run=True)
    result3 = type_text("test", dry_run=True)
    
    assert result1.ok is True
    assert result2.ok is True
    assert result3.ok is True
    assert "DRY RUN" in result1.message
    assert "DRY RUN" in result2.message
    assert "DRY RUN" in result3.message


# =============================================================================
# Phase E5: Skill Manifest Validation
# =============================================================================


def test_skill_manifest_exists():
    """E5.7: Verify skill_manifest.json exists and is valid JSON."""
    from advanced_vision.config import get_settings
    
    settings = get_settings()
    manifest_path = settings.repo_root / "skill_manifest.json"
    
    assert manifest_path.exists(), "skill_manifest.json not found"
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    assert "name" in manifest
    assert manifest["name"] == "advanced-vision"
    assert "tools" in manifest
    assert len(manifest["tools"]) > 0


def test_skill_manifest_tool_definitions():
    """E5.8: Verify all tools are documented in manifest."""
    from advanced_vision.config import get_settings
    
    settings = get_settings()
    manifest_path = settings.repo_root / "skill_manifest.json"
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    tool_names = {tool["name"] for tool in manifest["tools"]}
    
    # Core tools should be documented
    assert "screenshot_full" in tool_names
    assert "move_mouse" in tool_names
    assert "click" in tool_names
    assert "verify_screen_change" in tool_names


# =============================================================================
# Phase E5: Error Handling
# =============================================================================


@pytest.mark.skipif(not ADVANCED_VISION_REGISTERED, reason="advanced-vision not registered in mcporter")
def test_mcporter_invalid_tool():
    """E5.9: mcporter returns error for invalid tool."""
    result = subprocess.run(
        ["mcporter", "call", "advanced-vision.invalid_tool"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    
    # Should fail gracefully
    assert result.returncode != 0 or "error" in result.stdout.lower()


def test_python_api_invalid_coordinates():
    """E5.10: Python API handles invalid coordinates gracefully."""
    from advanced_vision.tools import move_mouse
    
    # Negative coordinates should still work (pyautogui handles it)
    result = move_mouse(-100, -100, dry_run=True)
    
    # Should not crash, just report in dry_run
    assert result.ok is True


# =============================================================================
# Phase E5: Documentation Tests
# =============================================================================


def test_usage_documentation_exists():
    """E5.11: Verify USAGE.md documentation exists."""
    from advanced_vision.config import get_settings
    
    settings = get_settings()
    usage_path = settings.repo_root / "docs" / "USAGE.md"
    
    assert usage_path.exists(), "docs/USAGE.md not found"
    
    content = usage_path.read_text()
    assert "screenshot" in content.lower()
    assert "dry_run" in content.lower()


def test_execution_plan_exists():
    """E5.12: Verify the execution plan doc exists."""
    from advanced_vision.config import get_settings
    
    settings = get_settings()
    plan_path = settings.repo_root / "docs" / "roadmap" / "execution-plan.md"
    
    assert plan_path.exists(), "docs/roadmap/execution-plan.md not found"


# =============================================================================
# Phase E5: End-to-End Integration
# =============================================================================


@pytest.mark.skipif(not ADVANCED_VISION_REGISTERED, reason="advanced-vision not registered in mcporter")
def test_end_to_end_screenshot_and_verify():
    """E5.13: Complete workflow via mcporter.
    
    1. Screenshot
    2. Move mouse (dry_run)
    3. Verify change (against same screenshot)
    """
    # Screenshot
    screenshot_result = subprocess.run(
        ["mcporter", "call", "advanced-vision.screenshot_full"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    screenshot = json.loads(screenshot_result.stdout)
    
    # Move mouse (dry run)
    move_result = subprocess.run(
        ["mcporter", "call", "advanced-vision.move_mouse", "x=500", "y=500", "dry_run=true"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    move_output = json.loads(move_result.stdout)
    
    # Verify
    verify_result = subprocess.run(
        [
            "mcporter",
            "call",
            "advanced-vision.verify_screen_change",
            f"previous_screenshot_path={screenshot['path']}",
            "threshold=0.95",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    verify_output = json.loads(verify_result.stdout)
    
    # All should succeed
    assert screenshot_result.returncode == 0
    assert move_result.returncode == 0
    assert verify_result.returncode == 0
    assert move_output["ok"] is True
    assert "changed" in verify_output
