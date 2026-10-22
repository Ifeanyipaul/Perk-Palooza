# Perk Palooza

A purpose-spending platform in development. The product is designed to help people allocate funds for defined purposes and enable controlled spending with approved businesses.

> **Project status:** Requirements review and MVP planning, with UI design scheduled to begin. This is not a production-ready product.

## Problem

Giving someone money for a specific purpose does not guarantee that the money will be used as intended. Perk Palooza explores purpose-based funding, controlled spending, redemption verification and transaction records.

## Core product areas

- Purpose-based fund allocation and card creation
- Spending restrictions and expiry
- Approved-business onboarding and redemption
- Paystack payment integration and server-side payment verification
- Transaction records, notifications and operational audit trail
- Business float, settlement and reconciliation
- Cashback and physical-card capabilities, subject to unresolved scope decisions

The Product Requirements Document (PRD) is the source of truth for requirements. Proposed features must not be treated as approved launch scope until confirmed by the team.

## Current planning documents

- [Product Requirements Document / Developer Handoff (PDF)](PRD_Developer_Handoff_v1.0.pdf)
- [Product Roadmap](PRODUCT_ROADMAP.md)
- [Team and Responsibilities](TEAM_AND_RESPONSIBILITIES.md)
- [Decision Log](DECISION_LOG.md)
- [Progress Log](PROGRESS_LOG.md)
- [Meeting Notes](MEETING_NOTES.md)
- [Revenue model follow-up — Issue #4](https://github.com/Ifeanyipaul/Perk-Palooza/issues/4)
- [Card design and printing workflow — Issue #5](https://github.com/Ifeanyipaul/Perk-Palooza/issues/5)
- [Open UI design task](https://github.com/Ifeanyipaul/Perk-Palooza/issues/1)

## Current priorities

1. Review the PRD and agree the MVP scope.
2. Resolve launch-blocking product and operational questions.
3. Resolve revenue-model assumptions before implementing fees or paid advertising.
4. Confirm card types, design requirements and printing responsibility before implementation.
5. Track UI design deliverables and review them against agreed user journeys.
6. Break approved requirements into assigned GitHub Issues with acceptance criteria.
7. Keep implementation, testing and release claims tied to verifiable work.

## Team coordination

Paul Ifeanyichukwu Gabriel coordinates requirements, tasks and progress as Team Lead and contributes to product feature discussions, marketing strategy, revenue planning and business onboarding. Engineering, design and QA contributions should be attributed to the people who actually perform that work. See [Team and Responsibilities](TEAM_AND_RESPONSIBILITIES.md).

## Technology

The PRD identifies Paystack for checkout. The full application stack and implementation details should be recorded after engineering confirms them; this README does not assume unconfirmed technologies.

## Security and confidentiality

This is a private client project. Do not commit API keys, passwords, payment credentials, private client information or production user data. Public disclosure of source code, designs or client details requires appropriate authorization.
