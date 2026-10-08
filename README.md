# Cloud Cost Insights

**Turn a normalized cloud billing CSV into a transparent cost report.**

A small, local Python project for practicing cloud cost analysis: group spend by service and resource group, inspect day-to-day spikes, and compare a simple monthly estimate with a budget. No cloud account, API key, or paid deployment is required.

## Quick start

Python 3.10+; standard library only. Run from this repository's root:

```bash
python cost_report.py data/sample-costs.csv --budget 400
python -m unittest discover -v
```

Demo output: **USD 72.00 actual**, **USD 432.00 linear month-end estimate**, and a **September 3 spike**. The sample contains synthetic billing rows, not real Azure charges or current service prices.

## What it does

- Uses decimal arithmetic for costs, with two-decimal display rounding.
- Produces service, resource-group, daily and monthly totals.
- Flags a daily increase greater than 50% only between consecutive observed days.
- Rejects missing fields, invalid dates, non-finite costs, credits and mixed currencies.
- Writes a machine-readable JSON report to `reports/cost-report.json`.

## Input contract

| Column | Meaning |
| --- | --- |
| `date` | Billing day, YYYY-MM-DD |
| `service` | Service label |
| `resource_group` | Project or resource group |
| `cost` | Non-negative decimal cost |
| `currency` | Three-letter currency label; one currency per file |

For a provider export, first map its columns to this contract. This is not a direct Azure billing export parser. Rows are billing line items; duplicate-looking rows are included, since separate resources can legitimately share the same fields.

## Method and limitations

`estimate = month-to-date spend / last observed day number × days in that month`.

The estimate assumes the export covers the first day of the month through the last observed date, and that absent days represent zero spend. Partial or delayed exports make it unreliable. The tool cannot verify export completeness. Spikes are investigation prompts, not proof of waste. No savings, exchange-rate conversion, tax treatment, forecasting model, or cloud deployment is claimed.

## Project structure

- `cost_report.py`: validation, aggregation and CLI.
- `data/sample-costs.csv`: reproducible synthetic demo.
- `examples/cost-report.json`: generated demo result.
- `test_cost_report.py`: financial arithmetic and input edge cases.

## Next steps

Add a tested adapter for a specific provider export and compare estimates against complete historical months.
