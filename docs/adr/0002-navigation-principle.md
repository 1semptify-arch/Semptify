# ADR 0002: Navigation Principle

Date: 2026-08-06
Status: Accepted

## Decision

Semptify is engineered like a road system — routes, on-ramps, wayfinding — never like a shelter or security system with gates, checkpoints, stop signs, or controlled intersections.

Concretely:

- **No mandatory gates before value is delivered.** No forced account creation or verification screen between a visitor and something useful.
- **No checkpoints in front of public information.** Open content stays reachable without a stop-and-check step, including soft barriers like modals or interstitials.
- **OAuth is a merge-lane, not a perimeter.** Connecting to a tenant's own Drive or iCloud routes them onto personal tools smoothly; it is never architected as a security wall around the site as a whole.
- **Friction must justify itself as a sign, not a barrier.** A pause or step is acceptable only when it points someone in the right direction, not when it stops them to check something about them.

Architecture and vocabulary are checked as **two separate passes**. A correctly-routed flow described with gate-language ("sign in," "log in," "account") still fails the standard because the language teaches the wrong mental model.

## Why

Tenants in housing crisis need immediate access to facts and tools. Gate-first UX trains users to expect restriction and creates abandonment before value is delivered. The Navigation Principle pairs with Open Access (ADR 0006): public information must remain reachable without identity checks.

## Consequences

- New features MUST NOT introduce mandatory login, verification, or interstitial steps before public information or crisis routing content.
- OAuth flows MUST be scoped to storage-dependent personal tools only.
- Copy and UI labels MUST use routing language ("connect your storage," "open the library") rather than gate language ("sign in," "create an account").
- Code reviews and preflight checks MUST evaluate both flow architecture and vocabulary.
