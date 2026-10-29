from __future__ import annotations

import unittest
from decimal import Decimal

from equity_research_data import (
    DILUTED_EPS_LINE_RE,
    REVENUE_LINE_RE,
    Company,
    DeskError,
    calculate_metrics,
    extract_aligned_facts,
    find_exhibit_991_url,
    format_quarterly_release_metrics,
    matching_release_lines,
    parse_quarterly_release_metrics,
)


def duration_point(
    value: float,
    start: str,
    end: str,
    accession: str,
    filed: str,
) -> dict[str, object]:
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": accession,
        "fy": int(end[:4]),
        "fp": "FY",
        "form": "10-K",
        "filed": filed,
    }


def instant_point(
    value: float,
    end: str,
    accession: str,
    filed: str,
) -> dict[str, object]:
    return {
        "end": end,
        "val": value,
        "accn": accession,
        "fy": int(end[:4]),
        "fp": "FY",
        "form": "10-K",
        "filed": filed,
    }


class FactSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        current_start = "2024-01-01"
        current_end = "2024-12-31"
        prior_start = "2023-01-01"
        prior_end = "2023-12-31"
        current_accession = "0000000000-25-000001"
        prior_accession = "0000000000-24-000001"

        def duration_units(current: float, prior: float) -> dict[str, object]:
            return {
                "USD": [
                    duration_point(
                        prior,
                        prior_start,
                        prior_end,
                        prior_accession,
                        "2024-02-01",
                    ),
                    duration_point(
                        current,
                        current_start,
                        current_end,
                        current_accession,
                        "2025-02-01",
                    ),
                ]
            }

        def instant_units(current: float, prior: float) -> dict[str, object]:
            return {
                "USD": [
                    instant_point(prior, prior_end, prior_accession, "2024-02-01"),
                    instant_point(current, current_end, current_accession, "2025-02-01"),
                ]
            }

        self.company_facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "label": "Revenue",
                        "units": {
                            "USD": [
                                duration_point(
                                    80,
                                    "2022-01-01",
                                    "2022-12-31",
                                    "0000000000-23-000001",
                                    "2023-02-01",
                                )
                            ]
                        },
                    },
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "label": "Revenue",
                        "units": duration_units(120, 100),
                    },
                    "OperatingIncomeLoss": {
                        "label": "Operating income",
                        "units": duration_units(24, 15),
                    },
                    "NetIncomeLoss": {
                        "label": "Net income",
                        "units": duration_units(18, 12),
                    },
                    "EarningsPerShareDiluted": {
                        "label": "Diluted EPS",
                        "units": {
                            "USD/shares": [
                                duration_point(
                                    2.0,
                                    prior_start,
                                    prior_end,
                                    prior_accession,
                                    "2024-02-01",
                                ),
                                duration_point(
                                    3.0,
                                    current_start,
                                    current_end,
                                    current_accession,
                                    "2025-02-01",
                                ),
                            ]
                        },
                    },
                    "StockholdersEquity": {
                        "label": "Equity",
                        "units": instant_units(90, 70),
                    },
                    "LongTermDebtNoncurrent": {
                        "label": "Long-term debt",
                        "units": instant_units(30, 32),
                    },
                    "LongTermDebtCurrent": {
                        "label": "Current debt",
                        "units": instant_units(6, 5),
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "label": "Cash from operations",
                        "units": duration_units(28, 20),
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "label": "Property additions",
                        "units": duration_units(8, 7),
                    },
                }
            }
        }

    def test_selects_newest_candidate_and_aligns_periods(self) -> None:
        fact_set = extract_aligned_facts(
            Company(ticker="TEST", cik=1, name="Issuer"),
            self.company_facts,
        )
        revenue = fact_set["facts"]["revenue"]
        self.assertEqual(
            revenue["tag"],
            "RevenueFromContractWithCustomerExcludingAssessedTax",
        )
        self.assertEqual(fact_set["fiscal_year_period_end"], "2024-12-31")
        self.assertEqual(fact_set["prior_year_period_end"], "2023-12-31")
        self.assertEqual(revenue["current"]["val"], 120)
        self.assertEqual(revenue["prior"]["val"], 100)

    def test_calculator_prints_the_required_arithmetic(self) -> None:
        fact_set = extract_aligned_facts(
            Company(ticker="TEST", cik=1, name="Issuer"),
            self.company_facts,
        )
        results = dict(calculate_metrics(fact_set, Decimal(30)))
        self.assertIn("(120 - 100) / 100 = 20.00%", results["Revenue growth"])
        self.assertIn("24 / 120 = 20.00%", results["Operating margin"])
        self.assertIn("18 / ((90 + 70) / 2) = 22.50%", results["Return on average equity"])
        self.assertIn("(30 + 6) / 90 = 0.4x", results["Debt to equity"])
        self.assertIn("28 - 8 = 20", results["Free cash flow"])
        self.assertIn("30 / 3 = 10x", results["P/E"])


