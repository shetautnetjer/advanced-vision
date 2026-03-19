# Pipeline Latency Benchmark Documentation

**Location:** `tests/benchmarks/test_pipeline_latency.py`  
**Output:** `benchmarks/pipeline_latency.json`  
**Last Updated:** 2026-03-18

---

## Overview

This benchmark suite measures the end-to-end latency of the Advanced Vision pipeline:

```
Capture → YOLO → Eagle → Governor → TruthWriter → WSS
```

**Target Performance:** <5 seconds total pipeline latency

---

## Running Benchmarks

### Run All Benchmarks
```bash
pytest tests/benchmarks/test_pipeline_latency.py -v
```

### Run Specific Category
```bash
# Hot path tests only
pytest tests/benchmarks/test_pipeline_latency.py -v -m "hot_path"

# Stage breakdown only
pytest tests/benchmarks/test_pipeline_latency.py -v -m "stage_breakdown"

# Load tests (slower)
pytest tests/benchmarks/test_pipeline_latency.py -v -m "load_test"

# Memory profiling
pytest tests/benchmarks/test_pipeline_latency.py -v -m "memory"

# Governor overhead
pytest tests/benchmarks/test_pipeline_latency.py -v -m "governor"
```

### Run with Report Generation
```bash
pytest tests/benchmarks/test_pipeline_latency.py -v --benchmark-save=pipeline
```

### Run from Project Root
```bash
cd /home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision
python -m pytest tests/benchmarks/test_pipeline_latency.py -v
```

---

## Benchmark Categories

### 1. Full Hot Path Timing

**Test Class:** `TestFullHotPathTiming`

Measures the complete pipeline execution time from frame capture to WSS publish.

| Test | Description | Target |
|------|-------------|--------|
| `test_full_pipeline_latency_target` | Single run latency | <5000ms |
| `test_full_pipeline_statistics` | Mean/P95/P99 over N runs | Mean <5000ms, P95 <6000ms |
| `test_pipeline_consistency` | Coefficient of variation | CV <0.3 (30%) |

**Pipeline Stages Measured:**
1. **Capture** - Frame capture and initialization
2. **YOLO Detection** - Object detection (<50ms target)
3. **Eagle Classification** - ROI classification (300-500ms target)
4. **Governor Evaluation** - Policy evaluation (<100ms target)
5. **TruthWriter** - Event logging (<10ms target)
6. **WSS Publish** - WebSocket publish (~0.1ms estimated)

---

### 2. Stage Breakdown

**Test Class:** `TestStageBreakdown`

Measures individual stage latencies to identify bottlenecks.

| Stage | Expected Latency | Measured By |
|-------|------------------|-------------|
| Capture | <50ms | `test_capture_stage_latency` |
| YOLO Detection | <50ms | `test_yolo_detection_latency` |
| Eagle Classification | 300-500ms | `test_eagle_classification_latency` |
| Governor Evaluation | <100ms | `test_governor_evaluation_latency` |
| TruthWriter | <10ms | `test_truth_writer_latency` |

**Output Statistics:**
- Min/Max latency
- Mean/Median latency
- P95/P99 percentiles
- Standard deviation

---

### 3. Load Testing

**Test Class:** `TestLoadTesting`

Measures pipeline behavior under sustained and burst load.

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_sustained_load_1fps` | 1 frame/sec for 10 seconds | Throughput ≥0.9 FPS, Degradation <20% |
| `test_burst_load_5frames` | Burst of 5 frames | Burst overhead <50% |
| `test_success_rate_under_load` | 20 iterations | Success rate ≥95% |

**Metrics:**
- Throughput (FPS)
- Latency degradation over time
- Success rate
- Burst overhead

---

### 4. Memory Profiling

**Test Class:** `TestMemoryProfiling`

Profiles memory usage throughout pipeline execution.

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_memory_per_stage` | VRAM usage per stage | Monitors growth |
| `test_memory_stability` | Memory over 10 runs | Growth <20% |
| `test_gc_impact` | Garbage collection overhead | GC impact <100ms |

**Requirements:**
- `pynvml` for GPU memory monitoring (optional)
- `psutil` for system memory monitoring

