# Perk Palooza — Product Roadmap

**Status:** Proposed planning baseline; confirm with the team before treating dates or scope as committed.

## Phase 1 — Requirements review and MVP planning

- Review PRD v1.0 with product, engineering, UI/UX, QA and operations.
- Assign an owner to every open decision that affects MVP.
- Confirm first-release scope and identify dependencies.
- Agree acceptance criteria and test approach.
- Record decisions in `DECISION_LOG.md`.

**Exit criteria:** MVP scope is agreed; launch-blocking decisions have owners and documented answers; work is split into assigned, reviewable issues.

## Phase 2 — MVP core flows

The PRD recommends prioritising:

- Giver authentication and wallet visibility.
- Card creation and one-business-or-one-category restriction.
- Paystack checkout with trusted server-side payment confirmation.
- Digital delivery and card dashboard.
- Business login and secure redemption validation.
- Atomic, single-use redemption.
- Giver redemption notifications.
- Business float/history and internal business onboarding.
- Audit trail and operational visibility.

Implementation order and technical dependencies must be confirmed by engineering.

## Phase 3 — Verification and operational readiness

- Test payment success, pending, failure, retries and duplicate webhook events.
- Test restriction enforcement, expiry, cancellation and duplicate/concurrent redemption.
- Reconcile giver and business ledgers across successful and failed scenarios.
- Verify access control, audit trail and notification retry behavior.
- Confirm monitoring, backup, recovery and incident response arrangements.
- Complete the Definition of Done in the PRD.

## Later / scope-dependent capabilities

The PRD recommends that physical cards, cashback and advanced admin workflows enter launch scope only after their open decisions are resolved and tested.

## Planning rules

- Do not invent delivery dates; add target dates only after agreement with owners.
- Mark dependencies explicitly in GitHub Issues.
- Distinguish proposed scope from approved scope.
- Update this roadmap when a decision changes the release plan.