class FilingAndReleaseParsingTests(unittest.TestCase):
    def test_finds_exhibit_991(self) -> None:
        html = """
        <table class="tableFile">
          <tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th></tr>
          <tr><td>2</td><td>Earnings release</td>
              <td><a href="release.htm">release.htm</a></td><td>EX-99.1</td></tr>
        </table>
        """
        url = find_exhibit_991_url(
            "https://www.sec.gov/Archives/edgar/data/1/2/index.html",
            html,
        )
        self.assertEqual(
            url,
            "https://www.sec.gov/Archives/edgar/data/1/2/release.htm",
        )

    def test_finds_revenue_and_diluted_eps_lines(self) -> None:
        text = """
        Total revenue | $ | 120 | $ | 100
        Deferred revenue | $ | 10 | $ | 8
        Revenue growth across products at WWDC26
        Proceeds from sales of marketable securities | 12 | 10
        Operating expenses | $ | 50 | $ | 45
        Diluted earnings per share | $ | 3.00 | $ | 2.00
        """
        self.assertEqual(
            matching_release_lines(text, REVENUE_LINE_RE),
            ["Total revenue | $ | 120 | $ | 100"],
        )
        self.assertEqual(
            matching_release_lines(text, DILUTED_EPS_LINE_RE),
            ["Diluted earnings per share | $ | 3.00 | $ | 2.00"],
        )

    def test_parses_comparative_gaap_rows_and_excludes_adjusted_eps(self) -> None:
        text = """
        Example Group Consolidated Statements of Income (Unaudited)
        Three Months Ended
        (Amounts in millions, except per share data)
        Total revenues | $ | 1,250 | $ | 1,000 | 25.0 | %
        Diluted net income per common share attributable to Example Group | $ | 1.23 | $ | 0.98 | 25.5 | %
        Adjusted diluted earnings per share | $ | 1.45 | $ | 1.10
        """
        metrics = parse_quarterly_release_metrics(text)

        self.assertEqual(metrics.revenue.current, Decimal("1250"))
        self.assertEqual(metrics.revenue.prior, Decimal("1000"))
        self.assertEqual(metrics.revenue.unit, "million")
        self.assertEqual(metrics.gaap_diluted_eps.current, Decimal("1.23"))
        self.assertEqual(metrics.gaap_diluted_eps.prior, Decimal("0.98"))
        self.assertNotIn(
            "Adjusted",
            metrics.gaap_diluted_eps.source_line,
        )

    def test_parses_diluted_at_end_and_parenthesized_loss(self) -> None:
        text = """
        Consolidated Statements of Operations
        Quarter Ended
        Dollars in thousands, except per-share amounts
        Net sales | $ | 500,000 | $ | 450,000 | 11.1%
        Non-GAAP diluted earnings per share | $2.00 | $1.80
        Net loss per common share - diluted | $ | (0.25) | $ | 0.10
        """
        metrics = parse_quarterly_release_metrics(text)

        self.assertEqual(metrics.revenue.current, Decimal("500000"))
        self.assertEqual(metrics.revenue.prior, Decimal("450000"))
        self.assertEqual(metrics.revenue.unit, "thousand")
        self.assertEqual(metrics.gaap_diluted_eps.current, Decimal("-0.25"))
        self.assertEqual(metrics.gaap_diluted_eps.prior, Decimal("0.10"))

    def test_parses_bare_diluted_eps_row_before_share_count_section(self) -> None:
        text = """
        Consolidated Statements of Income (Unaudited)
        Three Months and Fiscal Year Ended
        (Amounts in millions, except per-share and share data)
        Total revenue | 95,723 | 86,156 | 303,154 | 275,235
        NET INCOME PER COMMON SHARE:
        Basic | $ | 6.75 | $ | 5.88 | $ | 20.78 | $ | 18.24
        Diluted | $ | 6.75 | $ | 5.87 | $ | 20.76 | $ | 18.21
        Shares used in calculation (000's):
        Basic | 443,975 | 444,007 | 443,953 | 443,985
        Diluted | 444,364 | 444,706 | 444,427 | 444,803
        """
        metrics = parse_quarterly_release_metrics(text)

        self.assertEqual(metrics.gaap_diluted_eps.current, Decimal("6.75"))
        self.assertEqual(metrics.gaap_diluted_eps.prior, Decimal("5.87"))
        self.assertEqual(
            metrics.gaap_diluted_eps.source_line,
            "Diluted | $ | 6.75 | $ | 5.87 | $ | 20.76 | $ | 18.21",
        )

    def test_rejects_bare_diluted_share_count_row(self) -> None:
        text = """
        Consolidated Statements of Income (Unaudited)
        Three Months Ended
        Total revenue | 1,250 | 1,000
        EARNINGS PER SHARE:
        Basic | $ | 1.10 | $ | 1.00
        Weighted-average common shares outstanding:
        Basic | 100,000 | 99,000
        Diluted | 101,000 | 100,000
        """
        with self.assertRaisesRegex(DeskError, "GAAP diluted EPS"):
            parse_quarterly_release_metrics(text)

    def test_rejects_bare_diluted_row_in_adjusted_eps_section(self) -> None:
        text = """
        Consolidated Statements of Operations
        Three Months Ended
        Revenue | $ | 900 | $ | 800
        Adjusted earnings per share:
        Diluted | $ | 1.20 | $ | 1.00
        """
        with self.assertRaisesRegex(DeskError, "GAAP diluted EPS"):
            parse_quarterly_release_metrics(text)

    def test_rejects_release_with_only_adjusted_diluted_eps(self) -> None:
        text = """
        Consolidated Statements of Operations
        Three Months Ended
        Revenue | $ | 900 | $ | 800
        Adjusted diluted EPS | $ | 1.20 | $ | 1.00
        """
        with self.assertRaisesRegex(DeskError, "GAAP diluted EPS"):
            parse_quarterly_release_metrics(text)

    def test_formats_required_step_6_output(self) -> None:
        text = """
        Consolidated Statements of Income
        Three Months Ended
        (Dollars in millions, except per-share data)
        Revenues | $ | 120 | $ | 100
        Earnings per common share - diluted | $ | 3.00 | $ | 2.00
        """
        lines = format_quarterly_release_metrics(
            parse_quarterly_release_metrics(text),
            "0000000000-26-000123",
        )

        self.assertIn("Current-quarter revenue: $120 million", lines)
        self.assertIn("Prior-year-quarter revenue: $100 million", lines)
        self.assertIn(
            "Revenue growth arithmetic: ($120 - $100) / $100 = 20.00%",
            lines,
        )
        self.assertIn("Current-quarter GAAP diluted EPS: $3.00", lines)
        self.assertIn("Prior-year-quarter GAAP diluted EPS: $2.00", lines)
        self.assertIn(
            "Source release accession number: 0000000000-26-000123",
            lines,
        )
        self.assertTrue(
            any(line.startswith("Revenue source release line:") for line in lines)
        )
        self.assertTrue(
            any(
                line.startswith("GAAP diluted-EPS source release line:")
                for line in lines
            )
        )


if __name__ == "__main__":
    unittest.main()
