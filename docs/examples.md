# Examples

This document describes each example bundle included in the `examples/` directory.

---

## customer_service_replay_bundle.json

**Scenario:** A customer service agent reads a CRM system and attempts to send a confirmation email.

**What happens:**
- The agent proposes two actions: a CRM read and an email send
- The CRM read is **allowed** (authority record grants `crm:read`)
- The email send is **blocked** (no `external_send` authority present)
- Policy traces are included for both decisions
- A reliance record captures the CRM data dependency
- The final output notes that the email was not sent

**Interesting for:** Demonstrating blocked action records, authority checking, and policy trace detail.

---

## internal_research_replay_bundle.json

**Scenario:** A research assistant searches internal documents, reads a file, and attempts to export a summary.

**What happens:**
- Document search and file read are **allowed** under research read authority
- The export is **escalated** (no export authority; escalated to supervisor)
- Reliance records capture both the document search and file read
- The final output includes the generated summary

**Interesting for:** Demonstrating escalation (vs. block), reliance records for multiple sources, and partial completion.

---

## procurement_replay_bundle.json

**Scenario:** A procurement agent compares vendor quotes and attempts to create and approve a purchase order.

**What happens:**
- Vendor quote read is **allowed**
- Purchase order draft is **allowed**
- Purchase order approval is **blocked** (`purchase_order_approve` is in the blocked tool list)
- Vendor email notification is **blocked** (no `external_send` authority)
- Two blocked action records are present

**Interesting for:** Demonstrating multiple blocked actions, the blocked tool check rule, and approval gates.

---

## redacted_replay_bundle.json

**Scenario:** A redacted version of the customer service bundle prepared for external compliance review.

**What happens:**
- Action payloads are replaced with `{"redacted": true}`
- Action targets are replaced with `"[REDACTED]"`
- `final_output` is replaced with `"[REDACTED]"`
- `RedactionMetadata` records the fields redacted, timestamp, and policy
- Status is `"redacted"`
- All IDs, timestamps, decision results, fingerprints, and policy names are preserved

**Interesting for:** Demonstrating redaction output and what is preserved for governance review.

---

## signed_replay_bundle.json

**Scenario:** A structurally valid `SignedReplayBundle` with demo signature metadata.

**Important:** The signature value is a **demo placeholder** and is not cryptographically valid. This example demonstrates the structure of a signed bundle, not a real signing operation.

**What it shows:**
- `SignedReplayBundle` wrapping an `AgentReplayBundle`
- `SignatureMetadata` with `signed: true`, algorithm, and key_id
- The signature is clearly marked as a demo value

To generate a real signed bundle:
```bash
arb sign examples/customer_service_replay_bundle.json \
    --secret "your-secret" \
    --out /tmp/signed.json
```
