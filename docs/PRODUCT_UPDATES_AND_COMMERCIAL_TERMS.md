# Perk Palooza — Product Updates and Commercial Terms

**Document type:** Product requirements and commercial decisions  
**Source:** Product updates and changes document supplied on 24 October 2026  
**Status:** Requirements documented; implementation and final legal review are not confirmed by this document.

This document records the requested product changes and fee rules for the user and business experiences. It is a product handoff, not confirmation that every item has already been implemented.

## 1. Business-side updates

### 1.1 Business My Cards page
The page for cards ordered by a business for itself should show:
- Total Allocated Value
- Total Available Value
- Expired Value
- Used Value

It should link to **Request a Card**, **View Orders**, **View Cards**, and **View My Deposit History**.

**Scope and aggregation**
- The My Cards page shows only cards ordered by that business for itself.
- The overall business dashboard aggregates cards ordered by users and linked to the business, plus cards ordered by the business itself.
- Aggregate figures must not double-count cards.
- Example: ₦500,000 in user-ordered cards linked to a business plus ₦100,000 ordered by the business itself = ₦600,000 Total Allocated Value.

**Definitions from the supplied requirements**
- **Total Allocated Value:** total value of all cards allocated in the relevant scope.
- **Total Available Value:** combined value of active cards and expired cards.
- **Expired Value:** value of expired cards.
- **Used Value:** value of cards redeemed and marked as used.

Apply the definitions consistently on both user and business sides, with each view scoped appropriately.

### 1.2 Business card requests
When a business requests cards from its business profile, link the cards automatically to the logged-in business and populate its name automatically. Do not require manual business selection or name entry.

The form should support:
- Optional name displayed on the card
- Card design
- Card value
- Quantity
- Preferred delivery channel
- Expiration date selectable from 14 to 30 days

Reuse user-side request components where appropriate.

### 1.3 Business orders, cards, and deposit history
- **View Orders:** show the business's own orders as separate entries; each opens an Order Details page adapted from the user-side design.
- **View Cards:** filter by All Cards, Active Cards, Used Cards, and Expired Cards. Each card opens Card Details. Locked/unlocked states and identification-number features also apply.
- **View My Deposit History:** show deposit history for the business's own card orders, separately from the overall business deposit history.

### 1.4 Reinstating expired business cards
From Expired Value, a business can see expired cards from its own orders and reinstate eligible cards without another card-creation fee. During reinstatement, it can edit the displayed name (if applicable), choose a new expiry of 14–30 days, and select a delivery channel. Reinstated cards must be digital-only; no physical production or delivery. The original card value must remain unchanged.

### 1.5 Business descriptions and operating hours
- Collect a useful business description during onboarding, with a guided placeholder prompting actual products, services, activities, and facilities.
- Collect opening and closing hours as structured fields, not only as text in the description.
- Allow businesses to edit their description and, where permitted, operating hours after onboarding.
- Show the latest approved description and operating hours to users on business details.

## 2. User-side updates

### 2.1 Reinstating expired user cards
Users can view eligible expired cards and reinstate them by editing the displayed name (if applicable), selecting a new expiry between 14 and 30 days, and selecting a delivery channel. Users cannot change the original card value or switch the linked business. Reinstatement is free of an additional card-creation fee and produces a digital-only card.

### 2.2 Card design and expiry selection
- Card design selection is required in both user and business card-request flows.
- Users and businesses can select an expiry date between 14 and 30 days when requesting cards.
- Apply expiry rules appropriate to the card type and delivery method.

### 2.3 Business details and discovery search
Show the business description on user-facing business details and reflect approved description updates.

Search should support business name, category, product, service, facility, description terms, and a location selected independently of the user's current location. Users should be able to review matching business details—including offerings, location, and opening hours—before creating a linked card.

Search eligibility and safeguards:
- Only businesses that have completed required verification and approval should be eligible for card orders.
- Do not imply that a product is in stock or a service immediately available unless reliable information confirms it.
- Changing the selected search location should allow users to search in a different city or area.

## 3. Representative roles and notifications

### 3.1 Proposed representative roles
1. **Card Scanning and Redemption Representative:** scans cards and completes the redemption action, including marking cards as used where appropriate. Generate a system username automatically; it must not be editable. The business owner must authenticate with their login password to reveal it again, following the existing business-password reveal process.
2. **Deposit Notifications Representative:** receives business deposit notifications. WhatsApp, email, or both remain options under consideration. The registered business email receives deposit-related email notifications whether or not a separate representative is assigned.
3. **Business Owner / Primary Contact:** remains the primary contact for account administration.

Final role labels, permissions, and assignment rules still need confirmation before implementation.

### 3.2 Redemption and deposit notifications
- The representative who scans and processes a card should receive a push notification confirming the relevant action, including when it is scanned and marked as used.
- The business should receive a push notification when a linked card is successfully redeemed at its premises, subject to final notification configuration.
- Registered business email is for deposit-related notifications only, not general card-redemption alerts.
- Record redemption activity with the relevant date and time for accountability.

## 4. Cashback changes

- Remove the cashback on/off option from the Request a Card flow.
- Users must no longer apply cashback directly to card requests or purchases.
- Cashback should instead be withdrawn to the user's own bank account through a withdrawal request with required bank details and an approved processing procedure/timeframe.
- Do not require users to move cashback into a platform wallet or use it as an internal card-creation payment method.

## 5. Feature under deliberation: self-printing
Allowing users or businesses to print cards themselves is still under consideration. One proposed option is **Print by Self** within the physical-card section. This is not a confirmed decision.

## 6. Commercial terms and fees

| Item | Current documented term |
|---|---|
| Digital card creation fee | ₦50 per card |
| Physical card pricing | Still under consideration |
| Bulk order: 1–9 cards | No discount |
| Bulk order: 10–19 cards | 10% discount |
| Bulk order: 20–49 cards | 15% discount |
| Bulk order: 50+ cards | 20% discount |
| Cashback rate | 1% of eligible Perk Palooza fees collected, excluding the business transaction charge and card value |
| Business transaction charge | 2%, as agreed |

All bulk-discount thresholds and rates must be editable from the admin Settings page.

The supplied document states that commercial terms and applicable legal documentation will be reviewed with the lawyer expected to join the process next month. Treat these as the current documented terms pending that review, not as legal advice or proof of final approval.

## 7. Implementation guidance
Reuse existing user-side components where practical for business-side card requests, design selection, orders and Order Details, card lists and Card Details, and expired-card reinstatement. Ensure each business-side record is associated with the correct business account.

## 8. Open decisions and validation checklist

- [ ] Confirm final representative role names, permissions, and assignment rules.
- [ ] Decide deposit notification channels (WhatsApp, email, or both) and finalize push-notification configuration.
- [ ] Confirm physical-card pricing.
- [ ] Decide whether to offer self-printing.
- [ ] Review commercial terms and legal documents with counsel.
- [ ] Verify card-value calculations and prevent double-counting across user-ordered and business-ordered cards.
- [ ] Confirm expiry and delivery rules for each card type.
- [ ] Validate that reinstatement never changes original card value or linked business and is digital-only.
- [ ] Confirm cashback withdrawal processing workflow and timeframe.
- [ ] Ensure search results do not make unsupported stock or service-availability claims.

---
*Prepared from the supplied “Perk palooza changes and fees” document. No additional fees or policies have been inferred beyond the source.*
