# Model Deployment Issues - 2026-03-17

**Agent:** Aya (Issues/Schema Agent)  
**Project:** advanced-vision  
**Scope:** Schema violations, tag misalignments, doc/code drift, VRAM estimation errors, missing error handling  
**Status:** Issues Documented for Code Agent  

---

## 🔴 CRITICAL ISSUES

### 1. Model Registry / vLLM Config Mismatch - DOC/CODE DRIFT
**Files:** `config/model_registry.json` vs `config/vllm.yaml`

**Issue:** The model_registry.json and vllm.yaml reference completely different model families:
- `model_registry.json`: Uses Qwen2.5-VL (2B), Eagle2-2B, YOLOv8, SAM variants
- `vllm.yaml`: Uses Qwen3.5-NVFP4 (2B, 4B, 7B variants)

**Impact:** Cannot determine which models are actually deployed. VRAM calculations, loading strategies, and deployment scripts may target wrong models.

**Specific Problems:**
```yaml
# vllm.yaml references these models:
- qwen3.5-2b-nvfp4 (VRAM: 2.5GB)
- qwen3.5-4b-nvfp4 (VRAM: 4.0GB)
- qwen3.5-7b-nvfp4 (VRAM: 7.0GB)

# model_registry.json references these:
- qwen2.5-vl-2b (VRAM tensorrt: 2.2GB)
- eagle2-2b (VRAM tensorrt: 3.2GB)
```

**Evidence:**
- vllm.yaml line 35: `qwen3.5-2b-nvfp4` defined
- model_registry.json line 58: `qwen2.5-vl-2b` defined
- Model IDs don't match, VRAM estimates differ

**Recommendation:** Align both configs to use same model family (likely Qwen3.5-NVFP4 per latest setup).

---

### 2. Missing Metadata Fields in Schemas - SCHEMA VIOLATION
**File:** `src/advanced_vision/schemas.py`

**Issue:** Artifact schemas lack required metadata fields per project standards:
- `artifact_id`: No unique identifier for artifacts
- `plane`: No plane identification (plane-a, plane-b, etc.)
- `advisory`: No advisory classification field
- `tags`: No canonical tag support

**Current Schema (ScreenshotArtifact):**
```python
class ScreenshotArtifact(BaseModel):
    path: str
    width: int
    height: int
    timestamp: str
```

**Required Schema:**
```python
class ScreenshotArtifact(BaseModel):
    artifact_id: str      # Unique identifier
    path: str
    width: int
    height: int
    timestamp: str
    plane: str            # e.g., "plane-a"
    advisory: str | None  # Advisory classification
    tags: list[str]       # Canonical tags
```

**Impact:** Cannot properly track artifacts across planes, apply retention policies, or integrate with governance systems.

**Affected Classes:**
- `ScreenshotArtifact`
- `VideoArtifact`
- `VideoAnalysisResult`
- `ActionResult`
- `VerificationResult`

---

### 3. Tag System Misalignment - TAG MISALIGNMENT
**Files:** `src/advanced_vision/cleanup.py` vs `src/advanced_vision/schemas.py`

**Issue:** Tags are used in cleanup.py but not validated or defined in schemas.

**cleanup.py defines:**
```python
KEEP_TAGS = ['error', 'issue', 'data', 'debug', 'evidence']
```

**Problems:**
1. No canonical tag schema defined in schemas.py
2. No validation that tags are from allowed set
3. Tags in cleanup.py don't match any documented taxonomy
4. No integration with `TradingEventType` or `RiskLevel` enums from events.py

**Impact:** Inconsistent tagging, potential data loss (tags not recognized), governance gaps.

**Recommendation:** 
- Define canonical tags in schemas.py
- Link to TradingEventType taxonomy
- Add tag validation

---

### 4. VRAM Estimation Inconsistencies - VRAM ESTIMATION ERROR
**Files:** Multiple docs and configs

**Issue:** VRAM estimates vary between files for same models:

| Model | model_registry.json | vllm.yaml | VRAM_USAGE.md | SEQUENTIAL_LOADING.md |
|-------|---------------------|-----------|---------------|----------------------|
| Qwen2.5-VL-2B | 2.2 GB (tensorrt) | N/A | 2.2 GB | 2.2 GB |
| Eagle2-2B | 3.2 GB (tensorrt) | N/A | 3.2 GB | 3.2 GB |
| Qwen3.5-2B | N/A | 2.5 GB | N/A | N/A |
| Qwen3.5-4B | N/A | 4.0 GB | N/A | N/A |

**Problems:**
1. Different model families used across configs
2. TensorRT vs NVFP4 quantization not consistently documented
3. Some models have full precision breakdown (fp32/fp16/int8/tensorrt), others don't
4. `mobilesam` in model_registry.json missing fp32/fp16 breakdown

**Evidence:**
- model_registry.json line 117: eagle2-2b tensorrt_gb: 3.2
- vllm.yaml line 46: qwen3.5-2b-nvfp4 vram_usage_gb: 2.5
- Different quantization formats (tensorrt vs nvfp4)

**Impact:** Cannot accurately calculate VRAM budgets, loading strategies may fail.

---

### 5. Missing Error Handling in Core Flows - MISSING ERROR HANDLING
**Files:** Multiple

**Issue:** Several critical paths lack proper error handling:

#### 5a. vision_adapter.py
```python
def analyze_screenshot(image_path: str, task: str) -> ActionProposal:
    return StubVisionAdapter().analyze_screenshot(image_path=image_path, task=task)
```
- No handling if file doesn't exist
- No handling for image read errors
- Stub returns noop without warning

