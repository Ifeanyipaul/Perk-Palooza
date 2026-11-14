# Perk Palooza — Meeting Notes

## 2026-11-13 — XpressPay integration follow-up

- **Date:** 13 November 2026
- **Meeting:** Follow-up with XpressPay regarding the Perk Palooza payment gateway.
- **Purpose:** Obtain the sandbox details and business subaccount mapping required to proceed with payment gateway integration.
- **Record status:** Updated from Paul's account of the meeting and the subsequent provider handoff.

### Requested and received from XpressPay

Following the meeting, the Perk Palooza team requested the following integration details, and XpressPay has provided them:

- XpressPay test API keys.
- Confirmed Debug checkout and split-account sandbox URLs.
- A mapping of each Perk Palooza business ID to its verified XpressPay subaccount ID.

The actual credentials and sensitive configuration values should remain in approved secret storage or environment variables. They must not be added to this repository, committed to source control, or pasted into public issues.

### Current integration status

**Payment gateway integration is in progress.** The supplied sandbox information gives the development team the required provider-side configuration to continue implementation. This does not yet mean that a complete sandbox payment or split settlement has been verified.

### Dependencies and next steps

1. Continue implementing the XpressPay checkout and split-account flow using the supplied sandbox configuration.
2. Apply and verify the mapping between each Perk Palooza business ID and its corresponding verified XpressPay subaccount ID.
3. Obtain approval for the index-rename migration. The migration is required to resolve the related Django system-check warning; do not apply it until approval is received.
4. The authorised business-side representative must perform a sandbox payment using the agreed test checkout flow.
5. After the sandbox payment is performed, the developer can inspect the resulting transaction and split report to verify the transaction and allocation to the relevant subaccount.
6. Record the test result, any defects and the follow-up actions in the project progress log.

### Important distinction

- Sandbox credentials, endpoint URLs and subaccount mapping: **received**.
- Payment gateway implementation: **in progress**.
- Index-rename migration approval: **pending**.
- Sandbox payment by the authorised representative: **pending**.
- Transaction and split-report verification by the developer: **pending the sandbox payment**.
- Production payment processing: **not confirmed**.

---

## 2026-10-21 — Revenue model and app-card discussion

- **Date:** 21 October 2026
- **Meeting type:** Product strategy and monetisation discussion
- **Participants:** Paul Ifeanyichukwu Gabriel and the CEO (CEO's name not recorded here)
- **Purpose:** Discuss possible revenue streams, app-card design and responsibility for printing cards.
- **Record status:** Written from Paul's recollection of the discussion. Confirm participant details and any decisions with the CEO before treating proposals as approved.

### Paul's role and contribution

Paul participates in product leadership for Perk Palooza. His responsibilities include contributing to feature decisions, product and marketing strategy, revenue-model discussions, and business onboarding. This entry records his contribution to this discussion; it does not imply that every proposal was solely his idea, that a final decision was made, or that any discussed feature has been implemented.

### Topics discussed

#### 1. Revenue from businesses and customers
- The CEO and Paul discussed potential ways Perk Palooza could generate revenue from businesses and customers.
- A possible **5% fee or commission** was discussed. The calculation basis, payer, applicable transactions and exact mechanics were not confirmed in this meeting note.
- They also discussed **paid business advertising**: businesses could potentially pay to publish advertisements or promoted content on the platform.
- The fee and advertising concepts remain proposals until explicitly approved and documented.

#### 2. App-card design
- The participants discussed how cards in the app should be designed.
- The detailed card types, information hierarchy, visual treatment, restrictions and redemption/security requirements still need to be specified with the product designer and engineering team.

#### 3. Who prints the cards
- The participants considered whether businesses would print the cards themselves.
- No final printing responsibility or operating model is recorded as approved.
- The team needs to clarify whether this refers to digital cards, printable templates or physical cards, and assess consistency, cost, security and redemption risks before deciding.

### Decisions recorded

**No final product or commercial decision is recorded in this note.** The 5% proposal, paid business advertising, card design and business-led printing all require explicit confirmation.

See:
- [Issue #4 — Define and validate the revenue model](https://github.com/Ifeanyipaul/Perk-Palooza/issues/4)
- [Issue #5 — Define card design and printing workflow](https://github.com/Ifeanyipaul/Perk-Palooza/issues/5)
- [Decision Log](DECISION_LOG.md)

### Follow-up actions

- [ ] Confirm the proposed 5% fee's base, payer, transaction scope, collection point and treatment of refunds/cancellations.
- [ ] Assess paid business advertising options, pricing, placements, disclosures and moderation.
- [ ] Review monetisation assumptions with the CEO and record the authorised decision.
- [ ] Ask the product designer to prepare card design options and link Figma files to the relevant issue.
- [ ] Decide whether cards are digital, printable and/or physical for the MVP.
- [ ] Decide who is responsible for printing and document production, security, quality and cost implications if printing is in scope.
- [ ] Update the PRD and roadmap only after the relevant decisions are approved.
- [ ] Retain dated follow-up messages, design links, issue history and approvals as evidence of the actual product decision process.

### Evidence and attribution

This note is a contemporaneous project record based on Paul's account of the discussion. It should be supported, where available, by dated calendar entries, follow-up messages, issue history, approved documents and design artefacts. Do not describe proposals as approved decisions or claim measurable revenue/implementation outcomes without evidence.

---

## Future meeting template

- **Date/time:**
- **Meeting type:** Product review / planning / engineering sync / QA review
- **Facilitator:**
- **Attendees:** List only confirmed participants
- **Purpose:**

### Discussion
-

### Decisions
- Record only decisions actually agreed and add them to DECISION_LOG.md.

### Actions
- [ ] Action — owner — due date only if agreed

### Links
- Related issues:
- Relevant PRD sections:
