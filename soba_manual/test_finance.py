import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from model import World
from vn_calendar import VIETNAM
from finance import PROVIDERS, STREETS

class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.clock=[datetime(2026,1,2,8,tzinfo=VIETNAM)]
        self.w=World(seed=4,clock=lambda:self.clock[0])

    def test_cv_salary_is_agreed_and_locked(self):
        w=self.w;w.post_recruitment();c=w.candidates[0];requested=c['wage']
        self.assertFalse(w.hire(c['id'],requested+5000))
        self.assertTrue(w.hire(c['id']));e=w.employee(c['id'])
        self.assertEqual(e['agreed_wage'],requested)
        e['wage']=1;w.accrue_wages(e,3600,w.now.date(),False)
        self.assertEqual(e['attendance']['2026-01-02']['gross'],requested)

    def test_meter_invoice_notice_payment_once_and_no_double_expense(self):
        w=self.w;w.use_utility('water',2);m=w.meters['water']
        self.clock[0]=datetime.fromisoformat(m['next_close']).replace(tzinfo=VIETNAM)
        cash=w.cash;w.process_finance();bill=next(b for b in w.bills if b['kind']=='water')
        self.assertEqual((bill['start'],bill['end'],bill['amount']),(0,2,30000))
        self.assertEqual(bill['due'],(w.now.date()+timedelta(days=7)).isoformat())
        self.assertTrue(any('hạn' in s for s in w.logs));self.assertEqual(w.cash,cash)
        profit=sum(r['profit'] for r in w.totals().values())
        self.assertTrue(w.pay_bill(bill['id']));self.assertFalse(w.pay_bill(bill['id']))
        self.assertEqual(w.cash,cash-30000);self.assertEqual(sum(r['profit'] for r in w.totals().values()),profit)

    def test_provider_change_preserves_old_rate(self):
        w=self.w;w.use_utility('electricity',2)
        self.assertTrue(w.change_provider('electricity',1));bill=w.bills[-1]
        self.assertEqual((bill['quantity'],bill['rate'],bill['amount']),(2,3000,6000))
        w.use_utility('electricity',1);w.close_meter('electricity',w.now.date())
        self.assertEqual(w.bills[-1]['amount'],3400)

    def test_prior_year_tax_four_installments_and_loss_zero(self):
        w=self.w;w.ledger['2025-12-30']=dict(revenue=1000003,refunds=0,ingredients=0,electricity=0,water=0,gas=0)
        w.process_finance();bills=[b for b in w.bills if b['kind']=='shop_tax']
        self.assertEqual([b['due'] for b in bills],['2026-06-20','2026-08-20','2026-10-20','2026-12-20'])
        self.assertEqual(sum(b['amount'] for b in bills),100000)
        w.process_finance();self.assertEqual(len([b for b in w.bills if b['kind']=='shop_tax']),4)
        self.assertEqual(w.tax_assessments['2026']['profit'],1000003)
        self.clock[0]=datetime(2027,1,1,tzinfo=VIETNAM);w.process_finance()
        self.assertEqual(w.tax_assessments['2027']['total'],0)

    def test_rent_calendar_months_and_no_retroactive_charges(self):
        w=self.w;self.assertTrue(w.sign_lease(1));self.assertFalse(w.sign_lease(0))
        first=w.bills[-1];self.assertEqual(first['amount'],round(10000000*30/31))
        self.clock[0]=datetime(2026,3,2,tzinfo=VIETNAM);w.process_finance()
        rents=[b for b in w.bills if b['kind']=='rent']
        self.assertEqual([b['amount'] for b in rents],[first['amount'],10000000,10000000])
        w.process_finance();self.assertEqual(len([b for b in w.bills if b['kind']=='rent']),3)

    def test_save_migration_and_meter_continuity(self):
        w=self.w;w.use_utility('gas',1);w.post_recruitment();w.hire(w.candidates[0]['id'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';w.save(p);loaded=World.load(p)
            self.assertEqual(loaded.meters,w.meters);self.assertEqual(loaded.employees[0]['agreed_wage'],w.employees[0]['wage'])
            data=json.loads(p.read_text(encoding='utf-8'));data['version']=8
            for k in ('meters','bills','next_bill','finance_cursor','tax_assessments','lease'):data.pop(k)
            data['employees'][0].pop('agreed_wage');p.write_text(json.dumps(data),encoding='utf-8')
            migrated=World.load(p);self.assertTrue(p.with_suffix('.v8.bak').exists())
            self.assertEqual(migrated.bills[-1]['amount'],38000)
            self.assertEqual(migrated.employees[0]['agreed_wage'],w.employees[0]['wage'])
