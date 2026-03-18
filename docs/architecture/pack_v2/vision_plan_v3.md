# vision_plan.md
**Project:** AI Agent Frame — Vision Watcher + Targeted Segmentation + Video Tracking + Safe Escalation  
**Primary goal:** Build a local-first vision “watcher” loop that can **track important UI regions over time**, **detect risk/anomalies**, **record forensic clips**, and **escalate safely** to stronger models (local thinking + Kimi cloud) without leaking sensitive info.

---

## 0) One-page summary (what we’re building)

### What it does
- Watches a live screen/app (trading charts, web UIs, dashboards).
- Uses **SAM3** to **track targeted regions** across frames (stable track IDs).
- Uses **Qwen3-VL-2B-Instruct** as the **watcher brain** to interpret tracked regions and produce **small structured events**.
- Keeps a rolling **ring buffer** (last 30–120s). When risk triggers, it **commits a clip + keyframes + ROI crops**.
- Optionally escalates:
  - **Local “thinking” vision model** for deeper analysis (still local).
  - **Kimi K2.5 (cloud)** for **high-resolution forensic review** and **teaching feedback**.
- Stores “experience memory” in **LanceDB**:
  - ROI crops (chart panel, ticket, confirmation modal)
  - embeddings (from a dedicated embedder)
  - metadata + outcomes (labels)
- Uses a **retrieval + rerank** pattern to find similar past scenarios.

### What it’s not
- Not placing trades automatically by default.
- Not storing raw web text into trusted code context.
- Not pushing unredacted screenshots/clips to cloud.

---

## 1) Core principles (non‑negotiables)

### 1.1 Two trust zones (your “KA” rule)
**Plane A — Research Lab (Untrusted)**
- Raw web, public chat logs, unknown pages, third-party prompt content
- Output only to `research_inbox/`  
- Must be sanitized/verified before promotion

**Plane B — Build & RAG Workshop (Trusted)**
- Code execution, tests, commits, trusted RAG indexes
- Can retrieve only from `repo_index` + `research_index_approved`

### 1.2 Safe escalation
- Local watcher can record and summarize.
- Cloud escalation receives only **sanitized + minimal** artifacts:
  - redacted clip
  - cropped ROIs
  - watcher timeline JSON
  - minimal metadata

### 1.3 Model roles are specialized (no mixing)
- **Watcher model** (fast) ≠ **Embedder model** ≠ **Reranker**
- Reranker produces **scores** (not vectors).
- Embedders produce vectors with a defined dimension (must match DB schema).

---

## 2) Models and responsibilities

### 2.1 SAM3 (segmentation + tracking)
**Purpose:** Provide stable **track IDs + masks/bboxes** over time so UI regions remain consistent frame-to-frame.

**Used for:**
- Targeted region tracking: chart panel, ticket panel, confirm modal, P&L widget
- Video tracking: stable identities across frames
- Optional: keyframe selection (large region change)

**Outputs:**
- `track_id`, `bbox`, `mask_rle` (or polygon), `confidence`

### 2.2 Qwen3‑VL‑2B‑Instruct (local watcher)
**Purpose:** Constantly evaluate the tracked regions, produce structured events, and decide when to escalate/stop.

**Used for:**
- State classification: ok / uncertain / unsafe / escalate
- UI sanity checks: symbol, side, size, fees, slippage warnings, route warnings
- Detect “unknown modal,” “price jump,” “spread widening,” “confirmation required,” etc.

**Output:** small JSON events (no giant narrative).

### 2.3 Embedder model (local) + LanceDB
**Purpose:** Store searchable “experience” (ROIs) as vectors + metadata.

Recommended:
- If you want the 2B tier: **Qwen3‑VL‑Embedding‑2B** (max dim typically 2048; you can choose smaller dims for speed/space).
- If you ever want higher recall/expressiveness: Embedding‑8B (up to 4096).

**Important:** The constant must match the embedder’s output dim.
- Example: `EMBED_DIM = 2048` (for Embedding‑2B at full size)

### 2.4 Qwen3‑VL‑Reranker‑2B (local)
**Purpose:** Re-rank candidates found by vector search.
- Input: (query, candidate doc/ROI)
- Output: a relevance score  
**No embedding dims needed.**

### 2.5 Kimi K2.5 (cloud escalation / high-res)
**Purpose:** High-resolution forensic review + teaching feedback.
- “Why did the watcher fail?”
- “What should it track next time?”
- “What prompt template would reduce hallucination?”
- “What harness labels should we add?”

---

## 2.6 Optional “Tripwire + Precision + Reader” stack (recommended)

