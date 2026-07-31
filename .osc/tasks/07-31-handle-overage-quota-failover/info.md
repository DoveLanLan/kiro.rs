# Tech notes

- Architecture decision: extend the endpoint classifier and reuse the existing
  provider failover branch; do not duplicate response handling in the provider.
- Risk / mitigation: exact reason-code matching remains gated by HTTP 402.
- Rollback plan: restore the previous classifier and redeploy the prior image.
