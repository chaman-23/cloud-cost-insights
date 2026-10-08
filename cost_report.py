"""Analyze a normalized cloud billing CSV without cloud credentials."""
import argparse
import calendar
import csv
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {'date', 'service', 'resource_group', 'cost', 'currency'}

def analyze(path, budget=None):
    if budget is not None and (not budget.is_finite() or budget <= 0):
        raise ValueError('Monthly budget must be a positive finite number.')
    months = {}
    currencies = set()
    count = 0
    with open(path, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not REQUIRED.issubset(fields):
            raise ValueError('Expected unique CSV headers: ' + ', '.join(sorted(REQUIRED)))
        for line, row in enumerate(reader, 2):
            if None in row or any(row.get(k) is None or not row[k].strip() for k in REQUIRED):
                raise ValueError(f'Line {line}: missing values or extra fields.')
            try:
                day = date.fromisoformat(row['date'].strip())
                cost = Decimal(row['cost'].strip())
            except (ValueError, InvalidOperation) as exc:
                raise ValueError(f'Line {line}: invalid date or cost.') from exc
            if not cost.is_finite() or cost < 0:
                raise ValueError(f'Line {line}: cost must be finite and non-negative; credits are unsupported.')
            currency = row['currency'].strip().upper()
            if len(currency) != 3 or not currency.isalpha():
                raise ValueError(f'Line {line}: use a three-letter currency code.')
            currencies.add(currency)
            key = day.strftime('%Y-%m')
            m = months.setdefault(key, {'total': Decimal(0), 'service': defaultdict(Decimal),
                'group': defaultdict(Decimal), 'daily': defaultdict(Decimal), 'last': day})
            m['total'] += cost
            m['service'][row['service'].strip()] += cost
            m['group'][row['resource_group'].strip()] += cost
            m['daily'][day.isoformat()] += cost
            m['last'] = max(m['last'], day)
            count += 1
    if not count:
        raise ValueError('CSV contains no billing rows.')
    if len(currencies) != 1:
        raise ValueError('Mixed currencies cannot be added. Split the file by currency first.')
    money = lambda value: str(value.quantize(Decimal('0.01')))
    result = {'currency': next(iter(currencies)), 'rows': count, 'months': {}}
    for key, m in sorted(months.items()):
        last = m['last']
        days = calendar.monthrange(last.year, last.month)[1]
        forecast = m['total'] / last.day * days
        spikes = []
        previous = None
        for day, cost in sorted(m['daily'].items()):
            current = date.fromisoformat(day)
            if previous and (current - previous[0]).days == 1 and previous[1] > 0 and cost > previous[1] * Decimal('1.5'):
                spikes.append({'date': day, 'cost': money(cost), 'previous_day_cost': money(previous[1])})
            previous = current, cost
        result['months'][key] = {
            'actual': money(m['total']), 'last_observed_date': last.isoformat(),
            'linear_month_end_estimate': money(forecast),
            'services': {k: money(v) for k, v in sorted(m['service'].items(), key=lambda x: (-x[1], x[0]))},
            'resource_groups': {k: money(v) for k, v in sorted(m['group'].items())},
            'daily': {k: money(v) for k, v in sorted(m['daily'].items())},
            'spikes_above_50_percent': spikes,
            'monthly_budget': money(budget) if budget is not None else None,
            'estimate_exceeds_budget': forecast > budget if budget is not None else None,
        }
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file', type=Path)
    parser.add_argument('--budget', type=Decimal)
    parser.add_argument('--out', type=Path, default=Path('reports/cost-report.json'))
    args = parser.parse_args()
    try:
        report = analyze(args.csv_file, args.budget)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, InvalidOperation, csv.Error) as exc:
        parser.exit(2, f'Error: {exc}\n')
    for month, data in report['months'].items():
        print(f"{month}: actual {data['actual']} {report['currency']} | linear estimate {data['linear_month_end_estimate']}")
    print(f'Saved {args.out}')

if __name__ == '__main__':
    main()
