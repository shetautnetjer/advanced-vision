#!/usr/bin/bash
# End-to-End Integration Test Runner for Advanced Vision Pipeline
#
# Usage:
#   ./scripts/run_e2e_tests.sh           # Run all e2e tests
#   ./scripts/run_e2e_tests.sh --live    # Run with actual models (requires GPU)
#   ./scripts/run_e2e_tests.sh --quick   # Run quick smoke tests only
#   ./scripts/run_e2e_tests.sh --perf    # Run performance benchmarks
#
# Environment:
#   RTX 5070 Ti with 16GB VRAM
#   Models: YOLO, Eagle2, Qwen (NVFP4), MobileSAM

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS_DIR="${PROJECT_ROOT}/tests"
LOGS_DIR="${PROJECT_ROOT}/logs/e2e"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts/e2e"
VENV_PATH="${PROJECT_ROOT}/.venv"

# Performance targets (ms)
YOLO_TARGET=50
EAGLE_TARGET=1000
QWEN_TARGET=3000
TOTAL_TARGET=5000

# Parse arguments
DRY_RUN=true
QUICK_MODE=false
PERF_MODE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --live)
      DRY_RUN=false
      shift
      ;;
    --quick)
      QUICK_MODE=true
      shift
      ;;
    --perf)
      PERF_MODE=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --live      Run with actual models (requires GPU + downloaded models)"
      echo "  --quick     Run quick smoke tests only"
      echo "  --perf      Run performance benchmarks"
      echo "  --verbose   Verbose output"
      echo "  --help      Show this help"
      echo ""
      echo "Examples:"
      echo "  $0                    # Dry-run mode (safe, no GPU needed)"
      echo "  $0 --live             # Live mode with actual models"
      echo "  $0 --quick            # Quick smoke tests"
      echo "  $0 --live --perf      # Live performance benchmarks"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[FAIL]${NC} $1"
}

log_section() {
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}  $1${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

# Check Python environment
check_environment() {
  log_section "Environment Check"
  
  if [[ ! -d "$VENV_PATH" ]]; then
    log_error "Virtual environment not found at $VENV_PATH"
    log_info "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
  fi
  
  # Activate venv
  source "${VENV_PATH}/bin/activate"
  
  # Check Python version
  PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
  log_info "Python version: $PYTHON_VERSION"
  
  # Check if pytest is available
  if ! command -v pytest &> /dev/null; then
    log_error "pytest not found. Install with: pip install pytest"
    exit 1
  fi
  
  # Check GPU if running live
  if [[ "$DRY_RUN" == "false" ]]; then
    log_info "Live mode - checking GPU..."
    if ! command -v nvidia-smi &> /dev/null; then
      log_error "nvidia-smi not found. GPU required for live mode."
      exit 1
    fi
    
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)
    log_info "GPU: $GPU_INFO"
    
    # Check available VRAM
    VRAM_AVAILABLE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1 | tr -d ' ')
    if [[ ${VRAM_AVAILABLE%.*} -lt 8000 ]]; then
      log_warn "Available VRAM is low: ${VRAM_AVAILABLE}MB (recommended: 8000MB+)"
    else
      log_info "Available VRAM: ${VRAM_AVAILABLE}MB ✓"
    fi
  else
    log_info "Dry-run mode - no GPU required"
  fi
  
  log_success "Environment check passed"
}

