#!/bin/bash
# =============================================================================
# vLLM Model Server Launcher for Advanced Vision Trading Pipeline
# =============================================================================
# Usage: ./scripts/start_vllm.sh [model_name] [options]
# 
# Examples:
#   ./scripts/start_vllm.sh qwen3.5-2b-nvfp4          # Start 2B scout model
#   ./scripts/start_vllm.sh qwen3.5-4b-nvfp4          # Start 4B reviewer model
#   ./scripts/start_vllm.sh --dry-run                 # Test configuration
#   ./scripts/start_vllm.sh --list-models             # List available models
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config/vllm.yaml"
MODELS_DIR="${PROJECT_ROOT}/models"

# Default values
MODEL_NAME="${1:-qwen3.5-2b-nvfp4}"
DRY_RUN=false
LIST_MODELS=false
DETACH=false
PORT=8000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

show_help() {
    cat << EOF
Usage: $0 [MODEL_NAME] [OPTIONS]

Launch vLLM server with NVFP4 quantized models for trading pipeline.

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

Examples:
  $0 qwen3.5-2b-nvfp4              # Start 2B model on port 8000
  $0 qwen3.5-4b-nvfp4 --port 8001  # Start 4B model on port 8001
  $0 --dry-run                      # Validate setup

EOF
}

list_models() {
    echo "Available NVFP4 Models:"
    echo "======================="
    echo ""
    
    # 2B Model
    echo -e "${GREEN}qwen3.5-2b-nvfp4${NC} (Scout)"
    echo "  Path: ${MODELS_DIR}/Qwen3.5-2B-NVFP4"
    if [ -f "${MODELS_DIR}/Qwen3.5-2B-NVFP4/model.safetensors" ]; then
        SIZE=$(du -sh "${MODELS_DIR}/Qwen3.5-2B-NVFP4/model.safetensors" | cut -f1)
        echo "  Size: ${SIZE}"
        echo "  Status: ${GREEN}Downloaded ✓${NC}"
    else
        echo "  Status: ${RED}Not found ✗${NC}"
    fi
    echo "  VRAM: ~2.5 GB"
    echo "  Role: Quick screen analysis, pattern detection"
    echo ""
    
    # 4B Model
    echo -e "${GREEN}qwen3.5-4b-nvfp4${NC} (Reviewer)"
    echo "  Path: ${MODELS_DIR}/Qwen3.5-4B-NVFP4"
    if [ -f "${MODELS_DIR}/Qwen3.5-4B-NVFP4/model.safetensors" ]; then
        SIZE=$(du -sh "${MODELS_DIR}/Qwen3.5-4B-NVFP4/model.safetensors" | cut -f1)
        echo "  Size: ${SIZE}"
        echo "  Status: ${GREEN}Downloaded ✓${NC}"
    else
        echo "  Status: ${RED}Not found ✗${NC}"
    fi
    echo "  VRAM: ~4.0 GB"
    echo "  Role: Detailed chart analysis, signal validation"
    echo ""
    
    # 7B Model
    echo -e "${YELLOW}qwen3.5-7b-nvfp4${NC} (Expert - Not Downloaded)"
    echo "  VRAM: ~7.0 GB"
    echo "  Role: High-stakes decisions, complex analysis"
    echo ""
    
    # VRAM summary
    echo "VRAM Budget (RTX 5070 Ti 16GB):"
    echo "  Total: 16 GB"
    echo "  System Reserve: 2 GB"
    echo "  Available for Models: 14 GB"
    echo ""
    echo "Loading Combinations:"
    echo "  2B only: ~2.5 GB (safe)"
    echo "  4B only: ~4.0 GB (safe)"
    echo "  2B + 4B: ~6.5 GB (safe)"
    echo "  7B only: ~7.0 GB (safe)"
    echo "  2B + 7B: ~9.5 GB (safe)"
}

check_vllm() {
    if ! command -v vllm &> /dev/null; then
        if ! python3 -c "import vllm" 2>/dev/null; then
            log_error "vLLM not installed!"
            log_info "Install with: pip install vllm"
            exit 1
        fi
    fi
    log_success "vLLM found"
}

