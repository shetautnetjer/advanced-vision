#!/bin/bash
# Start WebSocket Server v2 for Advanced Vision
# Usage: ./start_wss_server.sh [options]
#
# v2: Single port (8000) with topic-based routing

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default configuration
CONFIG_FILE="${PROJECT_DIR}/config/wss_config.yaml"
PYTHON_CMD="${PYTHON_CMD:-python3}"
HOST="0.0.0.0"
PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    cat << EOF
Advanced Vision WebSocket Server v2 Launcher

Usage: $0 [OPTIONS]

Options:
    -c, --config PATH       Path to config file (default: config/wss_config.yaml)
    -p, --port PORT         Port to run on (default: 8000)
    -h, --help              Show this help message
    --install-deps          Install required dependencies

Examples:
    $0                      # Start v2 server on port 8000
    $0 -p 9000              # Start v2 server on custom port
    $0 --install-deps       # Install dependencies first

EOF
}

# Install dependencies
install_deps() {
    print_info "Installing dependencies..."
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 not found. Please install Python3 and pip."
        exit 1
    fi
    
    # Install required packages
    pip3 install websockets asyncio pyyaml pillow numpy
    
    print_success "Dependencies installed!"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        --install-deps)
            install_deps
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check Python availability
if ! command -v $PYTHON_CMD &> /dev/null; then
    print_error "Python not found. Please install Python 3.8+"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
print_info "Using Python $PYTHON_VERSION"

# Verify config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    print_warning "Config file not found: $CONFIG_FILE"
    print_info "Using default configuration"
    CONFIG_ARG=""
else
    print_info "Using config: $CONFIG_FILE"
    CONFIG_ARG="--config $CONFIG_FILE"
fi

# Create necessary directories
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/logs/frames"

# Check if server script exists
SERVER_SCRIPT="${PROJECT_DIR}/src/advanced_vision/wss_server_v2.py"
if [[ ! -f "$SERVER_SCRIPT" ]]; then
    print_error "Server script not found: $SERVER_SCRIPT"
    exit 1
fi

# Export PYTHONPATH
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH}"

print_info "Starting Advanced Vision WSS v2 Server..."
print_info "Project directory: $PROJECT_DIR"
print_info "Logs directory: ${PROJECT_DIR}/logs"
print_info "Port: $PORT"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     Advanced Vision WebSocket Server v2                ║"
echo "║                                                        ║"
echo "║  Port: $PORT                                            "
echo "║                                                        ║"
echo "║  Topics:                                               ║"
echo "║    vision.capture.raw       - Screen capture           ║"
echo "║    vision.detection.yolo    - YOLO detections          ║"
echo "║    vision.segmentation.sam  - MobileSAM masks          ║"
echo "║    vision.classification.eagle - Eagle classifications ║"
echo "║    vision.analysis.qwen     - Analysis results         ║"
echo "║                                                        ║"
echo "║  Press Ctrl+C to stop                                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Trap Ctrl+C
trap 'print_info "Shutting down server..."; exit 0' INT TERM

# Start the server
cd "$PROJECT_DIR"
exec $PYTHON_CMD -u "$SERVER_SCRIPT" --port $PORT $CONFIG_ARG
