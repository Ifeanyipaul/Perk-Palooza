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

### [DEC-002] Revenue model: proposed 5% fee and business advertising

- **Status:** Proposed / Under review — not approved
- **Date raised:** 2026-10-21
- **Decision date:** Not decided
- **Decision owner:** CEO and authorised product/business decision-makers to confirm
- **Contributors consulted:** Paul Ifeanyichukwu Gabriel and the CEO (CEO's name not recorded in the meeting note)
- **Related PRD section:** Monetisation / fees / business advertising — exact section to confirm
- **Related GitHub Issues:** [Issue #4 — Define and validate revenue model](https://github.com/Ifeanyipaul/Perk-Palooza/issues/4)

**Context**

During a product discussion on 21 October 2026, Paul and the CEO discussed possible revenue from businesses and customers. A 5% fee or commission was considered, alongside potential paid advertisements from businesses on the platform.

**Options considered**

- A 5% fee or commission (the basis and payer remain unspecified).
- Paid advertising or promoted placements for businesses.
- Potentially combining more than one revenue stream, subject to validation.

These are discussion points, not a complete or approved list of commercial options.

**Decision**

Not decided. The 5% proposal and business advertising have not been confirmed as approved pricing or launch features.

**Rationale and trade-offs**

The model must be understandable to customers and businesses, commercially viable, and operationally implementable. The team must clarify who pays, how fees are calculated and collected, how refunds and failed transactions are handled, how ads are labelled and moderated, and whether the model affects adoption or trust.

**Follow-up actions**

- [ ] Define the fee calculation basis, payer, scope, collection point and refund/cancellation treatment.
- [ ] Define advertising placements, pricing, duration, business eligibility and moderation.
- [ ] Evaluate commercial and user-experience implications with the CEO and relevant team members.
- [ ] Record the final authorised decision and update the PRD/roadmap before implementation.

### [DEC-003] App-card design and printing responsibility

- **Status:** Under review — not approved
- **Date raised:** 2026-10-21
- **Decision date:** Not decided
- **Decision owner:** Product/CEO decision-makers to confirm
- **Contributors consulted:** Paul Ifeanyichukwu Gabriel and the CEO (CEO's name not recorded in the meeting note)
- **Related PRD section:** Card design / physical-card scope / business redemption — exact section to confirm
- **Related GitHub Issues:** [Issue #5 — Define card design and printing workflow](https://github.com/Ifeanyipaul/Perk-Palooza/issues/5)

**Context**

The discussion covered how the app's cards should be designed and whether businesses should print cards themselves.

**Options considered**

- Digital in-app cards only.
- A printable card or template.
- Physical cards, with printing by the platform, businesses or an approved print partner.

These options are listed to structure follow-up; they were not all necessarily discussed as formal alternatives and none is approved by this record.

**Decision**

Not decided. Card format, MVP scope and printing responsibility require explicit confirmation.

**Rationale and trade-offs**

The choice affects design consistency, cost, business operations, security, copying or tampering risks, card identification and redemption verification. The team should define the card format and security requirements before implementation.

**Follow-up actions**

- [ ] Confirm card type(s) and MVP scope with the CEO/product team.
- [ ] Review design options with the product designer.
- [ ] If printing is in scope, define who prints, who pays, print specifications and security controls.
- [ ] Record the final decision and link approved designs and acceptance criteria.

### [DEC-001] Verify businesses before onboarding

- **Status:** Recorded from the 2026-10-20 product planning meeting
- **Date raised:** 2026-10-20
- **Decision date:** 2026-10-20
- **Decision owner:** To be confirmed by the team
- **Contributors consulted:** Meeting attendees; names should be recorded only where confirmed
- **Related PRD section:** Business onboarding
- **Related GitHub Issues:** [Issue #2 — Business verification and onboarding](https://github.com/Ifeanyipaul/Perk-Palooza/issues/2)

**Context**

The team discussed user roles and how businesses should be onboarded.

**Decision**

Businesses must be verified before they are uploaded to or onboarded onto the platform.

**Rationale and trade-offs**

This establishes verification as a gate before a business becomes available on the platform. The team still needs to define the verification evidence, responsible reviewer, approval/rejection states and audit trail.

**Follow-up actions**
- [ ] Define required business verification documents and checks — owner to be assigned.
- [ ] Define reviewer permissions and approval/rejection workflow — owner to be assigned.
- [ ] Track the workflow in [Issue #2](https://github.com/Ifeanyipaul/Perk-Palooza/issues/2) and assign an owner — owner to be assigned.

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


### [DEC-004] Payment gateway evaluation: XpressPay ₦1,000 flat transaction charge

- **Status:** Under review — not approved
- **Date raised:** 2026-10-27
- **Decision date:** Not decided
- **Decision owner:** CEO and authorised product/business decision-makers to confirm
- **Contributors consulted:** Paul Ifeanyichukwu Gabriel and meeting participants (full roles/names to be confirmed)
- **Related PRD section:** Payments / gateway fees / settlement — exact section to confirm
- **Related meeting note:** [Business Partnership Meeting between XPSL and Perk Palooza — 27 October 2026](MEETING_NOTES.md#2026-10-27--business-partnership-meeting-between-xpsl-and-perk-palooza)

**Context**

At a meeting titled “Business Partnership Meeting between XPSL x Perk Palooza” on 27 October 2026, XpressPay reportedly proposed a flat ₦1,000 charge per transaction. This would be in addition to Perk Palooza's own fee. Perk Palooza is still evaluating the proposal.

**Options to assess**

- Continue discussions with XpressPay and request complete written terms.
- Compare the proposal against alternative payment gateway providers.
- Evaluate who would bear the provider charge and whether the combined fees are commercially acceptable.

These are evaluation options, not confirmed decisions.

**Decision**

Not decided. Perk Palooza has not accepted the offer or selected XpressPay as its payment provider in this record.

**Rationale and trade-offs**

A fixed ₦1,000 fee could have a disproportionate impact on low-value transactions when combined with Perk Palooza's own fee. The team needs to understand the fee payer, transaction-value rules, settlement model, refunds, failed payments, taxes and any additional charges before deciding.

**Follow-up actions**

- [ ] Obtain XpressPay's formal fee schedule and written proposal.
- [ ] Confirm the exact fee basis, who pays it and any additional charges.
- [ ] Model total fees across representative transaction amounts.
- [ ] Verify settlement timing, split/direct-to-business settlement, refunds, reconciliation and dispute processes.
- [ ] Compare other gateway providers and document the approved choice.