check_model() {
    local model_path="$1"
    if [ ! -d "$model_path" ]; then
        log_error "Model directory not found: $model_path"
        return 1
    fi
    
    if [ ! -f "${model_path}/model.safetensors" ] && [ ! -f "${model_path}/pytorch_model.bin" ]; then
        log_error "Model weights not found in: $model_path"
        return 1
    fi
    
    log_success "Model validated: $model_path"
    return 0
}

get_model_path() {
    case "$1" in
        qwen3.5-2b-nvfp4|2b|scout)
            echo "${MODELS_DIR}/Qwen3.5-2B-NVFP4"
            ;;
        qwen3.5-4b-nvfp4|4b|reviewer)
            echo "${MODELS_DIR}/Qwen3.5-4B-NVFP4"
            ;;
        qwen3.5-7b-nvfp4|7b|expert)
            echo "${MODELS_DIR}/Qwen3.5-7B-NVFP4"
            ;;
        *)
            echo ""
            ;;
    esac
}

get_gpu_memory_util() {
    case "$1" in
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
    case "$1" in
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
    local model_path=$(get_model_path "$model_name")
    local gpu_mem_util=$(get_gpu_memory_util "$model_name")
    local max_len=$(get_max_model_len "$model_name")
    
    if [ -z "$model_path" ]; then
        log_error "Unknown model: $model_name"
        exit 1
    fi
    
    check_model "$model_path"
    
    log_info "Starting vLLM server..."
    log_info "  Model: $model_name"
    log_info "  Path: $model_path"
    log_info "  Port: $PORT"
    log_info "  GPU Memory: ${gpu_mem_util}"
    log_info "  Max Length: ${max_len}"
    
    # Build vLLM command
    VLLM_CMD="vllm serve \"${model_path}\" \
        --host 0.0.0.0 \
        --port ${PORT} \
        --quantization modelopt \
        --gpu-memory-utilization ${gpu_mem_util} \
        --max-model-len ${max_len} \
        --tensor-parallel-size 1 \
        --trust-remote-code \
        --reasoning-parser qwen3 \
        --chat-template qwen3"
    
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
        eval "$VLLM_CMD" &
        local PID=$!
        echo $PID > "${PROJECT_ROOT}/.vllm_server.pid"
        log_success "Server started with PID: $PID"
        log_info "API endpoint: http://localhost:${PORT}/v1"
        log_info "Logs: tail -f ${PROJECT_ROOT}/logs/vllm_server.log"
    else
        log_info "Starting server (Ctrl+C to stop)..."
        eval "$VLLM_CMD"
    fi
}

dry_run() {
    log_info "Dry Run Mode - Testing Configuration"
    echo "====================================="
    echo ""
    
    # Check Python environment
    log_info "Checking Python environment..."
    python3 --version
    
    # Check vLLM
    log_info "Checking vLLM installation..."
    if python3 -c "import vllm; print(f'vLLM version: {vllm.__version__}')" 2>/dev/null; then
        log_success "vLLM is installed"
    else
        log_warn "vLLM not found in Python environment"
    fi
    
    # Check models
    log_info "Checking model files..."
    for model_dir in "${MODELS_DIR}"/*/; do
        if [ -d "$model_dir" ]; then
            model_name=$(basename "$model_dir")
            if [ -f "${model_dir}/model.safetensors" ]; then
                size=$(du -sh "${model_dir}/model.safetensors" | cut -f1)
                log_success "Found: $model_name (${size})"
            else
                log_warn "Incomplete: $model_dir"
            fi
        fi
    done
    
    # Check GPU
    log_info "Checking GPU..."
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
    else
        log_warn "nvidia-smi not found - cannot detect GPU"
    fi
    
    # Test loading configuration
    log_info "Testing configuration file: $CONFIG_FILE"
    if [ -f "$CONFIG_FILE" ]; then
        log_success "Configuration file exists"
        # Could add YAML validation here if yq or similar is available
    else
        log_warn "Configuration file not found"
    fi
    
    echo ""
    log_success "Dry run complete - no errors detected"
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
mkdir -p "${PROJECT_ROOT}/logs"

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
