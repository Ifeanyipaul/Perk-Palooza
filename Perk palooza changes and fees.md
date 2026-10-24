# PERK PALOOZA
## Product Updates and Changes

## PART A: BUSINESS-SIDE UPDATES

### 1. Business My Cards Page

Participating businesses can request cards linked directly to their own businesses.

The My Cards page should contain:
- Total Allocated Value
- Total Available Value
- Expired Value
- Used Value

It should provide access to Request a Card, View Orders, View Cards, and View My Deposit History.

**Value calculations and scope**
- The My Cards page displays figures only for cards ordered by that business for itself.
- The overall business dashboard aggregates cards ordered by Perk Palooza users and linked to that business, plus cards ordered by the business itself.
- Overall dashboard values must include both sources without double-counting. For example, ₦500,000 in user-ordered cards linked to a business plus ₦100,000 ordered by the business itself equals ₦600,000 Total Allocated Value.

**Value definitions**
- Total Allocated Value: total value of all cards allocated under the relevant scope.
- Total Available Value: combined value of active and expired cards.
- Expired Value: value of expired cards.
- Used Value: value of cards redeemed and marked as used.

Apply the definitions consistently on user and business sides, scoped to the relevant page.

### 2. Request a Card — Business Side

When a business accesses Request a Card from its profile, automatically link cards to that business and display its business name. Do not require business selection or manual name entry.

The form should support:
- Name to appear on the card, if applicable
- Card design
- Card value
- Number of cards
- Preferred delivery channel
- Expiration date selectable between 14 and 30 days

Reuse relevant user-side components where appropriate while automatically linking cards to the logged-in business.

### 3. Business Orders and Card Details

Businesses should access their own card orders and cards.

**View Orders**
- Display orders placed by the business for itself as separate orders.
- Each order opens an Order Details page adapted from the user-side design.

**View Cards**
- Filter by All Cards, Active Cards, Used Cards, and Expired Cards.
- Each card opens Card Details.
- Locked, unlocked, and identification-number features also apply.

**View My Deposit History**
- Show deposit history associated with the business’s own card orders.
- Keep this separate from overall business deposit history.

### 4. Expired Cards — Business Side

When a business clicks Expired Value, show expired cards associated with its own card orders. The business should be able to reinstate eligible cards without an additional card creation fee.

During reinstatement, allow the business to edit the displayed name (if applicable), select a new expiration date between 14 and 30 days, and select a delivery channel. Reinstated cards must be digital only; do not offer physical production or delivery in this flow. The original card value must remain unchanged.

### 5. Business Description and Business Profile Editing

Each participating business should have a description explaining its activities and the products, services, or facilities it offers. Display this description in user-facing business details.

During onboarding:
- Prompt businesses to provide a useful description.
- Provide a placeholder or guided example encouraging accurate descriptions of activities, products, services, and facilities.
- Collect opening and closing hours as structured information, not only as text in the description.

Businesses should be able to edit their description and, where permitted, opening and closing hours after onboarding. Save updates to the business profile so the latest approved information is displayed to users.

## PART B: USER-SIDE UPDATES

### 6. Expired Cards — User Side

When a user clicks Expired Value, display the user’s eligible expired cards. The user can edit the displayed name (if applicable), select a new expiration date between 14 and 30 days, and choose a delivery channel.

The user cannot change the original card value or select a different business during reinstatement. Reinstatement has no additional card creation fee and results in a digital card only.

### 7. Card Design Selection

Card design selection is required on both sides. Users and businesses requesting cards for themselves should be able to select a design within the card-request flow.

### 8. Expiration Date Selection

Users and businesses should be able to select an expiration date between 14 and 30 days when requesting a card. Apply the appropriate expiry rules for the selected card type and delivery method.

### 9. Business Details Display

When users open a participating business’s details, display the business description. If the business updates its description, reflect the update on the user side. The description should help users understand the business’s offerings before creating a linked card.

### 10. Search by Business Description, Products, Services and Location

The user-side app should support discovery based on search terms, location, and business offerings—not only business names or categories.

