#!/bin/bash
# =============================================================================
# YOLO Dataset Split Application Script
# Applies the session-based train/val/test split strategy
# =============================================================================

set -euo pipefail

# Base directories
BASE_DIR="/home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision/yolo_training"
RAW_IMAGES_DIR="$BASE_DIR/annotations/raw_images"
CONFIG_FILE="$BASE_DIR/data_split_strategy.json"

# Target directories
TRAIN_IMG_DIR="$BASE_DIR/data/images/train"
VAL_IMG_DIR="$BASE_DIR/data/images/val"
TEST_IMG_DIR="$BASE_DIR/data/images/test"
TRAIN_LBL_DIR="$BASE_DIR/data/labels/train"
VAL_LBL_DIR="$BASE_DIR/data/labels/val"
TEST_LBL_DIR="$BASE_DIR/data/labels/test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Setup directories
# =============================================================================
setup_directories() {
    log_info "Creating target directories..."
    
    for dir in "$TRAIN_IMG_DIR" "$VAL_IMG_DIR" "$TEST_IMG_DIR" \
               "$TRAIN_LBL_DIR" "$VAL_LBL_DIR" "$TEST_LBL_DIR"; do
        mkdir -p "$dir"
    done
    
    log_success "Directories created"
}

# =============================================================================
# Clear existing data
# =============================================================================
clear_existing() {
    log_warn "Clearing existing split data..."
    
    for dir in "$TRAIN_IMG_DIR" "$VAL_IMG_DIR" "$TEST_IMG_DIR" \
               "$TRAIN_LBL_DIR" "$VAL_LBL_DIR" "$TEST_LBL_DIR"; do
        rm -f "$dir"/*
    done
    
    log_success "Existing data cleared"
}

# =============================================================================
# Copy images and create empty labels for negative examples
# =============================================================================
copy_with_label() {
    local src_file="$1"
    local dest_img_dir="$2"
    local dest_lbl_dir="$3"
    local split_name="$4"
    
    local filename
    filename=$(basename "$src_file")
    local name_no_ext="${filename%.*}"
    local dest_img="$dest_img_dir/$filename"
    local dest_lbl="$dest_lbl_dir/$name_no_ext.txt"
    
    # Copy image
    cp "$src_file" "$dest_img"
    
    # Create empty label file (negative example - no annotations)
    touch "$dest_lbl"
    
    echo "  [$split_name] $filename"
}

# =============================================================================
# Process each split
# =============================================================================
process_split() {
    local split_name="$1"  # train, val, or test
    local dest_img_dir="$2"
    local dest_lbl_dir="$3"
    
    log_info "Processing $split_name split..."
    
    # Extract sessions for this split from JSON
    local sessions
    sessions=$(python3 -c "
import json
with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)
sessions = config.get('${split_name}_sessions', [])
print(' '.join(sessions))
")
    
    local count=0
    for session in $sessions; do
        # Get files for this session
        local files
        files=$(python3 -c "
import json
with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)
session_data = config.get('sessions', {}).get('$session', {})
files = session_data.get('files', [])
for f in files:
    print(f)
")
        
        for file in $files; do
            local src_file="$RAW_IMAGES_DIR/$file"
            if [ -f "$src_file" ]; then
                copy_with_label "$src_file" "$dest_img_dir" "$dest_lbl_dir" "$split_name"
                count=$((count + 1))
            else
                log_error "File not found: $src_file"
            fi
        done
    done
    
    log_success "$split_name split complete: $count images"
}

# =============================================================================
# Verify the split
# =============================================================================
verify_split() {
    log_info "Verifying split..."
    
    echo ""
    echo "================================================================================"
    echo "SPLIT VERIFICATION"
    echo "================================================================================"
    echo ""
    
    local train_img_count train_lbl_count val_img_count val_lbl_count test_img_count test_lbl_count
    train_img_count=$(ls -1 "$TRAIN_IMG_DIR"/*.png 2>/dev/null | wc -l)
    train_lbl_count=$(ls -1 "$TRAIN_LBL_DIR"/*.txt 2>/dev/null | wc -l)
    val_img_count=$(ls -1 "$VAL_IMG_DIR"/*.png 2>/dev/null | wc -l)
    val_lbl_count=$(ls -1 "$VAL_LBL_DIR"/*.txt 2>/dev/null | wc -l)
    test_img_count=$(ls -1 "$TEST_IMG_DIR"/*.png 2>/dev/null | wc -l)
    test_lbl_count=$(ls -1 "$TEST_LBL_DIR"/*.txt 2>/dev/null | wc -l)
    
    local total_img total_lbl
    total_img=$((train_img_count + val_img_count + test_img_count))
    total_lbl=$((train_lbl_count + val_lbl_count + test_lbl_count))
    
    printf "%-10s | %-8s | %-8s | %-10s\n" "Split" "Images" "Labels" "Status"
    printf "%-10s-+-%8s-+-%8s-+-%10s\n" "----------" "--------" "--------" "----------"
    printf "%-10s | %8d | %8d | %s\n" "Train" "$train_img_count" "$train_lbl_count" "$([ "$train_img_count" -eq "$train_lbl_count" ] && echo "OK" || echo "MISMATCH")"
    printf "%-10s | %8d | %8d | %s\n" "Val" "$val_img_count" "$val_lbl_count" "$([ "$val_img_count" -eq "$val_lbl_count" ] && echo "OK" || echo "MISMATCH")"
    printf "%-10s | %8d | %8d | %s\n" "Test" "$test_img_count" "$test_lbl_count" "$([ "$test_img_count" -eq "$test_lbl_count" ] && echo "OK" || echo "MISMATCH")"
    printf "%-10s-+-%8s-+-%8s-+-%10s\n" "----------" "--------" "--------" "----------"
    printf "%-10s | %8d | %8d |\n" "Total" "$total_img" "$total_lbl"
    
    echo ""
    
    if [ "$train_img_count" -eq "$train_lbl_count" ] && \
       [ "$val_img_count" -eq "$val_lbl_count" ] && \
       [ "$test_img_count" -eq "$test_lbl_count" ]; then
        log_success "Verification passed: All images have matching labels"
        return 0
    else
        log_error "Verification failed: Image/label mismatch detected"
        return 1
    fi
}

# =============================================================================
# Generate summary report
# =============================================================================
generate_report() {
    local output_file="$BASE_DIR/split_report.txt"
    
    log_info "Generating summary report: $output_file"
    
    local train_img_count val_img_count test_img_count
    train_img_count=$(ls -1 "$TRAIN_IMG_DIR"/*.png 2>/dev/null | wc -l)
    val_img_count=$(ls -1 "$VAL_IMG_DIR"/*.png 2>/dev/null | wc -l)
    test_img_count=$(ls -1 "$TEST_IMG_DIR"/*.png 2>/dev/null | wc -l)
    
    cat > "$output_file" << REPORT
================================================================================
YOLO Dataset Split Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')
================================================================================

Configuration: $CONFIG_FILE

DIRECTORY STRUCTURE:
  Train Images: $TRAIN_IMG_DIR
  Train Labels: $TRAIN_LBL_DIR
  Val Images:   $VAL_IMG_DIR
  Val Labels:   $VAL_LBL_DIR
  Test Images:  $TEST_IMG_DIR
  Test Labels:  $TEST_LBL_DIR

SPLIT COUNTS:
  Train: $train_img_count images
  Val:   $val_img_count images
  Test:  $test_img_count images

NEGATIVE EXAMPLES:
  All images in this split are negative examples (no P0 class annotations).
  Empty .txt files created for each image to indicate negative samples.

NEXT STEPS:
  1. Review the split in data/images/ and data/labels/
  2. Add positive examples with actual YOLO format annotations
  3. Update data_phase1_p0.yaml with correct class names
  4. Run training: bash train_phase1_p0.sh

================================================================================
REPORT

    log_success "Report saved to $output_file"
}

# =============================================================================
# Main execution
# =============================================================================
main() {
    echo "================================================================================"
    echo "YOLO Dataset Split Application"
    echo "================================================================================"
    echo ""
    
    # Check if config exists
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Check if raw images exist
    if [ ! -d "$RAW_IMAGES_DIR" ]; then
        log_error "Raw images directory not found: $RAW_IMAGES_DIR"
        exit 1
    fi
    
    setup_directories
    clear_existing
    
    echo ""
    log_info "Copying images and creating empty labels..."
    echo ""
    
    process_split "train" "$TRAIN_IMG_DIR" "$TRAIN_LBL_DIR"
    process_split "val" "$VAL_IMG_DIR" "$VAL_LBL_DIR"
    process_split "test" "$TEST_IMG_DIR" "$TEST_LBL_DIR"
    
    echo ""
    verify_split
    
    echo ""
    generate_report
    
    echo ""
    echo "================================================================================"
    log_success "Dataset split complete!"
    echo "================================================================================"
    echo ""
    echo "To train the model:"
    echo "  cd $BASE_DIR"
    echo "  bash train_phase1_p0.sh"
}

# Run main function
main "$@"
