# Antigravity IDE — Native Features for Screenshot Capture

**Discovery:** Antigravity has built-in browser/agent functionality

## What We Learned

### Antigravity Architecture

1. **IDE + Agent Panel** — Built-in Claude Opus 4.0 integration
2. **Native Browser** — Can spawn browser windows from within IDE
3. **Unified Workspace** — Code, browser, terminal, agent chat in one window

### Why Chrome Kept Appearing

- Antigravity's agent was opening browser windows
- Not separate Chrome — Antigravity's embedded browser
- Part of the IDE's integrated tooling

## Better Capture Strategy Using Antigravity

### Option 1: Use Antigravity Terminal

Antigravity has built-in terminal. Use it directly:

```bash
# Open terminal in Antigravity (Ctrl+`)
# Then run capture commands:

# Capture full IDE
import -window root antigravity_full.png

# Capture just the editor
import -window ID antigravity_editor.png
```

### Option 2: Use Antigravity's Agent

Ask the integrated agent to capture screenshots:

```
Agent: "Capture a screenshot of the current trading chart"
Agent: "Open TradingView and capture the chart panel"
```

The agent can:
- Open URLs in Antigravity's browser
- Capture screens
- Save to project folder

### Option 3: Antigravity Native Commands

Check if Antigravity has built-in screenshot:

```bash
# Look for antigravity CLI options
antigravity --help | grep -i screenshot

# Or check command palette (Ctrl+Shift+P)
# Type: "screenshot"
```

## Key Insight

**Don't fight Antigravity's architecture.**

Instead of:
- External Chrome + xdotool (works but messy)

Use:
- Antigravity's built-in browser (cleaner integration)
- Antigravity's terminal (already in project context)
- Antigravity's agent (AI-assisted capture)

## Recommended Workflow

### For Trading Screenshots:

```bash
# 1. In Antigravity terminal (Ctrl+`)
# Navigate to project
cd yolo_training/annotations/raw_images/

# 2. Use Python with mss for fast capture
python3 -c "
import mss
with mss.mss() as sct:
    sct.shot(output='capture_01.png')
"

# 3. Or use ImageMagick
import -window root capture_02.png
```

### For Antigravity UI Itself:

```bash
# Capture IDE with agent panel visible
# (Ensure IDE is focused, not browser tab)
import -window root antigravity_ui.png
```

## Advantages of Antigravity

| Feature | Benefit |
|---------|---------|
| Built-in browser | No window switching |
| Integrated terminal | Project context preserved |
| AI agent | Can automate capture sequences |
| Git integration | Screenshots auto-tracked |
| Workspace memory | Knows project structure |

## Next Steps

1. **Use Antigravity terminal** for capture commands
2. **Ask Antigravity agent** to open trading sites and capture
3. **Leverage integrated workflow** instead of external tools

## Summary

Antigravity isn't just an IDE — it's an **AI-powered workspace** with:
- Code editing
- Browser integration  
- Terminal access
- AI agent assistance
- Git/version control

All in one window. Use its native features for cleaner automation.
