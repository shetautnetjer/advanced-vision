# ML Home

This directory is the future implementation-facing home for ML work in
`advanced-vision`.

## Purpose

Keep ML planning and future code structure separate from:

- `models/` for downloaded weights, assets, and third-party checkouts
- root-level operational docs for the current computer-use-first lane

## Layout

- `adapters/`
  - future model adapter interfaces and integration shims
- `experiments/`
  - bounded experiments and evaluation code
- `notes/`
  - ML-specific design notes and decision records
- `hotpaths/`
  - future performance work, including optional Rust exploration

## Current Rule

Python remains the default language for current repo work.

If a future hot path justifies Rust or another systems language, document the
reason and boundary first instead of mixing it into the active control lane.