This is the **three-piece** vision stack that works especially well for **live trading charts** and **complex UIs**:

### A) YOLO (Tripwire / change detector)
- **Job:** Ultra-fast detection of “something changed” (new window/modal, dropdown opened, warning badge appears).
- **Output:** rough bounding boxes + class labels (e.g., `modal`, `button`, `warning`, `chart_area`).
- **Why:** Keeps SAM3 asleep most of the time so you don’t burn GPU on heavy tracking.

> Note: you can also replace YOLO with a cheaper “frame-diff tripwire” if you only need “change/no-change”.

### B) SAM3 (Precision tracker + ROI isolator)
- **Job:** When tripwire triggers, **lock onto the specific object** and track it across a short clip.
- **Superpower:** **Promptable Concept Segmentation (PCS)** — text prompts like “confirmation button” or “order ticket” can segment + track all instances of that concept in video. (Works best with per-app prompt libraries and/or visual exemplars.)
- **Output:** pixel-level masks + stable track IDs.

### C) OmniParser (UI reader / structure)
- **Job:** Convert UI screenshots into a **structured representation** (DOM-like elements + text + bounding regions).
- **Why:** Neither YOLO nor SAM3 “reads” text; OmniParser is purpose-built for UI semantics and grounding.

### Where Qwen3‑VL and Kimi fit
- **Qwen watcher** gets *only* the isolated ROI clip + OmniParser structure (less visual noise → fewer hallucinations).
- **Kimi (cloud)** gets the sanitized forensic bundle when needed (high-res troubleshooting + coaching).


---

## 3) Data flow architecture

```
[Screen Capture] -> [SAM3 Track Targets] -> [ROI Crops] -> [Watcher (Qwen3-VL-2B)]
                                          |                     |
                                          |                     v
                                          |             [Event Timeline JSON]
                                          |                     |
                                          v                     v
                                   [Ring Buffer] ----> [Escalation Trigger?]
                                          |                     |
                                          | yes                 | no
                                          v                     v
                         [Commit Clip + Keyframes + ROIs]     [Continue]
                                          |
                                          v
                            [Redact/Sanitize Bundle (local)]
                                          |
                                          +--> [Local Thinking Vision (optional)]
                                          |
                                          +--> [Kimi K2.5 Cloud (optional)]
                                          |
                                          v
                        [LanceDB Upsert: embeddings + metadata + outcomes]
                                          |
                                          v
                 [Retrieve Similar] -> [Rerank] -> [Explain / Coach / Improve Prompts]
```

---

## 4) Minimal viable file layout (local-first)

```
vision/
  capture/
    frames/                 # optional (usually keep in memory, write only on escalation)
    clips/                  # committed clips (sanitized)
    keyframes/              # extracted frames
    rois/                   # cropped regions (chart, ticket, modal, pnl)
  models/
    sam3/                   # local configs
    watcher_qwen2b/          # watcher configs + prompts
    embedder/               # embed model config (2B or 8B)
    reranker/               # reranker config
  pipeline/
    langgraph/              # graph definition + node contracts
    redaction/              # blur rules + OCR-based PII detection
    scoring/                # outcomes, labels, eval metrics
  storage/
    lancedb/
      trusted/              # Plane B
      untrusted/            # Plane A (optional)
  logs/
    watcher_events.jsonl
    sam_tracks.jsonl
    escalation_manifest.jsonl
  docs/
    vision_plan.md
```

---

## 5) Schemas (the stuff that makes the system dependable)

### 5.1 Track output schema (SAM3 → pipeline)
```json
{
  "ts_ms": 1730000000123,
  "frame_id": 98123,
  "source": "screen0",
  "tracks": [
    {"track_id": "chart_panel", "bbox": [x,y,w,h], "mask": "...", "conf": 0.93},
    {"track_id": "confirm_modal", "bbox": [x,y,w,h], "mask": "...", "conf": 0.88}
  ]
}
```

### 5.2 Watcher event schema (Qwen3‑VL‑2B → pipeline)
```json
{
  "ts_ms": 1730000000456,
  "frame_id": 98123,
  "state": "ok | uncertain | unsafe | escalate",
  "confidence": 0.86,
  "reasons": [
    "confirm_popup_detected",
    "slippage_warning_present",
    "symbol_mismatch_detected"
  ],
  "targets_to_track": ["chart_panel", "order_ticket", "confirm_modal", "pnl_widget"],
  "evidence": [
    {"track_id": "confirm_modal", "claim": "modal says Confirm", "conf": 0.81}
  ],
  "actions": [
    {"type": "pause", "why": "needs_approval"},
    {"type": "commit_clip", "seconds": 45}
  ]
}
```