# Setup test directories
setup_directories() {
  log_section "Setup"
  
  mkdir -p "$LOGS_DIR"
  mkdir -p "$ARTIFACTS_DIR"
  
  log_info "Log directory: $LOGS_DIR"
  log_info "Artifacts directory: $ARTIFACTS_DIR"
  
  # Clean old logs (keep last 10)
  if [[ -d "$LOGS_DIR" ]]; then
    ls -t "$LOGS_DIR"/*.jsonl 2>/dev/null | tail -n +11 | xargs -r rm -f
  fi
  
  log_success "Directories ready"
}

# Check models are downloaded (for live mode)
check_models() {
  if [[ "$DRY_RUN" == "true" ]]; then
    return 0
  fi
  
  log_section "Model Check"
  
  MODELS_DIR="${PROJECT_ROOT}/models"
  REQUIRED_MODELS=("Qwen3.5-2B-NVFP4" "Eagle2-2B" "MobileSAM")
  
  MISSING=()
  for model in "${REQUIRED_MODELS[@]}"; do
    if [[ ! -d "${MODELS_DIR}/${model}" ]]; then
      MISSING+=("$model")
    fi
  done
  
  if [[ ${#MISSING[@]} -gt 0 ]]; then
    log_error "Missing models: ${MISSING[*]}"
    log_info "Download models with: python scripts/download_model.py <model_name>"
    exit 1
  fi
  
  log_success "All required models present"
}

# Run e2e tests
run_tests() {
  log_section "Running E2E Tests"
  
  cd "$PROJECT_ROOT"
  source "${VENV_PATH}/bin/activate"
  
  # Build pytest arguments
  PYTEST_ARGS=(
    "-v"
    "--tb=short"
    "-m" "e2e"
    "-p" "no:warnings"
  )
  
  if [[ "$QUICK_MODE" == "true" ]]; then
    log_info "Quick mode - running smoke tests only"
    PYTEST_ARGS+=("-k" "TestBasicFlow")
  elif [[ "$PERF_MODE" == "true" ]]; then
    log_info "Performance mode - running benchmarks"
    PYTEST_ARGS+=("-m" "performance")
  fi
  
  if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_ARGS+=("-s" "--log-cli-level=INFO")
  fi
  
  # Set environment variables
  export ADVANCED_VISION_E2E=1
  if [[ "$DRY_RUN" == "true" ]]; then
    export ADVANCED_VISION_DRY_RUN=1
  else
    export ADVANCED_VISION_DRY_RUN=0
  fi
  
  # Run tests
  log_info "Running: pytest ${PYTEST_ARGS[*]} tests/test_e2e_pipeline.py"
  
  if pytest "${PYTEST_ARGS[@]}" tests/test_e2e_pipeline.py; then
    TEST_STATUS=0
  else
    TEST_STATUS=1
  fi
  
  return $TEST_STATUS
}

# Analyze test results
analyze_results() {
  log_section "Results Analysis"
  
  # Find latest log file
  LATEST_LOG=$(ls -t "$LOGS_DIR"/*.jsonl 2>/dev/null | head -n1)
  
  if [[ -z "$LATEST_LOG" ]]; then
    log_warn "No log files found"
    return 0
  fi
  
  log_info "Analyzing: $(basename "$LATEST_LOG")"
  
  # Count test scenarios
  SCENARIO_COUNT=$(grep -c "test_scenario" "$LATEST_LOG" 2>/dev/null || echo "0")
  log_info "Test scenarios logged: $SCENARIO_COUNT"
  
  # Check for failures
  FAILURES=$(grep -c '"passed": false' "$LATEST_LOG" 2>/dev/null || echo "0")
  if [[ "$FAILURES" -gt 0 ]]; then
    log_warn "Failed stages: $FAILURES"
    grep '"passed": false' "$LATEST_LOG" | head -5
  else
    log_success "All logged stages passed"
  fi
  
  # Performance summary (if available)
  if grep -q "total_latency_ms" "$LATEST_LOG"; then
    log_info "Performance summary:"
    grep "total_latency_ms" "$LATEST_LOG" | while read line; do
      echo "  $line"
    done
  fi
}

# Generate report
generate_report() {
  log_section "Test Report"
  
  REPORT_FILE="${LOGS_DIR}/e2e_report_$(date +%Y%m%d_%H%M%S).txt"
  
  cat > "$REPORT_FILE" << EOF
Advanced Vision E2E Test Report
================================
Date: $(date)
Mode: $([[ "$DRY_RUN" == "true" ]] && echo "Dry-run" || echo "Live")
Configuration:
  - YOLO target: ${YOLO_TARGET}ms
  - Eagle target: ${EAGLE_TARGET}ms
  - Qwen target: ${QWEN_TARGET}ms
  - Total target: ${TOTAL_TARGET}ms

Environment:
  - Python: $(python3 --version)
  - GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "N/A")

Logs: ${LOGS_DIR}
Artifacts: ${ARTIFACTS_DIR}

Test Scenarios:
  1. Basic Flow (Chart Detection)
  2. UI Navigation (Button Detection)
  3. Trading Pattern (SAM Refinement)
  4. Noise Filter (Cursor Discard)
EOF

  log_info "Report saved: $REPORT_FILE"
  cat "$REPORT_FILE"
}

# Cleanup
cleanup() {
  log_section "Cleanup"
  
  # Archive old artifacts
  if [[ -d "$ARTIFACTS_DIR" ]]; then
    ARCHIVE_COUNT=$(find "$ARTIFACTS_DIR" -type f -mtime +7 | wc -l)
    if [[ "$ARCHIVE_COUNT" -gt 0 ]]; then
      log_info "Archiving $ARCHIVE_COUNT old artifacts"
      # Could move to archive directory here
    fi
  fi
  
  log_success "Cleanup complete"
}

# ============================================================================
# Main
# ============================================================================

main() {
  echo ""
  echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║       Advanced Vision - E2E Integration Tests                 ║${NC}"
  echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  
  if [[ "$DRY_RUN" == "false" ]]; then
    echo -e "${YELLOW}⚠ LIVE MODE - Will use actual GPU models${NC}"
    echo ""
  fi
  
  # Run phases
  check_environment
  setup_directories
  check_models
  
  if run_tests; then
    TEST_STATUS=0
    echo ""
    log_success "All E2E tests passed!"
  else
    TEST_STATUS=1
    echo ""
    log_error "Some E2E tests failed"
  fi
  
  analyze_results
  generate_report
  cleanup
  
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  if [[ "$TEST_STATUS" -eq 0 ]]; then
    echo -e "${GREEN}  E2E Tests: PASSED${NC}"
  else
    echo -e "${RED}  E2E Tests: FAILED${NC}"
  fi
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo ""
  
  exit $TEST_STATUS
}

# Trap to ensure cleanup on exit
trap 'echo ""; log_warn "Interrupted"; exit 130' INT TERM

# Run main
main "$@"
