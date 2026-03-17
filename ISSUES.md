# Issues & Gaps - Advanced Vision

**Last Updated:** 2026-03-16  
**Agent:** Aya  
**Status:** Post Phase 1-4 Implementation

---

## ✅ RESOLVED

### 1. PyGetWindow Fails on Linux
**Issue:** `pygetwindow` raises `NotImplementedError` on Linux  
**Solution:** Installed `pywinctl` as cross-platform replacement  
**Status:** ✅ Working on X11 systems

### 2. MCP Server Not Registered
**Issue:** Server existed but wasn't usable as OpenClaw skill  
**Solution:** Registered with mcporter (`~/.openclaw/workspace-aya/config/mcporter.json`)  
**Status:** ✅ 10 tools available via `mcporter call`

### 3. Environment Not Operational
**Issue:** Unclear which Python env to use  
**Solution:** Verified `.venv-computer-use` with Python 3.11, all deps working  
**Status:** ✅ Dedicated computer-use runtime confirmed

---

## ⚠️ REMAINING GAPS

### P0 - Critical

#### 1. Vision Adapter is Stub
**File:** `src/advanced_vision/vision_adapter.py`  
**Issue:** Returns noop proposals, no real intelligence  
**Impact:** Cannot analyze screenshots or make decisions  
**Next Step:** Integrate actual vision model (Claude, GPT-4V, etc.)

### P1 - Architecture

#### 2. No Policy Envelope Support
**Issue:** Tools don't accept governance metadata  
**Impact:** Cannot integrate with governed orchestration (Arbiter's control plane)  
**Next Step:** Add `PolicyEnvelope` and `RequestContext` to all tool signatures

#### 3. No Dry-Run at MCP Level
**Issue:** Dry-run exists in Python code but not exposed via MCP  
**Impact:** Cannot preview actions through mcporter  
**Next Step:** Add `dry_run` parameter to MCP tool schemas

#### 4. No Artifact Retention Policy
**Issue:** Screenshots accumulate forever in `artifacts/screens/`  
**Impact:** Disk space unbounded, no cleanup  
**Next Step:** Implement retention module with TTL and classification

### P2 - Governance

#### 5. No Artifact Classification
**Issue:** Screenshots not tagged (public, private, sensitive)  
**Impact:** Cannot apply differentiated policies  
**Next Step:** Add classification tags to screenshot metadata

#### 6. Limited Provenance Logging
**Issue:** `artifacts/logs/actions.jsonl` incomplete  
**Impact:** Audit trail gaps  
**Next Step:** Ensure all actions logged with full context

---

## 🔧 PHASE 5 PENDING (Action Execution)

### Safe Testing Required

**Prerequisites before real execution:**
- [ ] Test `move_mouse` with small, safe movements
- [ ] Test `click` on harmless target (empty area)
- [ ] Test `type_text` in disposable scratch field
- [ ] Test `press_keys` with non-destructive combos
- [ ] Test `scroll` on safe window
- [ ] Verify screen changes with `verify_screen_change`

**Safety measures:**
- Use `pyautogui.FAILSAFE = True` (corner escape)
- Keep initial movements small (<100 pixels)
- Test on non-critical windows only
- Document flakiness vs stability

---

## 🐧 LINUX-SPECIFIC TRUTHS

### What's Reliable
- ✅ Screenshots (full screen and active window)
- ✅ Mouse movement by coordinates
- ✅ Keyboard input
- ✅ Basic scroll

### What's Limited
- ⚠️ Window enumeration (PyWinCtl works on X11, fails on Wayland)
- ⚠️ `getActiveWindow()` unreliable in terminal environments
- ⚠️ Window titles may not populate correctly

### Recommendation
Use **screenshot-based and coordinate-based workflows**, not window-dependent ones.

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 5: Prove Action Path
- [ ] Safe mouse movement test
- [ ] Safe click test
- [ ] Safe type test
- [ ] Screen change verification

### Phase 6: Tighten Linux Truth
- [ ] Document X11 vs Wayland limitations
- [ ] Mark window management as unreliable
- [ ] Emphasize coordinate-based workflows

### Phase 7: Integration Guidance
- [ ] Create OpenClaw skill manifest
- [ ] Document mcporter usage
- [ ] Example workflows

### Phase 8: Governance Seeds
- [ ] Policy envelope schema
- [ ] Artifact retention rules
- [ ] Classification system

---

## 🎯 NEXT IMMEDIATE ACTIONS

1. **Phase 5 testing** — Execute safe action tests
2. **Document Linux truth** — Update README with limitations
3. **Update README** — Add usage examples with mcporter
4. **Close gaps** — Address P0/P1 items based on priorities

---

## NOTES

- Environment: `.venv-computer-use` with Python 3.11
- Server: `advanced-vision-server` (stdio MCP)
- Tools: 10 available via mcporter
- Current working: Screenshots, dry-run, basic setup

*Reported by: Aya*  
*Date: 2026-03-16*
