#!/bin/bash
# =============================================================================
# vLLM Model Server Launcher for Advanced Vision Trading Pipeline
# =============================================================================
# Usage: ./scripts/start_vllm.sh [model_name] [options]
# 
# CRITICAL RTX 5070 Ti FIXES (2026-03-17):
#   1. pip install nvidia-nccl-cu12==2.27.3 (fixes CUBLAS_STATUS_ALLOC_FAILED)
#   2. Environment variables for stable NVFP4:
#      export VLLM_NVFP4_GEMM_BACKEND=marlin
#      export VLLM_TEST_FORCE_FP8_MARLIN=1
#
# Examples:
#   ./scripts/start_vllm.sh qwen3.5-2b-nvfp4          # Start 2B scout model
#   ./scripts/start_vllm.sh qwen3.5-4b-nvfp4          # Start 4B reviewer model
#   ./scripts/start_vllm.sh --dry-run                 # Test configuration
#   ./scripts/start_vllm.sh --list-models             # List available models
# =============================================================================

set -e

# =============================================================================
# CRITICAL: RTX 5070 Ti Environment Setup
# =============================================================================

# NVFP4 Stable Settings (MUST be set before importing vLLM)
export VLLM_NVFP4_GEMM_BACKEND="marlin"
export VLLM_TEST_FORCE_FP8_MARLIN="1"

# MoE router/gate precision (keep in BF16, not FP4!)
export VLLM_MOE_ROUTER_PRECISION="bf16"

# CUDA settings
export CUDA_VISIBLE_DEVICES="0"

# NCCL fix for RTX 5070 Ti (upgrade from 2.26.2 to 2.27.3)
# Run: pip install nvidia-nccl-cu12==2.27.3
NCCL_MIN_VERSION="2.27.3"

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config/vllm.yaml"
REGISTRY_FILE="${PROJECT_ROOT}/config/model_registry.json"
MODELS_DIR="${PROJECT_ROOT}/models"
LOGS_DIR="${PROJECT_ROOT}/logs"

# Default values
MODEL_NAME="${1:-qwen3.5-2b-nvfp4}"
DRY_RUN=false
LIST_MODELS=false
DETACH=false
PORT=8000
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

show_help() {
    cat << 'EOF'
Usage: start_vllm.sh [MODEL_NAME] [OPTIONS]

Launch vLLM server with NVFP4 quantized models for trading pipeline.

CRITICAL RTX 5070 Ti Setup:
  1. pip install nvidia-nccl-cu12==2.27.3
  2. Environment variables are auto-set in this script

Models:
  qwen3.5-2b-nvfp4    Scout model - 2.5GB VRAM, quick analysis
  qwen3.5-4b-nvfp4    Reviewer model - 4.0GB VRAM, deep reasoning
  qwen3.5-7b-nvfp4    Expert model - 7.0GB VRAM (not downloaded)

Options:
  -h, --help          Show this help message
  -d, --dry-run       Test configuration without starting server
  -l, --list-models   List available models and their VRAM usage
  --detach            Run server in background
  --port PORT         Override default port (default: 8000)
  -v, --verbose       Enable verbose output

Examples:
  ./start_vllm.sh qwen3.5-2b-nvfp4              # Start 2B model on port 8000
  ./start_vllm.sh qwen3.5-4b-nvfp4 --port 8001  # Start 4B model on port 8001
  ./start_vllm.sh --dry-run                      # Validate setup

EOF
}

check_nccl_version() {
    log_debug "Checking NCCL version..."
    
    local nccl_version
    nccl_version=$(python3 -c "import subprocess; result = subprocess.run(['pip', 'show', 'nvidia-nccl-cu12'], capture_output=True, text=True); print([line.split(':')[1].strip() for line in result.stdout.split('\n') if line.startswith('Version:')][0])" 2>/dev/null || echo "unknown")
    
    log_info "NCCL version: $nccl_version"
    
    if [ "$nccl_version" != "unknown" ]; then
        # Compare versions (simple string comparison for now)
        if [[ "$nccl_version" < "$NCCL_MIN_VERSION" ]]; then
            log_warn "NCCL version $nccl_version is older than recommended $NCCL_MIN_VERSION"
            log_warn "This may cause CUBLAS_STATUS_ALLOC_FAILED errors on RTX 5070 Ti"
            log_info "Fix: pip install nvidia-nccl-cu12==2.27.3"
            return 1
        else
            log_success "NCCL version is up to date ($nccl_version >= $NCCL_MIN_VERSION)"
            return 0
        fi
    fi
    return 0
}

