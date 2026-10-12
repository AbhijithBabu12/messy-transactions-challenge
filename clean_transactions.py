import argparse
import csv
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


Date_formats = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y")
Known_statuses = {
    "paid": "paid",
    "pending": "pending",
    "cancelled": "cancelled",
    "canceled" : "cancelled",
    "refund" : "refund",
}

def normalize_name(raw):
    
    value = re.sub(r"\s+"," ", (raw or "").strip())
    return " ".join(part[:1].upper() + part[1:].lower() for part in value.split())

def parse_date(raw):
    
    value = (raw or "").strip()
    if not value:
        return "", "missing transaction_date"
    
    for fmt in Date_formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat(), None
        except ValueError:
            continue
    return "", "unparseable or invalid transaction_date"


def parse_amount(raw):
    
    value = (raw or "").strip()
    if not value:
        return None, "missing amount"
    
    normalized = value.replace(",", "")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", normalized):
        return None, "invalid amount format"
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None, "invalid amount format"
    if not amount.is_finite():
        return None, "amount must be finite"
    if amount <=0:
        return None, "amount must be greater than zero"
    return amount, None


def process_rows(raw_rows):
    
    prepared = []
    for source_row, raw in enumerate(raw_rows, start=2):
        issues = []
        name = normalize_name(raw.get("customer_name", ""))
        if not name:
            issues.append("missing customer_name")
            
        date, date_issue = parse_date(raw.get("transaction_date", ""))
        if date_issue:
            issues.append(date_issue)
            
        amount, amount_issue = parse_amount(raw.get("amount", ""))
        if amount_issue:
            issues.append(amount_issue)
        
        raw_status = (raw.get('status') or '').strip().lower()
        status = Known_statuses.get(raw_status, "unknown")
        if status == "unknown":
            issues.append("unrecognized status")
        
        transaction_id = (raw.get("transaction_id") or "").strip()
        order_id = (raw.get("order_id") or "").strip()
        
        if not transaction_id:
            issues.append("missing transaction_id")
        if not order_id:
            issues.append("missing order_id")
            
        
        prepared.append({
        "source_row": source_row,
        "transaction_id": transaction_id,
        "customer_name_original": raw.get("customer_name", ""),
        "customer_name": name,
        "amount_original": raw.get("amount", ""),
        "amount_decimal": amount,
        "transaction_date_original": raw.get("transaction_date", ""),
        "transaction_date": date,
        "status_original": raw.get("status", ""),
        "status": status,
        "order_id": order_id,
        "issues": issues,
        "duplicate_transaction_id": False,
        "duplicate_transaction_id_group": "",
        "likely_duplicate": False,
        "duplicate_of_row": "",
        })
        

    transaction_groups = {}
    for row in prepared:
        if row['transaction_id']:
            transaction_groups.setdefault(row['transaction_id'], []).append(row)
    
    for transaction_id, group in transaction_groups.items():
        if len(group) > 1:
            for row in group:
                row['duplicate_transaction_id'] = True
                row['duplicate_transaction_id_group'] = transaction_id
                row['issues'].append('repeated transaction_id')
    
    
    signatures = {}
    for row in prepared:
        amount = row['amount_decimal']
        
        if row['customer_name'] and amount is not None and row['transaction_date'] and row['order_id']:
            signature = (
                row['customer_name'].casefold(),
                amount.quantize(Decimal('0.01')),
                row['transaction_date'],
                row['order_id'].casefold(),
            )
            
            signatures.setdefault(signature, []).append(row)
        
    for group in signatures.values():
        if len(group) > 1:
            canonical_row = group[0]['source_row']
            for row in group[1:]:
                row['likely_duplicate'] = True
                row['duplicate_of_row'] = str(canonical_row)
                row['issues'].append(
                f"likely duplicate of input row {canonical_row}"
                "(same customer, amount, date, order_id)"
                )
        
    for row in prepared:
        row['validity'] = 'valid' if not row['issues'] else 'invalid'
        row['is_valid'] = not row['issues']
        
    return prepared, transaction_groups, signatures
    

