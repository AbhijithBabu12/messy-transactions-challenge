# Messy Transactions --- Data Cleaning Challenge

## Overview

This project is a standalone Python command-line program that reads a
messy transactions CSV file, validates and normalizes its records,
identifies duplicate transactions, and generates two outputs:

-   `cleaned.csv` --- the original values, normalized values, row
    validity, and issue explanations.
-   `report.json` --- row counts, duplicate statistics, revenue totals,
    and a reconciliation check.

The program uses Python's standard library; no third-party packages are
required.

## Requirements

-   Python 3.9 or newer recommended
-   A CSV input file containing the required columns listed below

The program uses `argparse`, `csv`, `json`, `re`, `datetime`, `decimal`,
and `pathlib`.

## Project files

A typical submission layout is:

``` text
messy-transactions/
├── clean_transactions.py
├── input.csv
├── README.md
├── cleaned.csv       # generated when the program runs
└── report.json       # generated when the program runs
```

Your actual Python filename may differ. Use that filename in the run
command.

## Run the program

From a terminal in the project directory:

``` bash
python clean_transactions.py input.csv
```

By default, `cleaned.csv` and `report.json` are written to the current
working directory.

To write the output files to another directory:

``` bash
python clean_transactions.py input.csv --out-dir output
```

The output directory is created if it does not already exist.

On some systems, you may need to use `python3` instead of `python`.

## Input CSV format

The input CSV must contain these column names:

  Column               Purpose
  -------------------- ----------------------------------------------
  `transaction_id`     Identifier for a transaction
  `customer_name`      Customer name
  `amount`             Transaction amount
  `transaction_date`   Date of the transaction
  `status`             Transaction status
  `order_id`           Order identifier used in duplicate detection

Column names are expected to match these names exactly. The program
checks that all required headers are present before processing rows.

## Data-cleaning rules

### Customer names

-   Leading and trailing whitespace is removed.
-   Consecutive whitespace is collapsed to a single space.
-   Each word is converted to title-style capitalization.
-   The original customer name is preserved in `customer_name_original`;
    the normalized value is written to `customer_name`.

This helps standardize differences such as extra spaces and
capitalization. It does not guarantee that differently spelled names
refer to the same person.

### Transaction dates

The program accepts these date formats:

-   `YYYY-MM-DD`
-   `YYYY/MM/DD`
-   `DD/MM/YYYY`
-   `DD-MM-YYYY`

Accepted dates are written in ISO format: `YYYY-MM-DD`.

For slash-separated dates, the program interprets the date as
**day/month/year**. For example, `03/04/2026` means 3 April 2026.
Missing or unparseable dates are marked as issues, and the normalized
date is left blank.

### Amounts

-   Surrounding whitespace is removed.
-   Commas are removed before parsing, supporting values such as
    `1,470.00` when commas are used as thousands separators.
-   Values are parsed with `Decimal` to avoid typical binary
    floating-point rounding issues in monetary calculations.
-   Missing, malformed, non-finite, zero, and negative amounts are
    invalid.
-   Valid amounts are written to `cleaned.csv` as numeric text.

**Assumption:** comma separators are treated as thousands separators.
Formats such as `1.470,00` are not supported by this assumption and
should be handled explicitly if they occur in the source data.

### Statuses

Recognized statuses are normalized as follows:

  Input status   Normalized status
  -------------- -------------------
  `paid`         `paid`
  `pending`      `pending`
  `cancelled`    `cancelled`
  `canceled`     `cancelled`
  `refund`       `refund`

Status matching ignores leading/trailing whitespace and capitalization.
An unrecognized or missing status becomes `unknown` and adds an issue to
the row.

### Missing required values and row validity

The program checks for missing customer names, transaction IDs, and
order IDs, as well as invalid dates, amounts, and statuses.

Each row receives:

-   `validity`: `valid` if no issues were found, otherwise `invalid`
-   `issues`: a semicolon-separated explanation of all detected issues

A row may have more than one issue. Duplicate flags also add issues, so
duplicate records are marked invalid under this program's rules.

## Duplicate detection

The program uses two checks.

### 1. Repeated transaction IDs

