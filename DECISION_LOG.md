# Perk Palooza — Decision Log

Record decisions that affect product behavior, user experience, operations, security, finance or release scope. Do not mark a proposal as approved until the authorised people have agreed.

## Decision record template

### [DEC-XXX] Short decision title

- **Status:** Proposed / Under review / Approved / Superseded
- **Date raised:** YYYY-MM-DD
- **Decision date:** YYYY-MM-DD or Not decided
- **Decision owner:** [Name / role]
- **Contributors consulted:** [Names / roles]
- **Related PRD section:** [Section or open-decision ID]
- **Related GitHub Issues:** [Links]

**Context**  
What question or problem needs a decision?

**Options considered**  
List realistic options considered by the team.

**Decision**  
Record the agreed decision. If not decided, write “Not decided”.

**Rationale and trade-offs**  
Why was the option chosen? What risks or consequences remain?

**Follow-up actions**  
- [ ] [Action, owner, target date if agreed]

---

## Decision history

### [DEC-001] Verify businesses before onboarding

- **Status:** Recorded from the 2026-10-20 product planning meeting
- **Date raised:** 2026-10-20
- **Decision date:** 2026-10-20
- **Decision owner:** To be confirmed by the team
- **Contributors consulted:** Meeting attendees; names should be recorded only where confirmed
- **Related PRD section:** Business onboarding
- **Related GitHub Issues:** Create/link a dedicated business-verification issue

**Context**  
The team discussed user roles and how businesses should be onboarded.

**Decision**  
Businesses must be verified before they are uploaded to or onboarded onto the platform.

**Rationale and trade-offs**  
This establishes verification as a gate before a business becomes available on the platform. The team still needs to define the verification evidence, responsible reviewer, approval/rejection states and audit trail.

**Follow-up actions**
- [ ] Define required business verification documents and checks — owner to be assigned
- [ ] Define reviewer permissions and approval/rejection workflow — owner to be assigned
- [ ] Track the workflow in [Issue #2](https://github.com/Ifeanyipaul/Perk-Palooza/issues/2) and assign an owner — owner to be assigned

---

## Open decisions identified in PRD v1.0

Track each item below in an issue and assign an owner. These remain unresolved unless a dated decision record says otherwise.

- OD-01: Partial redemption and treatment of remaining value.
- OD-02: Default card validity and expiry/grace-window rules.
- OD-03: Treatment and possible exceptions for locked expired value.
- OD-04: Cashback rate, funding, eligibility and payout method.
- OD-05: Platform/Paystack fees and fee-refund treatment.
- OD-06: Wallet funding and withdrawal behavior.
- OD-07: Payment holding/safeguarding model, reconciliation and compliance.
- OD-08: Physical-card launch scope, shipping, activation and replacement.
- OD-09: WhatsApp/email delivery providers, validation and retry behavior.
- OD-10: Full-face-value redemption versus actual purchase amount and change.
- OD-11: Business float sizing, top-up approvals, thresholds and overdraft limits.
- OD-12: Business settlement and reconciliation process.
- OD-13: Active-card handling when a business changes category, is paused or removed.
- OD-14: Admin roles, approval limits and separation of duties.
- OD-15: Currency and launch geography.
- OD-16: Mandatory notification channels and urgency.

Do not treat the open items above as approved product behavior until the team records a decision.