---

### 5. Governor Overhead

**Test Class:** `TestGovernorOverhead`

Measures the enforcement cost of the Governor system.

| Test | Description | Target |
|------|-------------|--------|
| `test_governor_overhead_measurement` | Pipeline with/without Governor | <5% overhead |
| `test_verdict_routing_latency` | Different verdict types | Similar latency (<2x) |

**Overhead Calculation:**
```
overhead_ms = mean_with_governor - mean_without_governor
overhead_pct = (overhead_ms / mean_without_governor) * 100
```

---

## Output Format

### JSON Report Structure

```json
{
  "timestamp": "2026-03-18T17:30:00Z",
  "target_latency_ms": 5000,
  "target_governor_overhead_pct": 5.0,
  "results": [
    {
      "benchmark_name": "full_hot_path_statistics",
      "total_duration_ms": 2345.67,
      "stage_latencies": {
        "capture": {
          "stage_name": "capture",
          "min_ms": 5.2,
          "max_ms": 12.5,
          "mean_ms": 8.1,
          "p95_ms": 11.2
        }
      },
      "memory_snapshots": [...],
      "throughput_fps": 2.5,
      "success_rate": 1.0,
      "governor_overhead_pct": 2.3
    }
  ],
  "bottlenecks": [
    {
      "benchmark": "stage_yolo_detection",
      "stage": "yolo_detection",
      "issue": "Stage latency high: 650ms",
      "severity": "high"
    }
  ],
  "recommendations": [
    "Optimize slow stages: yolo_detection",
    "Consider model quantization"
  ]
}
```

---

## Identifying Bottlenecks

### High Severity Bottlenecks
- **Total latency exceeds target** (>5000ms)
- **Stage latency >1000ms**

### Medium Severity Bottlenecks
- **Stage latency >500ms**
- **Governor overhead >5%**
- **Memory growth >20%**

### Low Severity Bottlenecks
- **P95 latency >120% of target**
- **Throughput degradation >20%**

---

## Performance Targets Reference

From [MODEL_CAPABILITIES.md](docs/MODEL_CAPABILITIES.md):

| Model | Role | Expected Latency | VRAM |
|-------|------|------------------|------|
| YOLOv8n | Detection | <50ms | 0.4GB |
| Eagle2-2B | Scout | 300-500ms | 3.2GB |
| MobileSAM | Segmentation | 12ms | 0.5GB |
| Governor | Policy | <100ms | - |
| TruthWriter | Logging | <10ms | - |

---

## Troubleshooting

### Tests Failing Due to High Latency

1. **Check model loading:** Ensure models are loaded and warm
2. **GPU utilization:** Verify GPU is being used (not CPU fallback)
3. **System load:** Run benchmarks on idle system
4. **Dry run mode:** Some stages run in dry_run mode for safety

### GPU Memory Not Available

If `pynvml` is not installed:
```bash
pip install nvidia-ml-py3
```

The benchmarks will fall back to system memory monitoring via `psutil`.

### WSS Publishing

WSS publishing is mocked in benchmarks since a live WebSocket server is not required for latency measurement. The WSS stage is estimated at ~0.1ms.

---

## Continuous Integration

To add to CI pipeline:

```yaml
# .github/workflows/benchmark.yml
- name: Run Pipeline Benchmarks
  run: |
    pytest tests/benchmarks/test_pipeline_latency.py \
      -v \
      -m "not slow" \
      --tb=short

- name: Upload Benchmark Results
  uses: actions/upload-artifact@v3
  with:
    name: benchmark-results
    path: benchmarks/pipeline_latency.json
```

---

## Historical Performance

| Date | Mean Latency | P95 Latency | Status |
|------|--------------|-------------|--------|
| 2026-03-18 | TBD | TBD | 🔄 Initial |

*Update this table after each benchmark run.*

---

## Related Documentation

- [Model Capabilities](docs/MODEL_CAPABILITIES.md) - Model performance specifications
- [Governed Pipeline](src/advanced_vision/trading/governed_pipeline.py) - Pipeline implementation
- [Architecture](ARCHITECTURE.md) - System architecture overview
