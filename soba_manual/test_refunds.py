import unittest,tempfile,json
from datetime import datetime,timedelta
from pathlib import Path
from model import World,Bowl,STOCK_COST
from vn_calendar import VIETNAM

class RefundTests(unittest.TestCase):
    def setUp(self):
        self.clock=datetime(2026,10,5,10,tzinfo=VIETNAM)
        self.w=World(seed=7,clock=lambda:self.clock);self.w.staff_auto_open=False
        for n in ('Bát/đĩa',*STOCK_COST):self.w.restock(n,12)
        self.w.open_shop();self.w.spawn_left=1e9
    def paid(self,size=1,seat=True):
        p=self.w.add_party(size);p.drinks=['']*size;p.drinks_served=['']*size
        self.w.respond(p.id,'accept');self.w.update(p.buy_seconds)
        if seat:self.w.collect(p.id);self.w.seat(p.id,0)
        return p
    def test_paid_ticket_before_collect_can_refund_exactly_once(self):
        p=self.paid(seat=False);cash=self.w.cash;stock=dict(self.w.stock)
        self.assertEqual(p.phase,'ticket');self.assertTrue(self.w.refund_party(p.id))
        self.assertEqual(self.w.cash,cash-p.paid);self.assertEqual(p.refunded,p.paid);self.assertEqual(self.w.stock,stock)
        self.assertEqual(p.phase,'leaving');self.assertFalse(self.w.refund_party(p.id));self.assertEqual(self.w.cash,cash-p.paid)
        total=self.w.totals()['2026-10-05'];self.assertEqual(total['refunds'],p.paid);self.assertEqual(total['net_revenue'],0)
    def test_partial_service_shared_table_bowls_and_other_group(self):
        p=self.paid(2);other=self.paid(1)
        b=Bowl(100,0,toppings=p.recipes[0],stage='prep');self.w.clean-=1;self.w.bowls.append(b)
        self.assertTrue(self.w.serve(b.id,0,p.id));clean=self.w.clean
        self.assertTrue(self.w.refund_party(p.id));self.assertEqual(p.seats,[])
        self.assertEqual(self.w.tables[0].group,other.id);self.assertEqual(self.w.tables[0].dirty,1)
        self.assertTrue(self.w.tables[0].needs_wipe);self.assertEqual(self.w.at_table(0),[other])
        self.assertEqual(self.w.clean,clean);self.assertFalse(self.w.close_shop())
        self.w.clear_table(0);self.assertEqual(self.w.sink,1)
        b=Bowl(101,0,toppings=other.recipes[0],stage='prep');self.w.clean-=1;self.w.bowls.append(b)
        self.assertTrue(self.w.serve(b.id,0,other.id))
    def test_unpaid_or_finished_group_cannot_refund_but_missing_drink_can(self):
        p=self.w.add_party(1);self.assertFalse(self.w.refund_party(p.id))
        p=self.paid();b=Bowl(100,0,toppings=p.recipes[0],stage='prep');self.w.bowls.append(b);self.w.clean-=1
        self.w.serve(b.id,0,p.id);self.assertFalse(self.w.refund_party(p.id))
        p.drinks=['Bò húc'];p.drinks_served=[''];self.assertTrue(self.w.refund_party(p.id))
    def test_cancel_owned_staff_jobs_keep_stock_and_pots(self):
        p=self.paid();self.w.post_recruitment()
        c=self.w.applicants()[0];self.w.hire(c['id']);e=self.w.employee(c['id'])
        self.w.start_pot(0);stock=dict(self.w.stock);self.w.staff_cooking={'0':{'gid':p.id,'index':0}}
        e['job']={'action':['lift',0],'target':[800,400,0],'left':1}
        self.assertTrue(self.w.refund_party(p.id));self.assertIsNone(e['job']);self.assertFalse(self.w.staff_cooking)
        self.assertIsNotNone(self.w.pots[0]);self.assertEqual(stock,self.w.stock)
    def test_cross_day_refund_and_all_profit_periods(self):
        p=self.paid();self.clock+=timedelta(days=1)
        self.w.refund_party(p.id)
        day=self.w.totals()['2026-10-06'];self.assertEqual(day['profit'],-p.paid)
        self.assertEqual(self.w.totals('month')['2026-10']['net_revenue'],0)
        self.assertEqual(self.w.totals('year')['2026']['refunds'],p.paid)
    def test_save_resume_refund_and_v6_migration(self):
        p=self.paid();self.w.refund_party(p.id)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';self.w.save(path);w=World.load(path)
            self.assertEqual(w.group(p.id).refunded,p.paid);self.assertFalse(w.refund_party(p.id))
            data=json.loads(path.read_text(encoding='utf-8'));data['version']=6
            for party in data['parties']:party.pop('refunded')
            path.write_text(json.dumps(data),encoding='utf-8');w=World.load(path)
            self.assertTrue(path.with_suffix('.v6.bak').exists());self.assertEqual(w.cash,self.w.cash)
    def test_no_cash_does_not_trap_customer(self):
        p=self.paid();self.w.cash=0;self.assertTrue(self.w.refund_party(p.id));self.assertEqual(self.w.cash,-p.paid)

if __name__=='__main__':unittest.main()