### 5.3 Escalation manifest schema (what gets uploaded / saved)
```json
{
  "manifest_id": "esc_2026_02_20_001",
  "window": {"pre_s": 30, "post_s": 15},
  "clip_path": "vision/capture/clips/esc_...mp4",
  "keyframes": [".../kf_001.png", ".../kf_002.png"],
  "roi_crops": [{"track_id":"chart_panel","path":".../chart.png"}],
  "redaction": {"performed": true, "ruleset":"default_v1"},
  "watcher_summary_path": "logs/watcher_events_slice.jsonl",
  "risk_level": "MED",
  "approved_for_cloud": false
}
```

---

## 6) LanceDB layout (experience memory)

### 6.1 Why store ROIs instead of full frames
- Smaller, cheaper, less sensitive
- Higher signal (chart panel vs entire desktop)

### 6.2 Tables (recommended)
**Table: `vision_rois_trusted`**
- `id` (uuid)
- `ts_ms`, `frame_id`, `source_app`, `symbol`, `timeframe`
- `track_id` (chart_panel / order_ticket / confirm_modal / pnl_widget)
- `roi_path` (local path)
- `embedding` (vector[EMBED_DIM])
- `watcher_state`, `reasons[]`
- `outcome_label` (win/loss/abort/error/unknown)
- `risk_level`
- `manifest_id` (optional)

**Table: `vision_rois_untrusted`**
- same schema, but only for quarantined data (public web pages, unknown UIs)

### 6.3 Embedding dimensions (do this right)
- Reranker does not define dims.
- **Embedder defines dims**.
  - If you use Embedding‑2B at full size: `EMBED_DIM = 2048`
  - If you use Embedding‑8B: `EMBED_DIM = 4096`
- “1152” is not the DB vector dim you store in LanceDB.

---

## 7) The LangGraph graph (video tracking + targeted segmentation)

### 7.1 State object (shared across nodes)
```python
state = {
  "frame": <image>,
  "frame_id": int,
  "ts_ms": int,
  "targets": ["chart_panel", "order_ticket", ...],
  "tracks": [{"track_id":..., "bbox":..., "mask":..., "conf":...}],
  "rois": [{"track_id":..., "crop":<image>, "bbox":...}],
  "watcher_event": {...},
  "ring_buffer": {...},
  "escalate": bool,
  "manifest": {...}
}
```

### 7.2 Nodes (MVP)
1) `capture_frame`
2) `sam3_track_targets`
3) `crop_rois`
4) `watcher_infer`
5) `update_ring_buffer`
6) `decide_escalation`
7) `commit_clip_and_keyframes` (only if escalate)
8) `redact_bundle` (only if escalate)
9) `embed_and_upsert_lancedb` (optional continuous or only on commit)
10) `retrieve_similar_and_rerank` (optional on demand)
11) `escalate_to_cloud` (gated)

### 7.3 Edges (simplified)
- `capture_frame -> sam3_track_targets -> crop_rois -> watcher_infer -> update_ring_buffer -> decide_escalation`
- If `escalate`:
  - `commit_clip_and_keyframes -> redact_bundle -> (local_thinking?) -> (cloud?) -> embed_and_upsert`
- Else loop back to `capture_frame`

---

## 7.4 Concurrency layout (Rust, Rayon/Crossbeam)

This layout keeps **60 FPS capture** smooth while allowing heavy inference only when needed:

- **Thread A — Capture (real-time):**
  - grabs frames at 60 FPS
  - writes into the preallocated ring buffer
  - emits lightweight “frame available” signals (no copies)

- **Thread B — Tripwire (cheap):**
  - frame-diff / tiny detector / lightweight YOLO
  - decides whether to trigger “analysis window”

- **Thread C — SAM3 Worker (on trigger):**
  - pulls a time-slice from the ring
  - downsamples (FPS and/or resolution)
  - runs SAM3 tracking → stable masks/track IDs

- **Thread D — Watcher Worker (on trigger or periodic):**
  - consumes ROIs (cropped) + optional OmniParser output
  - runs Qwen3‑VL watcher → JSON timeline events

- **Thread E — Encoder/Commit (on escalation):**
  - commits sanitized clip + keyframes + ROI crops
  - uses NVENC/hardware encode if available
  - writes manifest + logs

**Crossbeam channels** are great for signaling; the ring buffer should be index-based to avoid moving big frame blobs through channels.


---


## 8) Ring buffer design (forensic clips without huge storage)

