# API Key and Vision Capability Documentation

**Last Updated:** 2026-03-16  
**Research by:** Aya

---

## API Key Source

The API key (`REDACTED`) was **NOT obtained from Moonshot directly** by the user.

It works on Moonshot endpoints but has **limited access**.

---

## Tested Endpoints

| Endpoint | Status | Works with Key? | Vision? |
|----------|--------|-----------------|---------|
| `api.moonshot.cn/v1` | ✅ | Yes | ❌ Text-only |
| `api.us.moonshot.cn/v1` | ✅ | Yes | ❌ Text-only |
| `api.kimik2ai.com/v1` | ❌ | DNS failed | N/A |
| `kimik2ai.com/api/v1` | ❌ | DNS failed | N/A |
| `api.kimi.ai/v1` | ❌ | 404 | N/A |
| `kimi.ai/api/v1` | ❌ | 502 | N/A |
| `api.openai.com/v1` | ❌ | 401 | N/A |

---

## Account Status

```
Account ID: cuvk5mcgv2aq6b702ogg
Available Balance: 0.00 CNY  ← INSUFFICIENT FOR VISION
Available Models: moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k (text-only)
```

**Text-only models work** because they're cheaper/free.

**Vision models (kimi-vl, kimi-k2-5 with vision) require paid credits.**

---

## What Works

### ✅ Text-Only API Calls
```python
# Works with 0.00 CNY balance
client.chat.completions.create(
    model='moonshot-v1-8k',
    messages=[{'role': 'user', 'content': 'Hello'}]
)
```

### ❌ Vision API Calls
```python
# FAILS with 0.00 CNY balance
client.chat.completions.create(
    model='kimi-k2-5',  # or kimi-vl
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': 'Describe image'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,...'}}
        ]
    }]
)
# Error: insufficient_balance
```

### ✅ OpenClaw Native Vision
```python
# WORKS through OpenClaw's internal credentials
image(path='video.mp4', prompt='Describe this video')
# Uses Kimi K2.5 with vision through OpenClaw's arrangement
```

---

## Solutions

### Option 1: Add Credits to Moonshot Account
1. Go to: https://platform.moonshot.cn/billing
2. Add payment method
3. Purchase credits
4. Vision API will work with direct API calls

### Option 2: Use OpenClaw Native
- Vision works through `image` tool (native OpenClaw)
- No additional credits needed
- Limited to OpenClaw session context

### Option 3: Obtain Vision-Enabled API Key
- Get a key from an account with vision access
- Or use a different provider (OpenAI GPT-4V, Anthropic Claude, etc.)

---

## Current Implementation Status

The `video.py` module is **built and ready** but requires one of the above solutions to enable vision.

**Working features (no vision):**
- ✅ Screen recording (MP4)
- ✅ Frame extraction (PNG)
- ✅ Video file management
- ✅ Metadata logging

**Requires credits/vision access:**
- ❌ Direct video analysis via Kimi API
- ❌ GIF understanding via API
- ❌ Image sequence analysis

---

## Recommendations

**For immediate use:** Use OpenClaw native `image` tool for vision tasks.

**For standalone API use:** Add credits to Moonshot account or obtain vision-enabled key.

**For production:** Consider multiple provider fallback (Moonshot + OpenAI + Anthropic).

---

*Documented by: Aya*  
*Date: 2026-03-16*
