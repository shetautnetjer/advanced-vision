# Tasks

## Immediate

- [x] Inspect repository structure
- [x] Read core implementation files
- [x] Read tests
- [x] Identify runtime blockers on this host
- [x] Document architecture direction
- [x] Create `brain/` working notes
- [ ] Update README to use `python3`
- [ ] Add diagnostics script/command
- [ ] Create virtualenv
- [ ] Install project dependencies
- [ ] Run tests
- [ ] Start MCP server

## Runtime validation

- [x] Validate `screenshot_full`
- [x] Validate `screenshot_active_window`
- [x] Validate `list_windows` (currently returns 0 windows on this host)
- [x] Validate `verify_screen_change`
- [x] Validate `run_single_cycle(execute=False)`
- [ ] Validate controlled input tools in safe context
- [ ] Install `python3-tk` / `python3-dev` and re-test input tools

## Governance improvements

- [ ] Add policy/request envelope support
- [ ] Add artifact retention settings
- [ ] Add no-persist / short-TTL screenshot mode
- [ ] Add dry-run support for action tools
- [ ] Add richer provenance logging

## Vision improvements

- [ ] Keep stub as default
- [ ] Design real adapter interface implementation
- [ ] Add redaction/cropping policy before external model use
- [ ] Log provider/egress decisions
