# Equity Research Report Audit Worksheet

Report: `equity_research_report.md`

Run folder: `runs/Apple_Inc_2026-11-02_15-00-13`

Sources compared: `10-K_000032019325000079.txt`, `10-Q_000032019326000020.txt`, `8-K_EX-99.1_000032019326000018.txt`, `facts.json`, `facts_MSFT.json`, `facts_GOOGL.json`, and `facts_DELL.json`.

Wrong + unsupported claims: 0

Missing claims: 0

## Partner Verification

Partner: Ansh Doshi (AD)

Date: 2026-11-02

Claim 9 — Correct: quarterly revenue was $109.417 billion versus $94.036 billion.

Claim 11 — Correct: quarterly GAAP diluted EPS was $2.02 versus $1.57.

| # | Report said | Filing says | Mark | Where |
|---|---|---|---|---|
| 1 | FY2025 revenue was **$416.161 billion**. | Total net sales were **$416.161 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1350; `RevenueFromContractWithCustomerExcludingAssessedTax`; unit `USD`; period 2024-09-29 to 2025-09-27. |
| 2 | Annual revenue growth was **6.43%**: **($416,161,000,000 - $391,035,000,000) / $391,035,000,000 = 6.43%**. | The filing values produce **6.4255118%**, displayed as **6.43%**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1350; `RevenueFromContractWithCustomerExcludingAssessedTax`; unit `USD`; periods 2024-09-29 to 2025-09-27 and 2023-10-01 to 2024-09-28. |
| 3 | Operating income was **$133.050 billion**; operating margin was **31.97%**: **$133,050,000,000 / $416,161,000,000 = 31.97%**. | Operating income was **$133.050 billion**; the filing values produce **31.9707998%**, displayed as **31.97%**. | Correct | Apple 10-K accession 0000320193-25-000079, lines 1350 and 1360; `OperatingIncomeLoss` and `RevenueFromContractWithCustomerExcludingAssessedTax`; unit `USD`; period 2024-09-29 to 2025-09-27. |
| 4 | Net income was **$112.010 billion**. | Net income was **$112.010 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1364; `NetIncomeLoss`; unit `USD`; period 2024-09-29 to 2025-09-27. |
| 5 | GAAP diluted EPS was **$7.46**. | Diluted EPS was **$7.46 per share**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1367; `EarningsPerShareDiluted`; unit `USD/shares`; period 2024-09-29 to 2025-09-27. |
| 6 | Return on average equity was **171.42%**: **$112,010,000,000 / (($73,733,000,000 + $56,950,000,000) / 2)**. | The filing inputs produce **171.4224497%**, displayed as **171.42%**. | Correct | Apple 10-K accession 0000320193-25-000079, lines 1364 and 1430; `NetIncomeLoss` and `StockholdersEquity`; unit `USD`; net-income period 2024-09-29 to 2025-09-27; equity instants 2025-09-27 and 2024-09-28. |
| 7 | Debt to equity was **1.2298x**: **($78,328,000,000 + $12,350,000,000) / $73,733,000,000**. | The filing inputs produce **1.2298157x**, displayed as **1.2298x**. | Correct | Apple 10-K accession 0000320193-25-000079, lines 1418, 1421, and 1430; `LongTermDebtNoncurrent`, `LongTermDebtCurrent`, and `StockholdersEquity`; unit `USD`; instant 2025-09-27. |
| 8 | Course-formula free cash flow was **$98.767 billion**: **$111,482,000,000 - $12,715,000,000**. | Cash from operations less property additions equals **$98.767 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, lines 1480 and 1485; `NetCashProvidedByUsedInOperatingActivities` and `PaymentsToAcquirePropertyPlantAndEquipment`; unit `USD`; period 2024-09-29 to 2025-09-27. |
| 9 | Latest-quarter revenue was **$109.417 billion**, versus **$94.036 billion** in the prior-year quarter. | Total net sales were **$109.417 billion** and **$94.036 billion**, respectively. | Correct | 8-K Exhibit 99.1 accession 0000320193-26-000018, lines 34-40; 10-Q accession 0000320193-26-000020, lines 728-734; `RevenueFromContractWithCustomerExcludingAssessedTax`; unit `USD`; three-month periods ended 2026-06-27 and 2025-06-28. |
| 10 | Quarterly revenue growth was **16.36%**: **($109,417,000,000 - $94,036,000,000) / $94,036,000,000 = 16.36%**. | The filing values produce **16.3565018%**, displayed as **16.36%**. | Correct | 8-K Exhibit 99.1 accession 0000320193-26-000018, lines 34-40; 10-Q accession 0000320193-26-000020, lines 728-734; `RevenueFromContractWithCustomerExcludingAssessedTax`; unit `USD`; three-month periods ended 2026-06-27 and 2025-06-28. |
| 11 | Latest-quarter GAAP diluted EPS was **$2.02 versus $1.57**. | Diluted EPS was **$2.02** and **$1.57**, respectively. | Correct | 8-K Exhibit 99.1 accession 0000320193-26-000018, lines 34-36 and 55-57; 10-Q accession 0000320193-26-000020, lines 728-730 and 749-751; `EarningsPerShareDiluted`; unit `USD/shares`; three-month periods ended 2026-06-27 and 2025-06-28. |
| FA-1 | The supplied closing price was **$347.10** on **October 27, 2026**. | **$347.10** is a user-supplied assignment input, not a filing value. | Correct | User-supplied closing price for 2026-10-27; unit `USD/share`; filing accession, line, tag, and period not applicable. |
| FA-2 | Shareholders' equity inputs were **$73.733 billion** and **$56.950 billion**. | Total shareholders' equity was **$73.733 billion** and **$56.950 billion**, respectively. | Correct | Apple 10-K accession 0000320193-25-000079, line 1430; `StockholdersEquity`; unit `USD`; instants 2025-09-27 and 2024-09-28. |
| FA-3 | Noncurrent term debt was **$78.328 billion**. | Noncurrent term debt was **$78.328 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1421; `LongTermDebtNoncurrent`; unit `USD`; instant 2025-09-27. |
| FA-4 | Current term debt was **$12.350 billion**. | Current term debt was **$12.350 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1418; `LongTermDebtCurrent`; unit `USD`; instant 2025-09-27. |
| FA-5 | Cash generated by operating activities was **$111.482 billion**. | Cash generated by operating activities was **$111.482 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1480; `NetCashProvidedByUsedInOperatingActivities`; unit `USD`; period 2024-09-29 to 2025-09-27. |
| FA-6 | Payments to acquire property, plant, and equipment were **$12.715 billion**. | Payments to acquire property, plant, and equipment were **$12.715 billion**. | Correct | Apple 10-K accession 0000320193-25-000079, line 1485; `PaymentsToAcquirePropertyPlantAndEquipment`; unit `USD`; period 2024-09-29 to 2025-09-27. |
| Peer-1 | Microsoft operating margin was **$155,237,000,000 / $331,839,000,000 = 46.78%**. | The saved facts produce **46.7808184%**, displayed as **46.78%**. | Correct | `facts_MSFT.json`; Microsoft 10-K accession 0001193125-26-323660; filing line not available in the supplied peer facts; `OperatingIncomeLoss` and `RevenueFromContractWithCustomerExcludingAssessedTax`; unit `USD`; period 2025-07-01 to 2026-06-30. |
| Peer-2 | Alphabet operating margin was **$129,039,000,000 / $402,836,000,000 = 32.03%**. | The saved facts produce **32.0326386%**, displayed as **32.03%**. | Correct | `facts_GOOGL.json`; Alphabet 10-K accession 0001652044-26-000018; filing line not available in the supplied peer facts; `OperatingIncomeLoss` and `Revenues`; unit `USD`; period 2025-01-01 to 2025-12-31. |
| Peer-3 | Dell operating margin was **$8,149,000,000 / $113,538,000,000 = 7.18%**. | The saved facts produce **7.1773327%**, displayed as **7.18%**. | Correct | `facts_DELL.json`; Dell 10-K accession 0001571996-26-000008; filing line not available in the supplied peer facts; `OperatingIncomeLoss` and `Revenues`; unit `USD`; period 2025-02-01 to 2026-01-30. |
| P/E | P/E was **$347.10 / $7.46 = 46.5282x**. | The supplied price and filing EPS produce **46.5281501x**, displayed as **46.5282x**. | Correct | Price: user-supplied for 2026-10-27; unit `USD/share`; filing fields not applicable. EPS: Apple 10-K accession 0000320193-25-000079, line 1367; `EarningsPerShareDiluted`; unit `USD/shares`; period 2024-09-29 to 2025-09-27. |
| Template | The report contains **Overview; Market Positioning and Growth Outlook; Valuation Insights; Future Developments and Strategic Recommendations; Investment Recommendation**. | The report has exactly the five required section headings. | Correct | Report section headings; filing accession, line, tag, unit, and period not applicable. |
| Recommendation | The recommendation is **Hold**. The single deciding number is the **46.5282x P/E ratio**, calculated as **$347.10 / $7.46 = 46.5282x**. | The report states one permitted rating and identifies one deciding number with the required arithmetic. | Correct | Report Section 5. Price: user-supplied for 2026-10-27; unit `USD/share`; filing fields not applicable. EPS: Apple 10-K accession 0000320193-25-000079, line 1367; `EarningsPerShareDiluted`; unit `USD/shares`; period 2024-09-29 to 2025-09-27. |
