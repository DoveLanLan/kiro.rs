# Rollback Notes: Handle Overage Quota Exhaustion Failover

- Date: 2026-07-31

## Application rollback

On bytevirt, restore `/opt/kiro-rs/.env.bak.overage-failover-20260731` to
`/opt/kiro-rs/.env`, then run Docker Compose from `/opt/kiro-rs`. The previous
known image revision is `6e114c146ae88c4d573bb12a0030594227be1377`.

## Source rollback

Revert commit `9a7273e4447692ac2aa37b08d99099665b960e3e` and publish the resulting image.

## Data considerations

No schema, credential, or config migration was introduced. Runtime
`config.json`, `credentials.json`, and the persisted proxy setting are not part
of the image rollback.