Users should be able to:
- Search for a product, service, facility, business name, category, or relevant description term.
- Select or change the location they want to search in independently of their current location.
- View participating businesses matching the search and selected location.
- Open business details to review description, offerings, location, and opening hours.
- Select a business and proceed to create a card linked to it.

**Example:** A user in Asaba searches for a pharmacy offering medical equipment or testing services and selects Asaba as the location. The app displays matching participating businesses in Asaba. A user in Lagos should also be able to change the search location to Asaba and search there.

**Search requirements**
- Support business name, category, product, service, and relevant business-description terms.
- Allow search location to be changed independently of current location.
- Base results on selected location and relevant business information.
- Only businesses that completed required verification and approval are eligible for card orders.
- Do not imply stock availability or immediate service availability unless reliable information confirms it.
- Let users review business details before creating a card.

## PART C: REPRESENTATIVE ROLES AND NOTIFICATIONS

### 11. Representative Role Selection

Businesses should be able to assign roles to approved representatives during onboarding or representative management.

**A. Card Scanning and Redemption Representative**
- Scans cards and completes the required redemption action, including Mark as Used where appropriate.
- Receives an automatically generated system username that cannot be edited.
- The username should be provided securely to the business.
- To view the username again, the business owner authenticates using their login password, following the existing business-password reveal process.

**B. Deposit Notifications Representative**
- Receives notifications relating to business deposits.
- Notification channels remain under consideration: WhatsApp, email, or both.
- The registered business email receives deposit-related email notifications whether or not a separate representative is assigned.

**C. Business Owner / Primary Contact**
- Remains the primary contact for the business account and administrative responsibilities.

Final role labels, permissions, and assignment rules should be confirmed before implementation.

### 12. Card Scanning and Redemption Notifications

Distinguish business-level notifications from representative-level notifications.

**Representative notifications**
The representative who scans and processes a card should receive a push notification to the number provided confirming the relevant action, including when a card is scanned and marked as used.

**Business notifications**
The business should receive push notifications for cards successfully redeemed at its premises. The business phone number provided for notifications should receive these business-level redemption alerts, subject to final notification configuration.

The registered business email should receive deposit-related notifications only, not general card-redemption alerts. Record redemption activity with the relevant date and time for accountability.

## PART D: CASHBACK CHANGES

### 13. Cashback Withdrawal

Users should no longer apply cashback directly toward requesting or purchasing cards. Remove the cashback option or on/off control from the Request a Card flow.

Instead, cashback should be withdrawn to the user’s own bank account. The withdrawal flow should allow users to provide required bank details and submit a withdrawal request. Process requests according to the approved procedure and timeframe.

Do not require users to transfer cashback into a platform wallet or use it as an internal payment method for card creation.

## PART E: FEATURES UNDER DELIBERATION

### 14. Self-Printing of Cards

Allowing users and businesses to print cards themselves remains under consideration. One proposed approach is a **Print by Self** option within the physical-card section. This is not yet a confirmed decision.

## PART F: COMMERCIAL TERMS

### 15. Current Commercial Decisions

**Card creation fee**
- Digital card creation: ₦50 per card.
- Physical card pricing remains under consideration.

**Bulk card discounts**
- 1–9 cards: no discount.
- 10–19 cards: 10% discount.
- 20–49 cards: 15% discount.
- 50 cards and above: 20% discount.

All discount rates and quantity thresholds must be editable from the admin Settings page.

**Cashback**
Cashback rate: 1% of eligible Perk Palooza fees collected, excluding the business transaction charge and card value.

**Business transaction charge**
Business transaction charge: 2%, as agreed.

The commercial terms and applicable legal documentation will be reviewed with the lawyer expected to join the process next month.

## PART G: IMPLEMENTATION GUIDANCE

### 16. Reuse Existing Components

Where possible, business-side pages should reuse existing user-side designs and flows for:
- Card requests
- Card design selection
- Orders and Order Details
- Card lists and Card Details
- Expired-card reinstatement

Business-side versions should automatically associate cards, orders, and relevant records with the correct business account.
