# End-to-End Testing Guide

This guide explains how to run and interpret the E2E integration tests for the Advanced Vision pipeline.

## Overview

The E2E test harness verifies the complete pipeline:

```
Screenshot → YOLO Detection → Eagle Classification → Qwen Analysis → Log Write
                ↓                    ↓                      ↓
          (SAM Refinement)    (Noise Filter)        (Risk Assessment)
```

### Test Scenarios

| # | Scenario | Description | Expected Result |
|---|----------|-------------|-----------------|
| 1 | **Basic Flow** | Screenshot with chart → detect → classify → analyze → log | Trading log written |
| 2 | **UI Navigation** | Screenshot with buttons → detect → classify → log | UI log written |
| 3 | **Trading Pattern** | Pattern ROI → SAM refine → confirm → risk analysis | Risk-assessed log |
| 4 | **Noise Filter** | Cursor-only screenshot → classify as noise → discard | No log written |

## Quick Start

### Prerequisites

```bash
# Ensure virtual environment is set up
python3 -m venv .venv-computer-use
source .venv-computer-use/bin/activate
pip install -e ".[dev]"

# Verify installation
python -c "from advanced_vision.trading import DetectionPipeline; print('✓ Import OK')"
```

### Run Tests

```bash
# Run all E2E tests in dry-run mode (safe, no GPU needed)
./scripts/run_e2e_tests.sh

# Run with actual models (requires RTX 5070 Ti + downloaded models)
./scripts/run_e2e_tests.sh --live

# Quick smoke test only
./scripts/run_e2e_tests.sh --quick

# Performance benchmarks
./scripts/run_e2e_tests.sh --perf
```

### Run Individual Test Files

```bash
# All E2E tests
python -m pytest tests/test_e2e_pipeline.py -v

# Specific scenario
python -m pytest tests/test_e2e_pipeline.py::TestBasicFlow -v

# With live models
python -m pytest tests/test_e2e_pipeline.py --live -v

# Performance only
python -m pytest tests/test_e2e_pipeline.py -m performance -v
```

## Test Files

| File | Purpose |
|------|---------|
| `tests/test_e2e_pipeline.py` | Main E2E test scenarios |
| `tests/e2e_fixtures.py` | Shared fixtures and utilities |
| `scripts/run_e2e_tests.sh` | Test runner with setup/teardown |
| `logs/e2e/*.jsonl` | Test execution logs |

## Performance Targets (RTX 5070 Ti)

| Component | Target | Notes |
|-----------|--------|-------|
| YOLO Detection | < 50ms | Tripwire lane, always on |
| Eagle Classification | < 1s | Scout lane, UI classification |
| Qwen Analysis | < 3s | Reviewer lane, risk assessment |
| **Total Pipeline** | **< 5s** | End-to-end |

### VRAM Budget

```
RTX 5070 Ti 16GB
├── System Reserve:     2.0 GB
├── Resident Models:    8.0 GB (YOLO + Eagle2 + Qwen2B + MobileSAM)
├── On-Demand Max:     10.0 GB (SAM3 when needed)
└── Headroom:           6.0 GB (KV cache + buffers)
```

## Test Output

### Console Output

```
═══════════════════════════════════════════════════════════════
  Running E2E Tests
═══════════════════════════════════════════════════════════════
tests/test_e2e_pipeline.py::TestBasicFlow::test_basic_flow_chart_detection PASSED [ 25%]
tests/test_e2e_pipeline.py::TestUINavigation::test_ui_navigation_button_detection PASSED [ 50%]
tests/test_e2e_pipeline.py::TestTradingPattern::test_trading_pattern_with_sam_refinement PASSED [ 75%]
tests/test_e2e_pipeline.py::TestNoiseFilter::test_noise_filter_cursor_only PASSED [100%]

✅ Basic Flow passed in 145.32ms
   YOLO: 12.45ms, Eagle: 0.52ms, Qwen: 1.23ms
```

### Log Files

Logs are written to `logs/e2e/*.jsonl` in JSON Lines format:

```json
{"test_scenario": "basic_flow", "stage": "yolo_detection", "passed": true, "latency_ms": 12.45}
{"test_scenario": "basic_flow", "stage": "eagle_classification", "passed": true, "latency_ms": 0.52}
{"event_id": "e2e_abc123", "event_type": "chart_update", "risk_level": "low", "schema_type": "trading"}
```

## Schemas

### UI Schema

Used for general UI detection and navigation:

