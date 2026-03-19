#!/bin/bash
# Run All Model Capability Benchmarks
# Usage: ./scripts/run_benchmarks.sh

set -e

echo "=============================================="
echo "Advanced Vision Model Capability Benchmarks"
echo "=============================================="
echo

# Check if models are available
echo "Checking model availability..."
python3 -c "
import json
import os

with open('config/model_registry.json') as f:
    registry = json.load(f)

available = []
for model_id, info in registry['models'].items():
    if info.get('status') == 'available':
        path = info['files']['checkpoint']
        if os.path.exists(path):
            available.append(model_id)
        else:
            print(f'⚠️  {model_id}: configured but not downloaded')

print(f'\\nAvailable models: {available}')
"

echo
echo "=============================================="
echo "1. Eagle2-2B Classification Benchmark"
echo "=============================================="
echo "Tests: UI element detection, screen change classification"
echo "Target: 300-500ms inference"
echo
python3 tests/benchmarks/run_eagle2_benchmark.py || echo "⚠️  Eagle2 benchmark skipped (dependencies/models missing)"

echo
echo "=============================================="
echo "2. Qwen4B Reviewer Quality Benchmark"
echo "=============================================="
echo "Tests: Trading analysis, reasoning depth, comparison with Qwen2B"
echo "Target: 2-3s inference"
echo
python3 tests/benchmarks/run_qwen4b_benchmark.py || echo "⚠️  Qwen4B benchmark skipped (dependencies/models missing)"

echo
echo "=============================================="
echo "3. Pipeline Latency Benchmark"
echo "=============================================="
echo "Tests: Full hot path timing (Capture → YOLO → Eagle → Governor → WSS)"
echo "Target: <5s total"
echo
python3 tests/benchmarks/run_pipeline_benchmark.py || echo "⚠️  Pipeline benchmark skipped"

echo
echo "=============================================="
echo "Benchmark Summary"
echo "=============================================="
echo

# Display results
for result in benchmarks/*.json; do
    if [ -f "$result" ]; then
        echo "📊 $(basename $result):"
        python3 -c "
import json
with open('$result') as f:
    data = json.load(f)
    if 'summary' in data:
        for k, v in data['summary'].items():
            print(f'   {k}: {v}')
        " 2>/dev/null || cat "$result"
        echo
    fi
done

echo "=============================================="
echo "To install missing dependencies:"
echo "   pip install -r requirements.txt"
echo "=============================================="