parse_model_from_registry() {
    local model_id="$1"
    local key="$2"
    
    if [ -f "$REGISTRY_FILE" ]; then
        python3 -c "
import json
import sys
try:
    with open('$REGISTRY_FILE') as f:
        registry = json.load(f)
    model = registry.get('models', {}).get('$model_id', {})
    value = model
    for k in '$key'.split('.'):
        value = value.get(k, {}) if isinstance(value, dict) else ''
    print(value)
except Exception as e:
    sys.exit(1)
" 2>/dev/null
    fi
}

get_model_path_from_registry() {
    local model_id="$1"
    local checkpoint_path
    
    checkpoint_path=$(parse_model_from_registry "$model_id" "files.checkpoint")
    if [ -n "$checkpoint_path" ]; then
        echo "${PROJECT_ROOT}/${checkpoint_path}"
    fi
}

list_models() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Available Models - Advanced Vision Trading Pipeline"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    if [ -f "$REGISTRY_FILE" ]; then
        python3 "$SCRIPT_DIR/list_models_helper.py" "$REGISTRY_FILE" "$PROJECT_ROOT"
    else
        echo "Registry file not found, using fallback list"
        echo "qwen3.5-2b-nvfp4 (Scout) - 2.5GB VRAM"
        echo "qwen3.5-4b-nvfp4 (Reviewer) - 4.0GB VRAM"
        echo "qwen3.5-7b-nvfp4 (Expert) - 7.0GB VRAM"
    fi
    
    echo ""
    echo "VRAM Budget (RTX 5070 Ti 16GB):"
    echo "  ├─ Total: 16 GB"
    echo "  ├─ System Reserve: 2 GB"
    echo "  ├─ Available for Models: 14 GB"
    echo "  │"
    echo "  ├─ Resident Set (~8GB):"
    echo "  │   • YOLOv8n:        0.4 GB"
    echo "  │   • MobileSAM:      0.5 GB  ⭐ ALWAYS RESIDENT"
    echo "  │   • Qwen3.5-2B:     2.5 GB"
    echo "  │   • Eagle2-2B:      3.2 GB"
    echo "  │"
    echo "  ├─ On-demand Available:"
    echo "  │   • Qwen3.5-4B:     4.0 GB"
    echo "  │   • SAM3:          10.0 GB (rare use)"
    echo "  │"
    echo "  └─ Headroom: ~6GB for KV cache"
    echo ""
    echo "MobileSAM vs SAM3:"
    echo "  • MobileSAM: 12ms/image, 40MB, ~73% accuracy ⭐ DEFAULT"
    echo "  • SAM3:      2921ms/image, 3.4GB, ~88% accuracy (rare use)"
    echo ""
}

check_vllm() {
    log_debug "Checking vLLM installation..."
    
    if ! command -v vllm &> /dev/null; then
        if ! python3 -c "import vllm" 2>/dev/null; then
            log_error "vLLM not installed!"
            log_info "Install with: pip install vllm"
            return 1
        fi
    fi
    
    local vllm_version
    vllm_version=$(python3 -c "import vllm; print(vllm.__version__)" 2>/dev/null || echo "unknown")
    log_success "vLLM found (version: $vllm_version)"
    return 0
}

check_model() {
    local model_path="$1"
    local model_id="$2"
    
    log_debug "Checking model: $model_id at $model_path"
    
    if [ ! -d "$model_path" ]; then
        log_error "Model directory not found: $model_path"
        return 1
    fi
    
    local has_weights=false
    if [ -f "${model_path}/model.safetensors" ]; then
        has_weights=true
        local size
        size=$(du -sh "${model_path}/model.safetensors" 2>/dev/null | cut -f1 || echo "unknown")
        log_debug "Found model.safetensors ($size)"
    elif [ -f "${model_path}/pytorch_model.bin" ]; then
        has_weights=true
        local size
        size=$(du -sh "${model_path}/pytorch_model.bin" 2>/dev/null | cut -f1 || echo "unknown")
        log_debug "Found pytorch_model.bin ($size)"
    elif [ -n "$(find "$model_path" -name "*.safetensors" -print -quit 2>/dev/null)" ]; then
        has_weights=true
        log_debug "Found .safetensors files"
    fi
    
    if [ "$has_weights" = false ]; then
        log_error "Model weights not found in: $model_path"
        log_info "Expected: model.safetensors or pytorch_model.bin"
        return 1
    fi
    
    if [ ! -f "${model_path}/config.json" ]; then
        log_warn "config.json not found in model directory"
    fi
    
    log_success "Model validated: $model_id"
    return 0
}

