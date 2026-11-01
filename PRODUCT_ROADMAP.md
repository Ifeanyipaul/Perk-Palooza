# Perk Palooza — Product Roadmap

**Status:** Proposed product rollout structure, based on the discussion between the CEO and product lead. Feature scope and release timing should be confirmed with the team before being treated as committed.

## Roadmap overview

The roadmap is organised into four versions. Following the product discussion, the core platform capabilities originally grouped under Version 1 have been moved into Version 2. Version 1 therefore represents the existing platform baseline; Version 2 delivers the core card workflow and personalised card instructions.

## Version 1 — Existing Platform Baseline

This version represents the existing Perk Palooza platform baseline. The expanded core card creation, delivery, payment and redemption capabilities listed below are planned for Version 2.

## Version 2 — Core Platform and Personalised Card Instructions

### Core platform capabilities

- Card creation and requests.
- Linking cards to specific participating businesses.
- Digital card delivery.
- QR-code scanning and redemption.
- Card status and redemption tracking.
- Payment processing and transaction records.
- Business and administrative management.

The intended workflow allows a card to be created and issued to a recipient, who can present it at the designated participating business. The business scans the card's QR code to validate and process redemption.

### Personalised card instructions

The issuer can add a personal note, instruction, preference or restriction when creating a card. When the recipient presents the card and the business scans its QR code, the business can view the instruction attached to that specific card.

Examples include a special request, a personal instruction from the issuer, or a preference or restriction that the recipient wants the business to know.

**Version 2 objective:** Deliver the core card request, creation, issuance, delivery, payment, tracking and redemption workflow, including card-specific instructions visible to the business.

## Version 3 — Shared Card Feed

Version 3 introduces a shared feed where users can make cards available for other users to claim.

### Intended user flow

1. When creating a card, the issuer chooses between direct delivery to a recipient and publishing the card on the platform feed.
2. Shared cards become visible to other users on the platform.
3. An interested user selects a card and chooses **Accept**.
4. The card is temporarily reserved for that user for approximately two minutes.
5. During the reservation period, the user chooses a delivery channel, such as WhatsApp or email.
6. The card is delivered through the selected channel and removed from the feed.

### Notifications

- The original issuer is notified when another user accepts the card.
- The original issuer is notified when the card is redeemed.

**Version 3 objective:** Allow users to share cards with the wider platform community while keeping issuers informed about acceptance and redemption.

## Version 4 — Multi-Business Cards

Version 4 introduces cards that can be redeemed across all participating businesses, rather than being restricted to one specific business.

The issuer creates a card that is valid at participating businesses that support the relevant redemption. The recipient chooses where to redeem it.

### Example

An issuer creates a ₦20,000 card. Instead of linking it to one business, the card can be used at any eligible participating business on the platform. The recipient chooses where to spend it.

### Issuer notification

The issuer is notified of the business where the card was redeemed.

**Version 4 objective:** Give recipients more choice about where to redeem a card while retaining issuer visibility into the redemption location.

## Product planning and delivery notes

- This version structure records the proposed sequencing discussed by the CEO and product lead.
- The key change is moving the core capabilities originally listed under Version 1 into Version 2.
- Version 1 is the existing platform baseline; it is not a claim that all Version 2 capabilities are already implemented.
- Confirm detailed requirements, dependencies, acceptance criteria and ownership with product, engineering, design, QA and operations before implementation.
- Do not assign delivery dates until the team has agreed them.
- The PRD remains the source of truth for detailed requirements. Update this roadmap when scope or sequencing decisions change.
- This roadmap describes planned capabilities; it does not imply that they have already been built or released.
