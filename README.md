# Challenge 1 — Messy Transactions

## Overview

This program reads `input.csv`, cleans and validates transaction records, and generates two output files:

- `cleaned.csv` — normalized transaction data, original values, validity status, and explanations for row-level issues.
- `report.json` — summary counts, duplicate statistics, and revenue totals.

The implementation uses only the Python standard library; no third-party packages are required.

## Requirements

- Python 3.10 or newer recommended.
- Keep `input.csv` in the project directory, or provide its path when running the program.
- The input CSV must contain these columns:

  `transaction_id`, `customer_name`, `amount`, `transaction_date`, `status`, `order_id`

## Run the program

From the project directory, run:

```bash
python clean_transactions.py input.csv
```

By default, `cleaned.csv` and `report.json` are written to the current working directory.

To write the output files to a separate directory:

```bash
python clean_transactions.py input.csv --out-dir output
```

The output directory is created if it does not already exist.

## Cleaning and validation rules

### Customer names

- Leading and trailing whitespace is removed.
- Repeated whitespace is collapsed to a single space.
- Names are converted to title case.
- The original value is retained in `customer_name_original`.

### Dates

- Dates are normalized to `YYYY-MM-DD`.
- Supported input formats are `YYYY-MM-DD`, `YYYY/MM/DD`, `DD/MM/YYYY`, and `DD-MM-YYYY`.
- Slash-separated dates are interpreted as day/month/year.
- Missing, invalid, or unsupported dates are flagged as issues, and the normalized date is left empty.

### Amounts

- Commas are treated as thousands separators; for example, `1,470.00` becomes `1470.00`.
- Amounts must be numeric, finite, and greater than zero.
- Missing, malformed, zero, negative, and non-finite amounts are flagged as invalid.
- `Decimal` is used for monetary values.

### Statuses

- Status values are trimmed and converted to lowercase.
- `canceled` is normalized to `cancelled`.
- The accepted statuses are `paid`, `pending`, `cancelled`, and `refund`.
- Missing or unrecognized statuses are set to `unknown` and flagged as issues.

### Row validity

- A row is marked `valid` when no issues have been recorded.
- A row is marked `invalid` when one or more issues are recorded.
- A row can have multiple issues; these are joined into the `issues` field in `cleaned.csv`.
- Original values are retained alongside normalized values for traceability.

### Duplicate detection

- Every row whose `transaction_id` occurs more than once is flagged with `duplicate_transaction_id = true` and an issue message.
- Likely duplicates are identified using normalized customer name, amount, normalized date, and `order_id`. Status is not part of this comparison.
- The first row in a likely-duplicate group is treated as the canonical candidate; later matching rows are flagged and reference the first row's input line number.
- Duplicate rows are flagged rather than deleted.

## Report definitions and reconciliation

- `input_rows` is the number of transaction records read from the CSV, excluding the header.
- `valid_rows` is the number of rows marked valid in `cleaned.csv`.
- `invalid_rows` is the number of rows marked invalid in `cleaned.csv`.
- The row counts should reconcile:

  `input_rows = valid_rows + invalid_rows`

- Duplicate statistics distinguish repeated-ID groups, rows involved in repeated IDs, extra repeated-ID rows, and likely-duplicate groups/rows.
- `total_revenue` is defined as the sum of amounts from valid, non-duplicate rows with status `paid`.
- Pending, cancelled, refund, invalid, repeated-ID, and likely-duplicate rows are excluded from `total_revenue`.
- Valid refund amounts are reported separately, and `net_paid_less_refunds` is calculated as paid revenue minus the reported refund amount.

These are explicit assumptions for this challenge. A production system should confirm the date conventions, amount formats, duplicate policy, and revenue definition with the business owner.

## Edge cases tested

The supplied dataset includes cases such as:

- Invalid dates, including `2026-15-08` and `not a date`.
- Comma-formatted amounts such as `1,470.00`.
- Invalid amounts such as `NaN`, `oops`, `0`, and `-250`.
- Repeated transaction IDs.
- Customer names with inconsistent capitalization or repeated whitespace.

## Output files

After running the program, the project directory (or the directory specified with `--out-dir`) will contain:

```text
cleaned.csv
report.json
```