get_model_path() {
    local model_name="$1"
    local model_path=""
    
    model_path=$(get_model_path_from_registry "$model_name")
    
    if [ -z "$model_path" ]; then
        case "$model_name" in
            qwen3.5-2b-nvfp4|2b|scout)
                model_path="${MODELS_DIR}/Qwen3.5-2B-NVFP4"
                ;;
            qwen3.5-4b-nvfp4|4b|reviewer)
                model_path="${MODELS_DIR}/Qwen3.5-4B-NVFP4"
                ;;
            qwen3.5-7b-nvfp4|7b|expert)
                model_path="${MODELS_DIR}/Qwen3.5-7B-NVFP4"
                ;;
            *)
                model_path=""
                ;;
        esac
    fi
    
    echo "$model_path"
}

get_gpu_memory_util() {
    local model_name="$1"
    
    case "$model_name" in
        qwen3.5-2b-nvfp4|2b|scout)
            echo "0.70"
            ;;
        qwen3.5-4b-nvfp4|4b|reviewer)
            echo "0.75"
            ;;
        qwen3.5-7b-nvfp4|7b|expert)
            echo "0.80"
            ;;
        *)
            echo "0.75"
            ;;
    esac
}

get_max_model_len() {
    local model_name="$1"
    
    case "$model_name" in
        qwen3.5-2b-nvfp4|2b|scout)
            echo "32768"
            ;;
        qwen3.5-4b-nvfp4|4b|reviewer)
            echo "32768"
            ;;
        qwen3.5-7b-nvfp4|7b|expert)
            echo "16384"
            ;;
        *)
            echo "32768"
            ;;
    esac
}

launch_server() {
    local model_name="$1"
    local model_path
    model_path=$(get_model_path "$model_name")
    local gpu_mem_util
    gpu_mem_util=$(get_gpu_memory_util "$model_name")
    local max_len
    max_len=$(get_max_model_len "$model_name")
    
    if [ -z "$model_path" ]; then
        log_error "Unknown model: $model_name"
        log_info "Run '$0 --list-models' to see available models"
        exit 1
    fi
    
    if ! check_model "$model_path" "$model_name"; then
        log_error "Model validation failed"
        log_info "Download the model first or check the path"
        exit 1
    fi
    
    log_info "Starting vLLM server..."
    log_info "  Model: $model_name"
    log_info "  Path: $model_path"
    log_info "  Port: $PORT"
    log_info "  GPU Memory Util: ${gpu_mem_util}"
    log_info "  Max Length: ${max_len}"
    
    # Check if model supports vLLM
    local vllm_supported
    vllm_supported=$(parse_model_from_registry "$model_name" "vllm_supported")
    if [ "$vllm_supported" = "False" ]; then
        log_error "Model $model_name does not support vLLM"
        log_info "Use transformers-based inference instead"
        log_info "See: python scripts/load_models.py load --model $model_name"
        exit 1
    fi
    
    # Build vLLM command with NVFP4 optimizations
    local VLLM_CMD
    VLLM_CMD="vllm serve \"${model_path}\" \
        --host 0.0.0.0 \
        --port ${PORT} \
        --quantization modelopt \
        --gpu-memory-utilization ${gpu_mem_util} \
        --max-model-len ${max_len} \
        --tensor-parallel-size 1 \
        --trust-remote-code \
        --reasoning-parser qwen3 \
        --chat-template template_chatml.jinja"
    
    echo ""
    log_info "Environment Variables Set:"
    log_info "  VLLM_NVFP4_GEMM_BACKEND=$VLLM_NVFP4_GEMM_BACKEND"
    log_info "  VLLM_TEST_FORCE_FP8_MARLIN=$VLLM_TEST_FORCE_FP8_MARLIN"
    log_info "  VLLM_MOE_ROUTER_PRECISION=$VLLM_MOE_ROUTER_PRECISION"
    echo ""
    log_info "Command:"
    echo "$VLLM_CMD"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        log_warn "Dry run mode - not starting server"
        return 0
    fi
    
    if [ "$DETACH" = true ]; then
        log_info "Starting in background mode..."
        mkdir -p "$LOGS_DIR"
        eval "$VLLM_CMD" > "${LOGS_DIR}/vllm_server.log" 2>&1 &
        local PID=$!
        echo $PID > "${PROJECT_ROOT}/.vllm_server.pid"
        log_success "Server started with PID: $PID"
        log_info "API endpoint: http://localhost:${PORT}/v1"
        log_info "Logs: tail -f ${LOGS_DIR}/vllm_server.log"
        
        sleep 2
        if ! kill -0 $PID 2>/dev/null; then
            log_error "Server failed to start. Check logs: ${LOGS_DIR}/vllm_server.log"
            return 1
        fi
    else
        log_info "Starting server (Ctrl+C to stop)..."
        eval "$VLLM_CMD"
    fi
}

