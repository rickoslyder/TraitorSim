# Review

Summary: no agent should be the only reviewer of its own work. Use static checks, focused self-review, and cross-agent review where configured. Reviewer unavailability is not approval.

## Review dimensions

- **Spec compliance:** did the change match the requested TraitorSim behavior exactly?
- **Game correctness:** rule variants, win conditions, trust-matrix updates, day/night state transitions.
- **Safety/resource use:** no direct `python -m src.traitorsim` routine validation; no accidental 24-agent spawn.
- **UI correctness:** POV filtering, API route shape, loading/error/empty states.
- **Security:** no secrets printed or committed; model output treated as untrusted input.
- **Tests:** meaningful assertions and regression coverage; no false green.
- **Ops:** no deployment/restart without explicit approval.

## Cross-agent adapter

Optional. Configure with env vars when available:

```bash
export AOK_REVIEW_PRIMARY_CMD='hermes --provider xai-oauth -m grok-4.5 -z'
python /home/hermes/repos/agent-operability-kit/bin/aok_review.py . --diff
```

If no reviewer is configured, record `UNAVAILABLE` honestly and proceed only if the task does not require review.
