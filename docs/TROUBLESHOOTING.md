# Troubleshooting Guide - Advanced Vision

**Date:** 2026-03-17  
**Hardware:** NVIDIA RTX 5070 Ti 16GB  
**Status:** Solutions verified working

---

## Table of Contents

1. [VRAM OOM Issues](#vram-oom-issues)
2. [Model Path Errors](#model-path-errors)
3. [WSS Connection Issues](#wss-connection-issues)
4. [Screenshot/GUI Issues](#screenshotgui-issues)
5. [CUDA/Blackwell Issues](#cudablackwell-issues)

---

## VRAM OOM Issues

### Symptom
```
RuntimeError: CUDA out of memory
Tried to allocate X.XX GiB (GPU 0; 15.75 GiB total capacity)
```

### Solutions

#### 1. Check Current VRAM Usage
```bash
nvidia-smi
```

**Expected output:**
```
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.154.05             Driver Version: 535.154.05   CUDA Version: 12.2     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  NVIDIA GeForce RTX 5070 Ti     On  | 00000000:01:00.0  On |                  N/A |
|  0%   45C    P8              15W / 300W |    812MiB / 16303MiB |      0%      Default |
+-----------------------------------------+----------------------+----------------------+
```

#### 2. Clear VRAM Cache
```python
import torch
torch.cuda.empty_cache()
```

#### 3. Load Models Sequentially (Not Concurrently)
```python
# ❌ WRONG: Loading all models at once
model1 = load_qwen4b()  # 8.4GB
model2 = load_eagle2()  # 4.0GB
model3 = load_yolo()    # 0.4GB
# Total: ~12.8GB - may OOM

# ✅ CORRECT: Load only what you need
model1 = load_qwen4b()  # 8.4GB
result1 = model1.inference(...)
del model1
torch.cuda.empty_cache()

model2 = load_eagle2()  # 4.0GB
result2 = model2.inference(...)
```

#### 4. Use BF16 Instead of FP32
```python
# ✅ CORRECT: Use BF16 (half precision)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,  # Not torch.float32
    device_map="cuda",
)

# For Eagle2, use FP16 + half()
model = model.half()
```

#### 5. Set Smaller Batch Size
```python
# For YOLO
results = model(image, batch=1)  # Force batch size 1
```

---

## Model Path Errors

### Symptom 1: ModelNotFoundError
```
ModelNotFoundError: Model not downloaded: qwen3.5-4b
Expected at: models/Qwen3.5-4B/
```

### Solution
Check if model exists:
```bash
ls -la models/Qwen3.5-4B/
```

**Expected structure:**
```
models/Qwen3.5-4B/
├── config.json
├── model.safetensors.index.json
├── model.safetensors.00of04
├── model.safetensors.01of04
├── model.safetensors.02of04
├── model.safetensors.03of04
├── tokenizer.json
└── tokenizer_config.json
```

### Symptom 2: Path Not Found
```
FileNotFoundError: [Errno 2] No such file or directory: 'models/Qwen3.5-4B'
```

### Solution: Use Absolute Path
```python
from pathlib import Path

# ❌ WRONG: Relative path
MODEL_PATH = "models/Qwen3.5-4B"

# ✅ CORRECT: Absolute path
PROJECT_ROOT = Path.home() / ".openclaw/workspace/plane-a/projects/advanced-vision"
MODEL_PATH = PROJECT_ROOT / "models/Qwen3.5-4B"

# Or use Path().resolve()
MODEL_PATH = Path("models/Qwen3.5-4B").resolve()
```

### Symptom 3: safetensors Not Found
```
OSError: models/Qwen3.5-4B does not appear to have a file named model.safetensors
```

### Solution: Use index.json
```python
# Transformers automatically handles sharded models
# Just point to the directory, not individual files
model = AutoModelForCausalLM.from_pretrained(
    "models/Qwen3.5-4B",  # Directory with index
    torch_dtype=torch.bfloat16,
    device_map="cuda",
)
```

---

## WSS Connection Issues

### Symptom 1: Connection Refused
```
ConnectionRefusedError: [Errno 111] Connection refused
```

### Solution: Check Server Status
```bash
# Check if WSS server is running
lsof -i :8001  # YOLO publisher
lsof -i :8002  # SAM publisher
lsof -i :8003  # Eagle publisher
lsof -i :8004  # Analysis publisher
```

**Start the server:**
```python
from advanced_vision.wss_server import WSSServer, WSSServerConfig

config = WSSServerConfig(port=8001)
server = WSSServer(config)
await server.start()
```

### Symptom 2: Connection Timeout
```
timeout: timed out
```

### Solution: Increase Timeout
```python
import websockets

async with websockets.connect(
    "ws://localhost:8001",
    timeout=30,  # Increase from default 10s
    ping_interval=20,
    ping_timeout=10,
) as ws:
    ...
```

### Symptom 3: SSL/TLS Error
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

### Solution: Disable SSL for Localhost
```python
# For local development only
import ssl
ssl_context = ssl.SSLContext()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async with websockets.connect(
    "wss://localhost:8001",
    ssl=ssl_context,
) as ws:
    ...
```

### Symptom 4: Port Already in Use
```
OSError: [Errno 98] Address already in use
```

### Solution: Kill Existing Process
```bash
# Find process using port
lsof -i :8001

# Kill it
kill -9 <PID>

# Or use different port
python examples/wss_demo.py --port 8005
```

---

## Screenshot/GUI Issues

### Symptom 1: Gray Screenshots (1280x720)
```
Screenshot: 1280x720
Note: Using placeholder (headless/GUI unavailable)
```

### Solution: Check Display
```bash
# Check DISPLAY variable
echo $DISPLAY

# Should output: :0 or :1

# If empty, set it
export DISPLAY=:1

# Verify X11
echo $XDG_SESSION_TYPE
# Should output: x11 (not wayland)
```

### Symptom 2: pyautogui FailSafeException
```
pyautogui.FailSafeException: Display not detected
```

### Solution: Install Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install -y python3-tk python3-dev scrot

# Verify tkinter
python3 -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))"
```

### Symptom 3: Wayland Not Supported
```
Error: Wayland display not supported
```

### Solution: Switch to X11
```bash
# Log out and select "X11" or "Xorg" at login screen
# Or set environment variable (temporary):
export QT_QPA_PLATFORM=xcb
export GDK_BACKEND=x11
```

---

## CUDA/Blackwell Issues

### Symptom 1: NVFP4 Not Working
```
RuntimeError: CUDA error: no kernel image is available for execution on the device
CUDA kernel errors might be asynchronously reported at some other API call
```

### Root Cause
RTX 5070 Ti uses Blackwell architecture (sm120) which lacks NVFP4 kernels in current vLLM/flashinfer.

### Solution: Use BF16 Models
```python
# ❌ WRONG: NVFP4 not supported
model = AutoModelForCausalLM.from_pretrained(
    "models/Qwen3.5-4B-NVFP4",
    quantization_config={"load_in_4bit": True},  # NVFP4
)

# ✅ CORRECT: Use BF16 (only ~1-2GB more VRAM)
model = AutoModelForCausalLM.from_pretrained(
    "models/Qwen3.5-4B",  # BF16 version
    torch_dtype=torch.bfloat16,
    device_map="cuda",
)
```

### Symptom 2: vLLM Won't Start
```
RuntimeError: Failed to initialize vLLM engine
```

### Solution: Use Transformers Directly
```python
# ❌ WRONG: vLLM not supported on Blackwell
from vllm import LLM
llm = LLM(model="models/Qwen3.5-4B")

# ✅ CORRECT: Use transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained(
    "models/Qwen3.5-4B",
    torch_dtype=torch.bfloat16,
    device_map="cuda",
)
```

### Symptom 3: NCCL/CUBLAS Errors
```
RuntimeError: CUDA error: CUBLAS_STATUS_ALLOC_FAILED
cublasCreate failed: NCCL error
```

### Solution: Install Compatible NCCL
```bash
pip install nvidia-nccl-cu12==2.27.3

# Set environment variables
export VLLM_NVFP4_GEMM_BACKEND=marlin
export VLLM_TEST_FORCE_FP8_MARLIN=1
```

---

## Environment Setup Checklist

Run this checklist to verify your environment:

```bash
#!/bin/bash
# verify_setup.sh

echo "=== Advanced Vision Setup Checklist ==="

# 1. Python version
echo -n "Python 3.11+: "
python3 --version | grep -E "3\.(11|12)" && echo "✓" || echo "✗"

# 2. CUDA available
echo -n "CUDA available: "
python3 -c "import torch; print('✓' if torch.cuda.is_available() else '✗')"

# 3. GPU detected
echo -n "GPU detected: "
nvidia-smi --query-gpu=name --format=csv,noheader | head -1

# 4. Models exist
echo -n "Qwen3.5-4B: "
[ -d "models/Qwen3.5-4B" ] && echo "✓" || echo "✗"

echo -n "Eagle2-2B: "
[ -d "models/Eagle2-2B" ] && echo "✓" || echo "✗"

echo -n "YOLOv8n: "
[ -f "models/yolov8n.pt" ] && echo "✓" || echo "✗"

# 5. Display
echo -n "DISPLAY: "
[ -n "$DISPLAY" ] && echo "✓ ($DISPLAY)" || echo "✗ (not set)"

# 6. X11 session
echo -n "X11 session: "
[ "$XDG_SESSION_TYPE" = "x11" ] && echo "✓" || echo "✗ ($XDG_SESSION_TYPE)"

echo "======================================="
```

---

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| OOM | `torch.cuda.empty_cache()` + load sequentially |
| Model not found | Check `models/` directory exists with correct case |
| WSS refused | `lsof -i :8001` to check if server running |
| Gray screenshot | `export DISPLAY=:1` |
| Wayland error | Log out → select X11 at login |
| NVFP4 error | Use BF16 models instead |
| vLLM error | Use transformers directly |

---

## Getting Help

1. Check diagnostics: `python -m advanced_vision.diagnostics`
2. Run smoke tests: `pytest tests/test_smoke.py -v`
3. Check VRAM: `nvidia-smi`
4. Review logs: `ls logs/`

---

*Last updated: 2026-03-17*
