# Cash forecast assumptions

SYNTHETIC DATA — all entities and events are fictional.

Document ID: forecast-policy-tenant_aurora
Tenant ID: tenant_aurora
Effective date: 2026-07-01

The forecast opens at the bank balance as of 2026-09-26T12:00:00Z. Include future events strictly after that timestamp and through 2026-10-10 inclusive, in the business timezone. All future fixture events are date-only. The baseline includes confirmed customer payment schedules and scheduled bills and payroll. A scheduled receipt is uncertain until it settles. Exclude overdue invoices with no confirmed schedule and tentative promises. Show collection scenarios separately. Never double-count settled receipts or treat an invoice total as an additional receipt after its balance was partly paid. No credit facilities, overdrafts, interest, or tax calculations are modeled.