### 8.0 Default target (human-smooth baseline)
**Target:** **60 FPS** capture with a **10‑second** rolling buffer (smooth enough for a human to “see it happen”).  
That’s **600 frames** in the ring.

You can still *analyze* at a lower rate (5–10 FPS) on trigger — but **capture** stays smooth.

### 8.0.1 Memory math (why 60 FPS × 10 s is still fine on 64 GB RAM)
If you store frames as **RGB8** (3 bytes/pixel):

- **1080p (1920×1080):** ~6.2 MB/frame → 600 frames ≈ **3.7 GB**
- **1440p (2560×1440):** ~11.1 MB/frame → 600 frames ≈ **6.6 GB**
- **4K (3840×2160):** ~24.9 MB/frame → 600 frames ≈ **15.0 GB**

✅ With **64 GB RAM**, even 4K is feasible from a pure capacity standpoint.

**Best practice:** store frames as **NV12/YUV** (often ~½ the memory + bandwidth of RGB), and only convert to RGB when a model actually needs it.

### 8.0.2 Bandwidth math (why the CPU can keep up)
Approx sustained write rates (raw frames):

- **1080p RGB @ 60 FPS:** ~6.2 MB × 60 ≈ **372 MB/s**
- **4K RGB @ 60 FPS:** ~24.9 MB × 60 ≈ **1.5 GB/s**

Your DDR5 system can move this comfortably — the real danger is **extra copies/allocations**, not the ring buffer itself.

### 8.0.3 The “no‑stutter” implementation rules (Rust)
To keep capture truly 60 FPS:
- **Preallocate** the full ring buffer up front (no heap allocs per frame).
- Use **one writer** (capture thread) and many readers via indices (avoid locks on the hot path).
- Store in a **compact pixel format** (NV12) when possible.
- Avoid per‑frame conversions; do them **only on trigger**.
- Never block capture on disk I/O:
  - If you commit a clip, hand frames to an encoder thread.
  - Prefer **NVENC** (GPU hardware encode) for fast commits that don’t stall capture.

### 8.0.4 Triggered analysis (keep heavy work off the hot path)
When YOLO (or frame-diff) triggers:
- slice the last 10 seconds from the ring (still in RAM)
- **downsample** to ~5–10 FPS for SAM3 tracking
- keep **full-res keyframes/ROIs** for Kimi forensic review



---

## 9) Redaction & sanitization (cloud-safe)

### 9.1 Redaction rules (default_v1)
Blur/blackout:
- wallet addresses
- account numbers
- emails
- names
- browser URL bar
- OS notifications
- API keys (never store)

### 9.2 How to do it
- OCR pass on keyframes/ROIs to find patterns
- Mask regions matching patterns
- Store unredacted only in trusted local storage with strict perms

### 9.3 Promotion pipeline for “approved knowledge”
- Raw watcher clips → `research_inbox/` (quarantined) if they include unknown content
- Summarize + verify → `research_approved/`
- Embed only approved summaries into `research_index_approved`

---

## 10) Using this for trading + RL harness

### 10.1 What gets labeled
Each event window can get:
- outcome label: win/loss/abort/error
- volatility regime label
- UI integrity label: ok/suspicious/broken
- “trade quality” label: A+/B/C
- “watcher correctness” label: correct/false positive/false negative

### 10.2 Reward shaping hooks
- entry timing vs subsequent MFE/MAE
- time-to-profit
- slippage vs expected
- avoidable errors (wrong symbol, wrong size)

### 10.3 Chronos + watcher hybrid
- Chronos predicts numeric future (price/vol)
- Watcher extracts visual state (pattern/structure/UI state)
- Combine as features in a scorer (XGBoost / PPO)
- Store every episode slice in LanceDB for retrieval + postmortems

---

## 11) “Teaching Qwen” via Kimi coaching

### 11.1 Coaching bundle (what Kimi receives)
- sanitized clip + keyframes
- ROI crops (chart, ticket, confirm)
- watcher timeline
- question prompts:
  - “Where did the watcher miss evidence?”
  - “What should be tracked next time?”
  - “What prompt template reduces uncertainty?”

### 11.2 Prompt tactics that improve watcher reliability
- Checklist prompts (symbol/side/size/fees/slippage)
- Counterfactuals (“if unsafe, what would appear?”)
- Evidence-first (“list evidence before conclusion”)
- Calibrated confidence (“what would raise confidence from 0.7 to 0.9?”)

### 11.3 How learning is promoted safely
- Kimi produces suggestions → quarantined summary
- Local verifier promotes only clean, actionable templates into trusted docs
- No raw web content becomes code instructions