def write_outputs(rows, transaction_groups, signatures, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned_path = out_dir / 'cleaned.csv'
    
    columns = [
        'source_row', 'transaction_id', 'customer_name_original', 'customer_name',
        'amount_original', 'amount', 'transaction_date_original', 'transaction_date',
        'status_original', 'status', 'order_id', 'validity', 'issues',
        'duplicate_transaction_id', 'duplicate_transaction_id_group',
        'likely_duplicate', 'duplicate_of_row',
    ]
    
    with cleaned_path.open('w', newline = '', encoding = 'utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        
        for row in rows:
            writer.writerow({
                'source_row' : row['source_row'],
                "transaction_id": row["transaction_id"],
                "customer_name_original": row["customer_name_original"],
                "customer_name": row["customer_name"],
                "amount_original": row["amount_original"],
                "amount": format(row["amount_decimal"], "f") if row["amount_decimal"] is not None else "",
                "transaction_date_original": row["transaction_date_original"],
                "transaction_date": row["transaction_date"],
                "status_original": row["status_original"],
                "status": row["status"],
                "order_id": row['order_id'],
                "validity" : row['validity'],
                "issues" : "; ".join(row['issues']),
                "duplicate_transaction_id" : str(row['duplicate_transaction_id']).lower(),
                "duplicate_transaction_id_group" : row['duplicate_transaction_id_group'],
                "likely_duplicate" : str(row['likely_duplicate']).lower(),
                "duplicate_of_row" : row["duplicate_of_row"],
            })
    
    valid_count = sum(row["is_valid"] for row in rows)
    invalid_count = len(rows) - valid_count
    repeated_groups = {key: group for key, group in transaction_groups.items() if len(group) > 1}
    likely_groups = [group for group in signatures.values() if len(group) > 1]

    
    paid_rows =[
        row for row in rows
        if row["is_valid"] and row["status"] == "paid"
        and not row["duplicate_transaction_id"] and not row["likely_duplicate"]
    ]
    
    refund_rows = [
        row for row in rows
        if row['is_valid'] and row['status'] == 'refund'
        and not row['duplicate_transaction_id'] and not row['likely_duplicate']
    ]
    
    paid_total = sum((row['amount_decimal'] for row in paid_rows), Decimal('0'))
    refund_total = sum((row['amount_decimal'] for row in refund_rows), Decimal('0'))
    
    report = {
        'input_rows' : len(rows),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "row_count_reconciliation": {
            "valid_rows_plus_invalid_rows": valid_count + invalid_count,
            "matches_input_rows": valid_count + invalid_count == len(rows),
        },
        "duplicates": {
            "repeated_transaction_id_groups": len(repeated_groups),
            "rows_with_repeated_transaction_id": sum(len(group) for group in repeated_groups.values()),
            "extra_rows_from_repeated_transaction_ids": sum(len(group) - 1 for group in repeated_groups.values()),
            "likely_duplicate_groups": len(likely_groups),
            "likely_duplicate_rows_flagged_after_first": sum(len(group) - 1 for group in likely_groups),
            "rows_flagged_as_likely_duplicate": sum(row["likely_duplicate"] for row in rows),
            "note": (
                "Rows with repeated transaction IDs are marked invalid because the ID collision is ambiguous. "
                "For likely duplicates, the first matching signature is retained as the canonical candidate and "
                "later rows are flagged; signature uses normalized customer, amount, date, and order_id, not status."
            ),
        },
        "revenue": {
            "definition": (
                "total_revenue is the sum of valid, non-duplicate rows with status=paid; pending, cancelled, "
                "refund, invalid, repeated-ID, and likely-duplicate rows are excluded."
            ),
            "total_revenue": format(paid_total.quantize(Decimal("0.01")), "f"),
            "valid_refund_amount_total": format(refund_total.quantize(Decimal("0.01")), "f"),
            "net_paid_less_refunds": format((paid_total - refund_total).quantize(Decimal("0.01")), "f"),
            "counted_paid_rows": len(paid_rows),
            "counted_refund_rows" : len(refund_rows),
        },
    }
    
    report_path = out_dir / 'report.json'
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding = 'utf-8')
    return cleaned_path, report_path, report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    
    with args.input_csv.open('r', newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        required = {'transaction_id', 'customer_name', 'amount', 'transaction_date', 'status', 'order_id'}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise SystemExit(f"Input CSV must contain these columns: {', '.join(sorted(required))}")
        raw_rows = list(reader)
        
        
    rows, transaction_groups, signatures = process_rows(raw_rows)
    cleaned_path, report_path, report = write_outputs(rows, transaction_groups, signatures, args.out_dir)
    print(f"Wrote: {cleaned_path}")
    print(f"Wrote: {report_path}")
    print(
        f"Input rows: {report['input_rows']} | valid: {report['valid_rows']} | "
        f"invalid: {report['invalid_rows']} | total revenue: {report['revenue']['total_revenue']}"
    )
    
if __name__ == "__main__":
    main()