dry_run() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Dry Run - Advanced Vision Trading Pipeline"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Check NCCL version (CRITICAL for RTX 5070 Ti)
    log_info "Checking NCCL version (CRITICAL for RTX 5070 Ti)..."
    check_nccl_version || true
    
    # Check Python environment
    log_info "Checking Python environment..."
    python3 --version
    
    # Check vLLM
    log_info "Checking vLLM installation..."
    if check_vllm; then
        log_success "vLLM is installed"
    else
        log_warn "vLLM not found in Python environment"
    fi
    
    # Check environment variables
    log_info "Checking NVFP4 environment variables..."
    log_info "  VLLM_NVFP4_GEMM_BACKEND=$VLLM_NVFP4_GEMM_BACKEND"
    log_info "  VLLM_TEST_FORCE_FP8_MARLIN=$VLLM_TEST_FORCE_FP8_MARLIN"
    log_info "  VLLM_MOE_ROUTER_PRECISION=$VLLM_MOE_ROUTER_PRECISION"
    
    # Check models
    log_info "Checking model files..."
    local found_count=0
    local missing_count=0
    
    for model_dir in "${MODELS_DIR}"/*/; do
        if [ -d "$model_dir" ]; then
            model_name=$(basename "$model_dir")
            if [ -f "${model_dir}/model.safetensors" ] || [ -f "${model_dir}/pytorch_model.bin" ]; then
                local size
                size=$(du -sh "$model_dir" 2>/dev/null | cut -f1 || echo "unknown")
                log_success "Found: $model_name (${size})"
                ((found_count++)) || true
            else
                log_warn "Incomplete: $model_dir"
                ((missing_count++)) || true
            fi
        fi
    done
    
    log_info "Models found: $found_count, incomplete: $missing_count"
    
    # Check GPU
    log_info "Checking GPU..."
    if command -v nvidia-smi &> /dev/null; then
        local gpu_info
        gpu_info=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "unknown")
        echo "  $gpu_info"
    else
        log_warn "nvidia-smi not found - cannot detect GPU"
    fi
    
    # Test loading configuration
    log_info "Testing configuration files..."
    if [ -f "$CONFIG_FILE" ]; then
        log_success "vLLM config: $CONFIG_FILE"
    else
        log_warn "vLLM config not found: $CONFIG_FILE"
    fi
    
    if [ -f "$REGISTRY_FILE" ]; then
        log_success "Model registry: $REGISTRY_FILE"
        local model_count
        model_count=$(python3 -c "import json; print(len(json.load(open('$REGISTRY_FILE'))['models']))" 2>/dev/null || echo "unknown")
        log_info "Registered models: $model_count"
    else
        log_warn "Registry file not found: $REGISTRY_FILE"
    fi
    
    echo ""
    log_success "Dry run complete"
    echo ""
    
    # Show fix reminder
    echo "═══════════════════════════════════════════════════════════════"
    echo "  RTX 5070 Ti Fix Reminder"
    echo "═══════════════════════════════════════════════════════════════"
    echo "If you encounter CUBLAS_STATUS_ALLOC_FAILED errors:"
    echo "  pip install nvidia-nccl-cu12==2.27.3"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -l|--list-models)
            LIST_MODELS=true
            shift
            ;;
        --detach)
            DETACH=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            MODEL_NAME="$1"
            shift
            ;;
    esac
done

# Create logs directory if needed
mkdir -p "${LOGS_DIR}"

# Execute command
if [ "$LIST_MODELS" = true ]; then
    list_models
    exit 0
fi

if [ "$DRY_RUN" = true ]; then
    dry_run
    exit 0
fi

# Launch server
launch_server "$MODEL_NAME"
