# W0 contract addendum: C8 evidence compatibility

Status: W0 candidate mapping contract.

Inspected main: `459e4ba62fca49364aebb0050cd5fb2dd5a71bfa`.
Reconstruction Bundle 0.2.0 remains the current accepted consumer for historical producer pairs.

## C8 compatibility rule
Replay must preserve the meaning of new W0 fields without upgrading historical assurance.

For a future tenant-aware producer generation, Replay records:
- producer contract generation and exact source revision;
- tenant_id as supplied by the producer;
- C4 failure class/stage/reasons;
- C3 profile identity/config/capability fields when present;
- C6 flow and result-admission decision identities when present;
- C7 stop/intervention transitions when present;
- C5 observation uncertainty/freshness/finality fields.

Value states remain explicit: `present`, `omitted`, `redacted`, `unknown`, `unsupported`.

Unsupported producer/consumer pairs fail clearly or yield explicitly incomplete evidence; shape similarity is never version negotiation. Historical 0.2.0 artifacts do not acquire tenant/profile assurance by inference or backfill.

No schema version is advanced by W0 merely to reserve these mappings. W3 chooses the smallest accepted Replay generation after actual producer schemas are accepted and adds fixtures for that exact pair.