Rows with the same non-empty `transaction_id` are grouped together. If
an ID occurs more than once, every row in that group is flagged with
`duplicate_transaction_id = true` and receives a
`repeated transaction_id` issue.

This conservative rule treats a repeated ID as ambiguous rather than
choosing one record automatically.

### 2. Likely duplicate transactions

The program builds a matching signature from:

-   Normalized customer name (case-insensitive comparison)
-   Amount rounded to two decimal places
-   Normalized transaction date
-   Order ID (case-insensitive comparison)

When multiple rows have the same signature, the first row is treated as
the canonical candidate and later rows are marked as likely duplicates.
The later rows include `duplicate_of_row`, which identifies the first
matching input row number.

Status is not part of this signature. Consequently, two records with the
same customer, amount, date, and order ID can be flagged even if their
statuses differ. This is an intentional assumption in the current
implementation and should be reconsidered if the data requires
status-sensitive matching.

A matching signature is a heuristic, not proof that two records
represent the same real-world transaction.

## Output files

### `cleaned.csv`

The output preserves original values and adds normalized data and audit
information, including:

-   Input row number
-   Original and normalized customer name
-   Original and normalized amount
-   Original and normalized transaction date
-   Original and normalized status
-   Transaction and order IDs
-   Row validity and issue explanations
-   Repeated-ID and likely-duplicate flags
-   The input row number of the canonical candidate for likely
    duplicates

### `report.json`

The report contains:

-   `input_rows`
-   `valid_rows`
-   `invalid_rows`
-   `row_count_reconciliation`
-   Duplicate group and row counts
-   Revenue totals and the definition used to calculate them

The reconciliation check verifies:

``` text
valid_rows + invalid_rows == input_rows
```

This should be `true` for every successful run.

### Revenue definition

`total_revenue` is calculated as the sum of rows that are:

-   Valid
-   Marked `paid`
-   Not flagged as repeated transaction IDs
-   Not flagged as likely duplicates

Pending, cancelled, refund, invalid, and duplicate rows are excluded
from `total_revenue`.

Refund amounts are reported separately as `valid_refund_amount_total`.
`net_paid_less_refunds` is calculated as total revenue minus the
separately reported refund amount. The program does not infer that a
refund row should be matched to a particular original payment.

## Edge case to test before submission

Test a row with an amount written as `1,470.00`, and another row with an
invalid amount such as `oops`. Confirm that the first is parsed as a
positive amount and the second is marked invalid with an amount-format
issue.

Also test at least two rows with the same transaction ID and two rows
sharing the same likely-duplicate signature. Confirm that the duplicate
flags and report counts reflect those rows.

> Before submitting, run these cases against your actual input and
> update this section to say which edge case you personally tested and
> what the program returned.

## Assumptions and limitations

-   Slash-separated dates use day/month/year order.
-   Commas in amounts are treated as thousands separators.
-   Amounts must be finite and greater than zero.
-   Unknown statuses are not silently accepted.
-   Every row sharing a repeated transaction ID is flagged.
-   Likely-duplicate detection is based on customer, amount, date, and
    order ID; status is excluded.
-   The first matching row is the canonical candidate for a
    likely-duplicate group.
-   Revenue includes only valid, non-duplicate `paid` rows; refunds are
    reported separately.
-   Name normalization standardizes whitespace and capitalization but
    does not resolve spelling variations or prove identity.

These choices are documented assumptions for this challenge, not
universal accounting rules.

## Troubleshooting

-   **Missing input file:** confirm that the input filename and path are
    correct.
-   **Missing-column error:** check that the CSV has all six required
    headers with the expected spelling.
-   **Unexpected date result:** verify the accepted formats and remember
    that slash-separated dates are interpreted as `DD/MM/YYYY`.
-   **Unexpected amount result:** check whether commas are thousands
    separators in the source data.
-   **Unexpected duplicate flag:** inspect the transaction ID or the
    four fields used by the likely-duplicate signature.

## Challenge objective

The goal is to make messy transaction data more consistent and auditable
while preserving original values, explaining row-level problems,
identifying duplicate candidates, and producing a report whose row
counts reconcile with the cleaned output.
