# What's Next for Advanced Vision

**Date:** 2026-03-18  
**Status:** Phase 1 ~70% complete  
**Goal:** Train YOLO to detect 6 P0 UI classes

---

## Immediate Next Steps (This Week)

### 1. Label Screenshots
```bash
pip install labelImg
labelImg yolo_training/annotations/raw_images/active_session/
```

**Label 6 P0 Classes:**
| Class | ID | Status | Action |
|-------|----|--------|--------|
| chart_panel | 0 | ✅ Strong (17 images) | Verify bounding boxes tight |
| order_ticket | 1 | ⚠️ Weak (0 images) | Need to capture trading panels |
| primary_action_button | 2 | ⚠️ Weak (0 images) | Need Buy/Sell buttons visible |
| confirm_modal | 3 | ⚠️ Partial (tooltips) | Need confirmation dialogs |
| alert_indicator | 4 | ⚠️ Partial (alert areas) | Need active alert banners |
| position_panel | 5 | ⚠️ Partial (watchlists) | Need open positions view |

**Labeling Guidelines:**
- Tight bounding boxes (touch object edges)
- One box per instance
- Skip if <50% visible
- Minimum 20x20 pixels

### 2. Split by Session
```bash
# Manual split by time/session
train/  # Sessions A, B, C (70%)
val/    # Sessions D, E (15%)
test/   # Sessions F, G (15%)
```

**Critical:** Split by SESSION, not adjacent frames

### 3. Train YOLO Phase 1
```bash
./yolo_training/train_phase1_p0.sh
```

**Targets:**
- mAP@0.5 > 0.75
- Inference < 50ms
- False positives < 5%

---

## Short Term (Next 2 Weeks)

### 4. Capture Missing UI States
**Need login to capture:**
- TradingView paper trading (order tickets)
- MetaTrader 4/5 demo (Buy/Sell buttons)
- ThinkOrSwim paper (confirmation dialogs)

**Script:**
```bash
./tools/quick_capture.sh 50 2
```

### 5. Validate on Live UI
- Run trained YOLO on live trading screens
- Check detection accuracy
- Measure inference time
- Document false positives/negatives

### 6. Iterate
- Add more training data if mAP < 0.75
- Refine class definitions if ambiguous
- Expand to Phase 2 classes (buy_button, sell_button)

---

## Medium Term (Next Month)

### 7. Integrate into Hot Path
Replace stub YOLO with trained model:
```python
# Current (stub)
detections = mock_yolo.detect(frame)

# Target (trained)
model = YOLO('yolo_training/runs/phase1_p0_nano/weights/best.pt')
detections = model(frame)
```

### 8. End-to-End Testing
Full pipeline validation:
```
Capture → YOLO (real) → ROI extraction → Eagle → Governor → Action
```

**Success metrics:**
- Eagle gets better ROIs
- Fewer false escalations
- Faster correct understanding

### 9. Phase 2 Expansion
Add classes:
- buy_button / sell_button
- stop_loss_area / take_profit_area
- warning_badge

Only after Phase 1 stable.

---

## Long Term (Next Quarter)

### 10. Production Hardening
- TensorRT optimization for inference speed
- Multi-resolution training (4K, 1080p, 720p)
- Edge case handling (overlapping windows, blur)
- Continuous learning pipeline

### 11. Advanced Features
- Real-time cursor tracking integration
- Click-to-element mapping
- Hover state detection
- Action correlation (what happened after click)

### 12. Documentation
- Complete architecture docs
- Training playbook for new classes
- Performance benchmarks
- Deployment guide

---

## Current Blockers

| Blocker | Resolution |
|---------|------------|
| No order_ticket examples | Need login to TradingView/MetaTrader |
| No buy/sell buttons | Need trading interface visible |
| Cursor tracking | ✅ Solved (25 training images) |
| YOLO not trained | ✅ Pipeline ready, waiting for labels |

---

## Success Criteria

**Phase 1 Complete When:**
- ✅ mAP@0.5 > 0.75 on test set
- ✅ Inference < 50ms per frame
- ✅ Detects chart_panel reliably
- ✅ Works on live trading UI
- ✅ Integrated into hot path

**Ready for Phase 2 When:**
- Phase 1 stable for 1 week
- No critical false positives
- Performance validated under load

---

## Resources Ready

- **76 screenshots** captured
- **YOLO training pipeline** configured
- **6 P0 classes** defined
- **Labeling guide** in ANNOTATION_GUIDE_P0.md
- **Computer use tools** for capture
- **Governor** implemented and validated

---

## Call to Action

**Next immediate action:**
1. Open `labelImg`
2. Label first 20 screenshots
3. Save labels as YOLO format
4. Run training script
5. Check mAP

**Estimated time:** 2-3 hours for initial labeling

Ready to proceed? ✊🏾
