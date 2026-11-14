# Perk Palooza

A purpose-spending platform in development. The product is designed to help people allocate funds for defined purposes and enable controlled spending with approved businesses.

> **Project status (14 November 2026):** XpressPay has supplied the requested sandbox integration details. Payment gateway integration is in progress; sandbox transaction and split-report verification are still pending.

## Problem

Giving someone money for a specific purpose does not guarantee that the money will be used as intended. Perk Palooza explores purpose-based funding, controlled spending, redemption verification and transaction records.

## Core product areas

- Purpose-based fund allocation and card creation
- Spending restrictions and expiry
- Approved-business onboarding and redemption
- XpressPay checkout and split-account payment integration (currently in progress)
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

1. Complete the XpressPay checkout and split-account integration in the sandbox.
2. Verify the business ID to XpressPay subaccount ID mapping.
3. Obtain approval and apply the pending index-rename migration, then confirm the Django system check.
4. Coordinate an authorised sandbox payment and verify the resulting transaction and split report.
5. Review the PRD and agree the MVP scope.
6. Resolve launch-blocking product and operational questions.
7. Keep implementation, testing and release claims tied to verifiable work.

## Team coordination

Paul Ifeanyichukwu Gabriel coordinates requirements, tasks and progress as Team Lead and contributes to product feature discussions, marketing strategy, revenue planning and business onboarding. Engineering, design and QA contributions should be attributed to the people who actually perform that work. See [Team and Responsibilities](TEAM_AND_RESPONSIBILITIES.md).

## Technology and payment integration

XpressPay is the current payment gateway integration being worked on. The team has received XpressPay test credentials, confirmed Debug checkout and split-account sandbox URLs, and the business-to-subaccount mapping. Sandbox verification remains pending. Sensitive credentials must be stored outside the repository in approved secret storage or environment variables.

## Security and confidentiality

This is a private client project. Do not commit API keys, passwords, payment credentials, private client information or production user data. Public disclosure of source code, designs or client details requires appropriate authorization.
