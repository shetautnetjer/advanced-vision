# API Key Source Discovery

**Date:** 2026-03-16  
**Discovery:** User provided screenshot from kimi.com/code/console

---

## Key Finding

The API key (`sk-kimi-2WE2zm7...`) is from **Kimi Code** (kimi.com/code), NOT Moonshot!

**Screenshot Evidence:**
- URL: `kimi.com/code/console`
- Service: "KIMI Code"  
- Key Name: "openclaw"
- Created: 03/14/2025
- Model Access: K2.5 (Flagship Model)
- Status: Enabled

---

## Kimi Code vs Moonshot

| Service | URL | Purpose |
|---------|-----|---------|
| **Moonshot** | platform.moonshot.cn | General API platform |
| **Kimi Code** | kimi.com/code | IDE extension / coding assistant |

---

## API Endpoint Tests

**Kimi Code Endpoints:**
- `kimi.com/api/v1` → ❌ HTML (Cloudflare)
- `kimi.com/code/api/v1` → ❌ HTML
- `api.kimi.com/v1` → ❌ 404

**Kimi Code appears to be:**
- An IDE extension service
- Not a public REST API
- Uses different authentication than Moonshot

---

## Why OpenClaw Works

**Theory:** OpenClaw has a **special integration** with Kimi Code:

```
Your Key (Kimi Code) → OpenClaw Internal Routing → Kimi K2.5 Vision ✅
Your Key (Kimi Code) → Direct API Call → Moonshot → ❌ 0.00 CNY
```

OpenClaw likely:
1. Authenticates with Kimi Code internally
2. Routes to appropriate model (K2.5 with vision)
3. Handles credits/quota separately

---

## Implications

**For direct API use:** The key is tied to OpenClaw's infrastructure, not general Moonshot API access.

**For vision:** Works through OpenClaw native tools, not direct API calls.

**For standalone scripts:** Would need a separate Moonshot API key with general access.

---

## Recommendation

Use OpenClaw's native `image` tool for vision tasks — that's the intended path for this key.

The advanced-vision skill should integrate with OpenClaw's native tools rather than direct API calls.

---

*Documented by: Aya*  
*Date: 2026-03-16*
