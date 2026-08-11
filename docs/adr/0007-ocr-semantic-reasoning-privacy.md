# ADR 0007: OCR + Semantic Reasoning Privacy Model

Date: 2026-08-07
Status: BETA — not yet Accepted. Requires a monitored testing period and defined success criteria (below) before promotion to Accepted status.

## Decision

Semantic reasoning gets added to the OCR pipeline (Pass 2 of the Document Center architecture) using a hybrid model:

1. **Default path — client-side embedding.** OCR and embedding generation (all-MiniLM-L6-v2, run client-side via WASM/ONNX) happen on the tenant's own device. Only the resulting embedding — a number-list representing meaning, not readable text — ever crosses to Semptify's servers for matching against the Question Atlas / document-type classifier. Raw document text and images never leave the device on this path.

2. **Fallback path — ephemeral server-side OCR.** Used only where client-side accuracy isn't sufficient (heavy handwriting, poor scan quality). Document content exists in server memory only for the duration of processing — never written to disk, never cached, never captured by logging or monitoring. Only the output (document type, confidence score, extracted structured fields) is retained, and it's written back to the tenant's own storage, not into any Semptify-held database.

3. **Zero server-side logging, enforced structurally** on both paths — not a policy statement, but logging configuration that structurally cannot capture document content fields, so there's no accidental trail even during a crash or debug session.

**Not included in this decision (deferred, not rejected):** PII redaction before semantic classification (masking names/SSNs/account numbers ahead of the reasoning step). Worth adding later as a low-cost hardening layer, but not required for this beta to proceed.

## Why

The actual privacy concern, as clarified directly: it's not momentary processing, it's **persistence** — data sitting somewhere it can later be stolen, subpoenaed, or leaked. This mirrors the storage architecture's "nothing here to steal" logic (ADR 0001), applied one layer earlier, at processing time instead of storage time. Momentary, on-device or in-memory-only processing satisfies that concern without requiring OCR to be avoided entirely, which real tenant documents (leases, notices, receipts) make impractical anyway — they inherently contain personal information.

## Why This Is Beta, Not Accepted

This path has real open questions that need actual testing before it earns standing-architecture status:

- **Client-side accuracy across devices.** Does WASM/ONNX-based OCR and embedding generation perform acceptably on the range of phones and browsers tenants actually use, especially older/lower-power devices?
- **Fallback trigger accuracy.** How reliably does the system detect "client-side isn't going to work here" and route to the ephemeral server-side path, versus silently producing a low-quality result?
- **Verified zero-logging.** "Structurally cannot log" needs to be confirmed by actual audit of the logging/monitoring stack, not just written into the code with good intentions.
- **Real-world false negative/positive rates** on document classification and confidence scoring, measured against a real (even if small) sample of actual document types.

## Success Criteria to Promote to Accepted

- [ ] Client-side path handles a defined minimum percentage of real test documents without falling back
- [ ] Fallback path confirmed, via logging audit, to retain zero document content after processing completes
- [ ] Classification confidence scores validated against human-reviewed ground truth on a test document set
- [ ] No open Tier-A-level privacy concerns remaining from a full review pass
