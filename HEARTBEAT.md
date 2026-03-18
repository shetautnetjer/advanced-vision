# Heartbeat Configuration for Advanced Vision

## Periodic Checks

### Every 30 minutes
- [ ] Check for new commits needing push
- [ ] Verify WSS v2 server health (port 8000)
- [ ] Monitor disk space (models/logs)

### Every 2 hours
- [ ] Review ARCHITECTURE_GAP status
- [ ] Check for pending validation tasks
- [ ] Verify schema compliance in new code

### Daily
- [ ] Reconcile truth layer completeness
- [ ] Review artifact manifest integrity
- [ ] Check for model updates/alerts

## Alert Conditions
- WSS v2 down
- Disk > 80%
- Schema violations detected
- Gap items marked CRITICAL unaddressed > 24h
