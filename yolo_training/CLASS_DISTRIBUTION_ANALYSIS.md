# Class Distribution Analysis - YOLO P0 Training Dataset

## Dataset Overview

| Metric | Value |
|--------|-------|
| **Total Images** | 50 |
| **Total Sessions** | 9 |
| **Train Images** | 43 (86%) |
| **Val Images** | 4 (8%) |
| **Test Images** | 3 (6%) |

## P0 Class Distribution

### Current Status: All Negative Examples

| Class ID | Class Name | Train | Val | Test | Total | Notes |
|----------|------------|-------|-----|------|-------|-------|
| 0 | chart_panel | 0 | 0 | 0 | 0 | No trading platform screenshots |
| 1 | order_ticket | 0 | 0 | 0 | 0 | No trading platform screenshots |
| 2 | primary_action_button | 0 | 0 | 0 | 0 | No trading platform screenshots |
| 3 | confirm_modal | 0 | 0 | 0 | 0 | No trading platform screenshots |
| 4 | alert_indicator | 0 | 0 | 0 | 0 | No trading platform screenshots |
| 5 | position_panel | 0 | 0 | 0 | 0 | No trading platform screenshots |

### Content Analysis

The current dataset contains general desktop environment screenshots:

| Content Type | Count | Description |
|--------------|-------|-------------|
| Login/Lock Screens | ~25 | Ubuntu/GNOME login screens with aurora background |
| File Manager | ~5 | File browser windows showing directories |
| VS Code: Editor | ~8 | Code editor with JSON/config files |
| Ubuntu App Center | ~5 | Software store interface |
| Desktop Background | ~5 | Empty desktop with wallpaper |
| Active Windows | 2 | Window-only captures (different modality) |

## Negative Example Value

While no P0 classes are present, these **50 negative examples** are valuable for:

1. **False Positive Prevention** - Teaching the model what NOT to detect
2. **Background Learning** - Understanding desktop UI patterns vs trading UI
3. **Context Discrimination** - Distinguishing general applications from trading platforms

## Recommended Class Collection Strategy

### Phase 1: Minimum Viable Dataset (Target)

To train a functional P0 detector, collect:

| Class | Minimum Images | Instances per Image | Total Instances |
|-------|---------------|---------------------|-----------------|
| chart_panel | 50 | 1 | 50 |
| order_ticket | 50 | 1 | 50 |
| primary_action_button | 50 | 1-2 | 75 |
| confirm_modal | 30 | 1 | 30 |
| alert_indicator | 30 | 1-3 | 60 |
| position_panel | 50 | 1 | 50 |

**Total: ~260 images with ~315 annotations**

### Suggested Collection Sources

1. **TradingView** - Web-based charts, order panels
2. **MetaTrader 4/5** - Classic forex trading UI
3. **ThinkOrSwim** - Advanced options trading platform
4. **Interactive Brokers TWS** - Professional trading UI
5. **Binance/Bybit** - Crypto exchange interfaces

### Collection Guidelines

```
For each trading platform:
  - Capture 10-20 different chart configurations
  - Include various order ticket states (buy/sell/pending)
  - Capture confirmation dialogs in different states
  - Include alert/warning scenarios (margin calls, etc.)
  - Vary window sizes and layouts
  - Mix light and dark themes
```

## Session-Based Split Strategy (Maintained)

| Split | Sessions | Images | Rationale |
|-------|----------|--------|-----------|
| **Train** | 5 sessions (02,03,04,05,06) | 43 | Diverse desktop scenarios, includes burst captures |
| **Val** | 2 sessions (01,07) | 4 | Early morning + VS Code: for variety |
| **Test** | 2 sessions (08,09) | 3 | Single capture + active window modality |

## Empty Label File Convention

All 50 images have empty `.txt` label files indicating negative examples:

```
data/labels/
  train/*.txt  (43 empty files)
  val/*.txt    (4 empty files)
  test/*.txt   (3 empty files)
```

## Next Steps

1. **Collect positive examples** from trading platforms
2. **Annotate with labelImg** or similar tool
3. **Maintain session-based splits** for new data
4. **Rebalance** when positive examples are added
5. **Target ratio**: 70% positive / 30% negative for production training

---
*Generated: 2026-03-18*
*Dataset: yolo_training/annotations/raw_images/*