```json
{
  "event_id": "string",
  "timestamp": "ISO8601",
  "event_type": "ui_change",
  "source": "scout",
  "confidence": 0.0-1.0,
  "ui_elements": ["button", "dropdown"],
  "schema_type": "ui"
}
```

### Trading Schema

Used for trading-specific events with risk assessment:

```json
{
  "event_id": "string",
  "timestamp": "ISO8601",
  "event_type": "order_ticket|chart_update|...",
  "source": "reviewer",
  "confidence": 0.0-1.0,
  "risk_level": "none|low|medium|high|critical",
  "recommendation": "continue|note|warn|hold|pause",
  "reasoning": "string",
  "schema_type": "trading"
}
```

## Interpreting Results

### Success Criteria

All tests must pass:
1. **Detection**: YOLO detects expected elements
2. **Classification**: Eagle correctly classifies UI type
3. **Analysis**: Qwen provides risk assessment (trading schema)
4. **Logging**: Entry written to JSONL with correct schema
5. **Performance**: Latency within targets

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| YOLO timeout | Model not loaded | Check `models/` directory, run download script |
| VRAM error | Insufficient memory | Close other GPU apps, check `nvidia-smi` |
| Schema validation fail | Missing field | Check Pydantic model definitions |
| No log written | Permission error | Check `logs/e2e/` directory permissions |

### Dry-Run vs Live Mode

| Mode | Models | GPU | Use Case |
|------|--------|-----|----------|
| **Dry-run** | Stubbed | Not required | CI/CD, development, quick validation |
| **Live** | Real | RTX 5070 Ti required | Performance validation, pre-release testing |

To switch modes:

```python
# In test file or environment
USE_DRY_RUN = True   # Stub mode
USE_DRY_RUN = False  # Live mode
```

Or via environment variable:

```bash
export ADVANCED_VISION_DRY_RUN=0  # Enable live mode
./scripts/run_e2e_tests.sh --live
```

## Adding New Tests

### Example: New Test Scenario

```python
class TestMyNewScenario:
    """Test Scenario X: Description here."""
    
    def test_my_scenario(
        self,
        screenshot_generator: MockScreenshotGenerator,
        detection_pipeline: DetectionPipeline,
        log_verifier: LogVerifier,
        pipeline_timing: PipelineTiming,
    ) -> None:
        # 1. Generate test screenshot
        screenshot_path = screenshot_generator.generate_...()
        
        # 2. Start timing
        stage = pipeline_timing.start_stage("my_stage")
        
        # 3. Run pipeline stage
        result = detection_pipeline.process_frame(...)
        
        # 4. Complete timing
        stage.complete(passed=result is not None)
        
        # 5. Verify log
        log_verifier.write_entry({...})
        
        # 6. Assert
        assert result is not None, "Should detect something"
```

### Fixtures Available

| Fixture | Type | Description |
|---------|------|-------------|
| `screenshot_generator` | MockScreenshotGenerator | Creates synthetic UI screenshots |
| `detection_pipeline` | DetectionPipeline | YOLO-based detection |
| `reviewer_lane` | ReviewerLane | Qwen-based analysis |
| `roi_extractor` | ROIExtractor | SAM-based refinement |
| `log_verifier` | LogVerifier | JSONL verification |
| `pipeline_timing` | PipelineTiming | Performance tracking |

## Continuous Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: ./scripts/run_e2e_tests.sh --quick
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running E2E smoke tests..."
./scripts/run_e2e_tests.sh --quick || exit 1
```

## Troubleshooting

### Enable Verbose Output

```bash
./scripts/run_e2e_tests.sh --verbose
# or
pytest tests/test_e2e_pipeline.py -vvs --log-cli-level=DEBUG
```

### Check Logs

```bash
# Latest log
tail -f logs/e2e/*.jsonl | jq .

# Specific test
grep "test_scenario.*basic_flow" logs/e2e/*.jsonl | jq .
```

### Validate Models

```bash
# Check which models are available
python scripts/load_models.py status

# Verify model files
python scripts/verify_models.py
```

### Reset Environment

```bash
# Clean and rebuild
rm -rf logs/e2e artifacts/e2e
rm -rf tests/__pycache__ tests/.pytest_cache
./scripts/run_e2e_tests.sh
```

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - Pipeline architecture
- [Model setup archive](archive/model-setup-complete-2026-03.md) - Model installation
- [Trading implementation summary](trading/trading-implementation-summary.md) - Trading module details
- `pytest --help` - Pytest documentation
