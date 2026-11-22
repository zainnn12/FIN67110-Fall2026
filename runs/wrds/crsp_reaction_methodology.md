# Costco eight-event CRSP reaction methodology

## Sources

- Event timestamps and SEC accessions: `runs/wrds/costco_eight_events.csv`.
- Daily source observations: WRDS CRSP CIZ `crsp.dsf_v2`. The selected columns and aliases are saved at `runs/wrds/costco_crsp_daily.csv`.
- Calculations and results: `runs/wrds/crsp_reaction.json`.

## Method

The event input contains the latest eight Costco Item 2.02 8-K filings whose reaction windows are inside the account's CRSP CIZ data, which ended on `2025-12-31` at the time of this run. The SEC acceptance timestamps are stored in UTC with their accessions and source links. The eight events run from March 7, 2024 through December 11, 2025.

For each SEC acceptance timestamp, query the current CRSP CIZ daily stock file and retain `dlyclose` as `prc`, `dlyprcflg`, shares outstanding, ticker, and PERMNO. Select the last positive `dlyclose` observation whose 4:00 p.m. America/New_York close is before the timestamp. Then select the first positive `dlyclose` observation whose close is after the timestamp. Calculate the close-to-close reaction as `(first_close_after / last_close_before - 1) * 100`. Do not round the stored calculation.

## Independent arithmetic check

For accession `0000909832-24-000012`, the saved calculation is `(725.56 / 785.59 - 1) * 100 = -7.641390547232016700823584820` percent. This recomputation uses the two saved source prices and agrees with the program result.

## Reproducible command

```bash
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python wrds_crsp_reaction.py --events runs/wrds/costco_eight_events.csv --source-output runs/wrds/costco_crsp_daily.csv --output runs/wrds/crsp_reaction.json --methodology-output runs/wrds/crsp_reaction_methodology.md
```
