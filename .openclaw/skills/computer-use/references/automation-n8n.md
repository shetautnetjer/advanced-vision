# automation-n8n

Use this only when the repo’s local-control lane is already stable enough to
justify automation.

## Good n8n Workflow Candidates

### 1. Workspace Health Check

Trigger:
- manual
- on startup
- scheduled

Steps:

1. run diagnostics in `.venv-computer-use`
2. run `mcporter config doctor`
3. run `mcporter list`
4. call `advanced-vision.screenshot_full`
5. write a small health summary

### 2. Registration Drift Check

Trigger:
- manual
- after env changes

Steps:

1. inspect project `config/mcporter.json`
2. inspect `mcporter config list`
3. flag if `advanced-vision` is missing or offline

### 3. Local-Control Smoke Loop

Trigger:
- manual

Steps:

1. capture screenshot
2. run a dry-run input action
3. verify screen-change path
4. archive artifacts and results

## What Not To Automate Yet

- heavyweight model benchmarking
- broad GPU model orchestration
- anything that depends on unstable or stale entry points

Keep automation focused on the boring operating path first.
