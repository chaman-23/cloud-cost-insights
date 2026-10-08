import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from cost_report import analyze

class CostTests(unittest.TestCase):
    def run_csv(self, rows, budget=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cost.csv'
            path.write_text('date,service,resource_group,cost,currency\n' + rows, encoding='utf-8')
            return analyze(path, budget)

    def test_demo_totals_spike_and_budget(self):
        m = analyze(Path(__file__).parent / 'data/sample-costs.csv', Decimal('400'))['months']['2026-09']
        self.assertEqual(m['actual'], '72.00')
        self.assertEqual(m['linear_month_end_estimate'], '432.00')
        self.assertEqual(m['services']['Virtual Machines'], '62.00')
        self.assertTrue(m['estimate_exceeds_budget'])
        self.assertEqual([s['date'] for s in m['spikes_above_50_percent']], ['2026-09-03'])

    def test_mixed_currency_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Mixed currencies'):
            self.run_csv('2026-01-01,A,G,1,USD\n2026-01-02,A,G,1,INR\n')

    def test_invalid_amounts_rejected(self):
        for amount in ['NaN', 'Infinity', '-1', 'oops']:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.run_csv(f'2026-01-01,A,G,{amount},USD\n')

    def test_decimal_precision_and_month_boundaries(self):
        r = self.run_csv('2024-02-29,A,G,0.10,USD\n2024-02-29,A,G,0.20,USD\n2024-03-01,A,G,1,USD\n')
        self.assertEqual(r['months']['2024-02']['actual'], '0.30')
        self.assertEqual(r['months']['2024-02']['linear_month_end_estimate'], '0.30')
        self.assertEqual(len(r['months']), 2)

    def test_gap_is_not_daily_spike(self):
        r = self.run_csv('2026-01-01,A,G,1,USD\n2026-01-03,A,G,100,USD\n')
        self.assertEqual(r['months']['2026-01']['spikes_above_50_percent'], [])

    def test_empty_and_invalid_budget(self):
        with self.assertRaises(ValueError):
            self.run_csv('')
        with self.assertRaises(ValueError):
            self.run_csv('2026-01-01,A,G,1,USD\n', Decimal('NaN'))

if __name__ == '__main__':
    unittest.main()