#### 5b. model_manager.py
```python
def inference(self, model_id: str, prompt: str, ...):
    # ...
    raise NotImplementedError("Inference via vLLM API not yet implemented")
```
- Inference method always raises NotImplementedError
- No fallback mechanism
- No graceful degradation

#### 5c. flow.py
```python
def run_single_cycle(task: str, execute: bool = False) -> dict[str, Any]:
    before = screenshot_full()  # No try/except
    proposal = analyze_screenshot(before.path, task)  # No error handling
    # ...
```
- No exception handling for screenshot failures
- No handling for analysis failures
- No cleanup on partial failure

#### 5d. cleanup.py
```python
def parse_timestamp_from_filename(filename: str) -> datetime:
    # ...
    except Exception as e:
        # Fallback to file mtime
        filepath = SCREENSHOT_DIR / filename  # BUG: filepath may not exist
```
- Bare except clause
- Potential path traversal issues
- No validation of filename format

**Impact:** System crashes on errors, partial state corruption, difficult debugging.

---

## 🟡 WARNING ISSUES

### 6. Hardcoded Paths - CODE QUALITY
**File:** `src/advanced_vision/cleanup.py` line 14

```python
SCREENSHOT_DIR = Path.home() / ".openclaw/workspace/plane-a/projects/advanced-vision/artifacts/screens"
```

**Issues:**
1. Path hardcoded to specific workspace location
2. Uses `.openclaw/workspace/plane-a` (hidden directory)
3. Won't work if project moved or on different machine
4. Should use relative path or config-based path

**Recommended Fix:**
```python
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "artifacts" / "screens"
```

---

### 7. Schema Version Mismatch
**File:** `config/model_registry.json` line 2

```json
"registry_version": "1.1.0"
```

**Issue:** No corresponding schema version in code to validate against. If registry format changes, code may break silently.

**Recommendation:** Add version validation in model_manager.py

---

### 8. Incomplete Trading Pipeline Integration
**File:** `src/advanced_vision/trading/` module

**Issues:**
1. `events.py` defines rich taxonomy but no consumers
2. `detector.py`, `reviewer.py`, `roi.py` may not fully implement event schema
3. No evidence that `TradingEvent` schema is actually used in screenshot analysis
4. Missing integration between screenshot artifacts and trading events

---

## 📋 ISSUE SUMMARY TABLE

| ID | Severity | Category | File(s) | Status |
|----|----------|----------|---------|--------|
| 1 | 🔴 Critical | Doc/Code Drift | model_registry.json, vllm.yaml | Open |
| 2 | 🔴 Critical | Schema Violation | schemas.py | Open |
| 3 | 🔴 Critical | Tag Misalignment | cleanup.py, schemas.py | Open |
| 4 | 🔴 Critical | VRAM Estimation | Multiple docs | Open |
| 5 | 🔴 Critical | Error Handling | Multiple files | Open |
| 6 | 🟡 Warning | Code Quality | cleanup.py | Open |
| 7 | 🟡 Warning | Schema Version | model_registry.json | Open |
| 8 | 🟡 Warning | Integration | trading/ module | Open |

---

## 🔧 RECOMMENDED FIX PRIORITY

### Phase 1 (Immediate)
1. **Align model configs** - Choose Qwen3.5-NVFP4 or Qwen2.5-VL, update both files
2. **Add error handling** to flow.py, vision_adapter.py critical paths
3. **Fix hardcoded path** in cleanup.py

### Phase 2 (Short-term)
4. **Add metadata fields** to schemas.py (artifact_id, plane, advisory, tags)
5. **Define canonical tag schema** and validate in cleanup.py
6. **Standardize VRAM estimates** across all documentation

### Phase 3 (Medium-term)
7. **Implement actual inference** in model_manager.py or remove stub
8. **Add schema version validation**
9. **Integrate trading events** with screenshot analysis pipeline

---

## 📁 FILES CHECKED

- ✅ config/model_registry.json
- ✅ config/vllm.yaml
- ✅ src/advanced_vision/schemas.py
- ✅ src/advanced_vision/models/model_manager.py
- ✅ src/advanced_vision/models/__init__.py
- ✅ src/advanced_vision/trading/events.py
- ✅ src/advanced_vision/cleanup.py
- ✅ src/advanced_vision/flow.py
- ✅ src/advanced_vision/vision_adapter.py
- ✅ src/advanced_vision/server.py
- ✅ src/advanced_vision/diagnostics.py
- ✅ src/advanced_vision/logging_utils.py
- ✅ src/advanced_vision/config.py
- ✅ docs/MODEL_SETUP_SUMMARY.md
- ✅ docs/VRAM_USAGE.md
- ✅ docs/SEQUENTIAL_LOADING.md
- ✅ docs/TENSORRT_OPTIMIZATION.md
- ✅ skill_manifest.json
- ✅ ISSUES.md (existing)

---

## 📝 NOTES FOR CODE AGENT

1. **Model Alignment Decision Needed:** Determine whether to use Qwen2.5-VL or Qwen3.5-NVFP4 as the canonical model set. Qwen3.5-NVFP4 appears to be the newer setup per MODEL_SETUP_SUMMARY.md.

2. **Schema Changes Impact:** Adding artifact_id, plane, advisory fields will require updates to:
   - All tool functions that create artifacts
   - cleanup.py metadata handling
   - Any downstream consumers

3. **VRAM Reconciliation:** Create single source of truth for VRAM estimates. Recommend adding to model_registry.json and generating docs from it.

4. **Error Handling Pattern:** Use structured error returns (not exceptions) for tool functions to maintain compatibility with MCP interface.

---

*Documented by: Aya*  
*Date: 2026-03-17*  
*Next Review: After fixes applied*
