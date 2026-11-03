# Checkpoint 1 Submission

## Final partner-company report

Partner-confirmed company: Microsoft Corporation (MSFT)

- [Microsoft fallback equity research report](runs/MICROSOFT_CORP_2026-11-02_15-42-54/equity_research_report.md)
- [Microsoft completed human audit](runs/MICROSOFT_CORP_2026-11-02_15-42-54/report_audit.md)
- [Microsoft filing manifest](runs/MICROSOFT_CORP_2026-11-02_15-42-54/manifest.json)

The report uses Microsoft’s October 28, 2026 earnings release. Partner Ansh Doshi (AD) manually marked Claims 9 and 11 Correct at the top of the report. The report is labeled `fallback` because the model API returned an insufficient-credit error, as permitted by the course fallback rule.

Microsoft audit results:

- Wrong plus unsupported: 0
- Missing: 0

## Costco report and hand audit

- [Costco fallback equity research report](runs/COSTCO_WHOLESALE_CORP_NEW_2026-10-28_21-58-12/equity_research_report.md)
- [Costco completed hand audit](costco_report_audit.md)
- [Costco filing manifest](runs/COSTCO_WHOLESALE_CORP_NEW_2026-10-28_21-58-12/manifest.json)

Costco audit results:

- Wrong plus unsupported: 0
- Missing: 1 — Claim 10, quarterly revenue growth

## Equity-research desk

- [Seven-step desk](equity_research_data.py)
- [Four-role workflow](research_roles.py)
- [Environment checker](check_env.py)
- [Dependencies](requirements.txt)
- [Four-role tests](tests/test_research_roles.py)
- [Seven-step tests](tests/test_equity_research_data.py)
- [Walmart prerequisite facts](runs/Walmart_Inc_2026-10-28_21-39-10/facts.json)

Verification: 19 unit tests passed.