---

## 12) Operating mode presets

### 12.1 Trading mode (high sensitivity)
- **Capture:** 60 FPS, 10s ring buffer
- **Analyze:** 5–10 FPS on trigger (SAM3/Qwen)

- Higher FPS
- Track fewer ROIs but more consistently
- Aggressive escalation on uncertainty

### 12.2 UI reverse-engineering mode (exploration)
- **Capture:** 60 FPS (or 30 FPS if you prefer), 10s ring buffer
- **Analyze:** periodic + on-trigger; store more ROIs for learning

- Lower FPS
- More targets + periodic “segment everything” checks
- Store more ROIs for future retrieval

### 12.3 Demo/video creation mode
- Always commit clips
- Heavier keyframe extraction
- Kimi used frequently for narrative/video assembly

---

## 13) Performance notes (your hardware)

**Rule of thumb:** keep **capture + buffering** on CPU at full rate (60 FPS), and run **SAM3/Qwen/OmniParser** only on trigger (downsampled). This prevents stutter and keeps VRAM stable.

- LanceDB stores vectors on disk; RAM helps caching/indexing.
- GPU VRAM is used mainly for model inference, not vector storage.
- Keep watcher cheap (2B) and escalate only when needed.

---

## 13.1 SAM3 tracking performance & VRAM safety (practical rules)

### Ring buffer RAM math (why RAM is fine)
For 1080p (1920×1080) **RGB8** frames:
- bytes per frame ≈ 1920×1080×3 ≈ 6.2 MB
- 30 FPS × 10 seconds = 300 frames → ≈ 1.86 GB in RAM

This fits comfortably in 64 GB RAM, especially if you store frames in NV12/YUV or compress after commit.

### VRAM pitfalls (why SAM3 can OOM)
SAM3 video tracking uses an `inference_state` memory bank that can grow with:
- number of frames you pass
- number/complexity of tracked objects
- resolution

### Two proven fixes
1) **Downsample the clip for SAM3**
   - Keep full-res frames in the ring buffer (RAM).
   - When triggered, downsample to ~**5 FPS** (or adaptive FPS) and/or downscale resolution for SAM3 tracking.
2) **CPU offload options**
   - Use `offload_video_to_cpu=True` (and optionally async frame loading) so cached frames aren’t all held in VRAM.


---

## 14) Testing & evals (so it doesn’t lie)
**Unit tests**
- schema validation for track/events
- redaction rules (regex + OCR)
- ring buffer commit boundaries

**Integration tests**
- run on a recorded screen video
- ensure same event triggers produce same manifests

**Metrics**
- false positive rate (unnecessary escalations)
- false negative rate (missed unsafe states)
- time-to-detect (latency)
- rerank effectiveness (MRR/NDCG on labeled episodes)

---

## 15) Ralph Wiggum loop template (iteration discipline)

Every iteration:
- **Goal (1–3 bullets)**
- **Risk level** + why
- **Actions/commands run**
- **Results**
- **Files changed**
- **Next step / ✅DONE**

---

## 16) Milestones (recommended sequence)


### M‑0.5 — 60 FPS ring buffer benchmark (acceptance test)
Before model work, validate the “human-smooth” foundation:

- Target: **1080p @ 60 FPS**, **10-second** ring buffer (600 frames), **0 dropped frames**
- Metrics to log:
  - capture loop latency/jitter (ms)
  - dropped frames count
  - ring overwrite correctness
  - CPU usage of capture thread
  - memory usage

Then scale up to 1440p/4K and/or switch to NV12 to reduce bandwidth.


### M0 — Playback-only MVP (no live screen)
- Run pipeline over a recorded MP4
- Validate: tracking → watcher events → clip commit → manifest

### M1 — Live screen capture + ring buffer
- Minimal targeted tracking: chart panel only
- Commit on “modal detected” or “confidence drop”

### M2 — Redaction + cloud escalation gate
- Create sanitized bundle
- Manual approval switch before upload

### M3 — LanceDB memory + retrieval
- Upsert ROI embeddings + metadata
- Retrieve similar + rerank

### M4 — Coaching loop
- Kimi produces prompt improvements
- Promote verified templates to trusted knowledge

---

## 17) Open decisions (we’ll lock these next)
- FPS targets per mode
- Default ring buffer length
- ROI target list per app (Tradovate / Robinhood / browser)
- Embedder dimension choice (2048 vs 4096) based on scale + quality needs
- Index type in LanceDB (HNSW vs IVF_PQ vs quantization) based on expected vector count
