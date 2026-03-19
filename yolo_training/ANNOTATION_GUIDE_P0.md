# P0 Narrow Class Set — Annotation Guide (Phase 1)

## Goal
Train YOLO to reliably box the main regions that matter for the scout/reviewer loop.

**Not:** Detect every button, icon, and pattern.
**Yes:** Find where the chart is, where the ticket is, where the action button is.

---

## The 6 P0 Classes

### 0: chart_panel
**What:** Main price chart area (candlesticks, lines, volume)

**Include:**
- Full chart region including price axis
- Multiple chart windows if side-by-side

**Exclude:**
- Just the chart title bar
- Indicators/RSI panel below (that's separate)

**Tips:**
- Box should touch the chart boundaries
- Include the full width and height of the price display

---

### 1: order_ticket
**What:** Buy/Sell order entry panel (the ticket you place trades in)

**Include:**
- Full ticket panel with all fields
- Market/limit order selectors
- Price input, quantity input
- Buy/Sell buttons (but mark `primary_action_button` separately if prominent)

**Exclude:**
- Just the title bar
- Collapsed/minimized state

**Tips:**
- This is distinct from `position_panel` (ticket = placing orders, position = existing trades)

---

### 2: primary_action_button
**What:** Main CTA — the button that triggers the key action

**Include:**
- "Buy" button (large, prominent)
- "Sell" button (large, prominent)
- "Close Position" button
- "Confirm" button in dialogs
- "Place Order" submit button

**Exclude:**
- Small utility buttons (settings, minimize)
- Checkbox toggles
- Dropdown selectors

**Tips:**
- Only the PRIMARY action, not every button
- Should be the button the user is most likely to click

---

### 3: confirm_modal
**What:** Confirmation dialogs, popups, alerts that block the flow

**Include:**
- "Are you sure?" dialogs
- "Order placed successfully" notifications
- Error/warning popups
- Margin call alerts
- Position close confirmation

**Exclude:**
- Passive toasts that don't block
- Tooltip hovers

**Tips:**
- These are critical for the governor — block/warn decisions often depend on modals

---

### 4: alert_indicator
**What:** Warning badges, notification dots, status indicators

**Include:**
- Red warning triangles
- "Margin Call" badges
- Connection lost indicators
- New notification dots
- High spread warnings

**Exclude:**
- Passive color changes (green/red PnL)
- Static labels

**Tips:**
- Small but important — these often trigger reviewer escalation

---

### 5: position_panel
**What:** Open positions widget, PnL display, trade list

**Include:**
- "Positions" tab content
- Open trade list with PnL
- Current exposure summary
- Running profit/loss display

**Exclude:**
- History/closed trades (that's different)
- Account balance (not position-specific)

**Tips:**
- Distinct from `order_ticket` — position = existing, ticket = new

---

## Dataset Rules (Critical)

### Rule 1: Split by Session
**WRONG:** Adjacent frames in same session go to train AND test  
**RIGHT:** 
- Train: Sessions A, B, C
- Val: Sessions D, E  
- Test: Sessions F, G

**Why:** Adjacent frames look similar. Metrics will be inflated if you split by frame.

### Rule 2: Include Negatives
You NEED screenshots where:
- ✅ Nothing important changed (just noise)
- ✅ Only cursor moved
- ✅ Chart scrolled but no actionable event
- ✅ Overlapping windows obscure the UI
- ✅ Blur, compression, partial visibility

**Why:** Teaches the detector what NOT to fire on. Prevents false positives.

---

## Annotation Best Practices

### Bounding Box Quality
- **Tight:** Edges touch object boundaries
- **Complete:** Don't cut off parts of the object
- **Single:** One box per instance (don't double-label)

### Occlusion Handling
- **50%+ visible:** Annotate
- **<50% visible:** Skip (don't guess)
- **Overlapping:** Box each separately if distinguishable

### Small Objects
- Minimum 20x20 pixels for reliable detection
- Alert indicators can be smaller but may be harder to detect

---

## Success Metrics (Phase 1)

**Don't just chase mAP.** Measure:

| Metric | Target | Why |
|--------|--------|-----|
| mAP@0.5 | > 0.75 | Good enough reliability |
| Inference | < 50ms | Real-time hot path |
| False Positives | < 5% | Don't spam the reviewer |
| Eagle ROI Quality | Better | ROIs actually contain useful info |
| Escalations | Fewer | Less noise for governor |

---

## Phase 2 Classes (Later)
After Phase 1 is stable, add:
- `buy_button` (distinct from generic primary_action)
- `sell_button`
- `stop_loss_area`
- `take_profit_area`
- `warning_badge` (more specific than alert_indicator)

## Phase 3 Classes (Maybe Never)
Only if still needed:
- Support/resistance lines
- Candlestick patterns
- Chart state indicators

**Why maybe never:** Eagle can handle pattern recognition. YOLO should focus on UI structure.

---

## Quick Reference Card

```
chart_panel        → Where is the price chart?
order_ticket       → Where do I place a trade?
primary_action_button → What button triggers the action?
confirm_modal      → Is there a blocking dialog?
alert_indicator    → Is there a warning I should see?
position_panel     → Where are my open trades?
```

---

## Labeling Workflow

1. Open labelImg: `labelImg yolo_training/annotations/raw_images`
2. Set format: YOLO (Ctrl+Shift+Y)
3. For each screenshot:
   - Look for the 6 P0 classes
   - Draw tight bounding boxes
   - Assign correct class ID (0-5)
   - Save (Ctrl+S)
4. Split by session into train/val/test
5. Train: `yolo detect train data=yolo_training/data_phase1_p0.yaml model=yolov8n.pt epochs=100`

---

**Remember:** We're training a perception component for an agent, not a general detector. Optimize for downstream usefulness, not just detection metrics.
