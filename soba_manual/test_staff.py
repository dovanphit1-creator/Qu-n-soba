import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,date
from model import World,STOCK_COST,COOK_SECONDS
from catalog import DRINKS,DRINK_PRICES
from staff import income_tax,cycle_key
from vn_calendar import VIETNAM,holiday_name

class StaffTests(unittest.TestCase):
    def world(self):
        self.clock=[datetime(2026,10,2,9,tzinfo=VIETNAM)]
        w=World(seed=54,clock=lambda:self.clock[0]);w.spawn_left=100000
        for name in ['Bát/đĩa',*STOCK_COST]:w.restock(name,20)
        return w
    def hire(self,w,role):
        if not w.applicants():w.post_recruitment()
        c=next(c for c in w.applicants() if c['role']==role);w.hire(c['id']);e=w.employee(c['id'])
        e['traits']=['Chăm','Cẩn thận','Nhanh'];e['leaves']['2026-10']=[]
        w.set_shift(e['id'],8*60,8 if role=='contract' else 10)
        if role=='contract':w.set_overtime(e['id'],2)
        else:e['plans']['2026-10-02']=dict(segments=[[480,1080,'baito']],start=480,end=1080,late=0,absence=False,early=0)
        return e
    def tick(self,w,seconds):
        for _ in range(seconds):self.clock[0]+=timedelta(seconds=1);w.update(1)

    def test_automated_service_and_real_consumption(self):
        w=self.world();a=self.hire(w,'baito');b=self.hire(w,'contract')
        before=w.stock['Mì tươi'];w.update(0);self.assertTrue(w.open)
        p=w.add_party(2);self.tick(w,1250)
        self.assertEqual(w.served,2)
        self.assertEqual(w.stock['Mì tươi'],before-2)
        self.assertTrue(w.reviews)
        self.assertTrue(p.ticket_read)
        self.assertGreater(a['tasks'],0);self.assertGreater(b['tasks'],0)
        self.assertFalse(w.tables[0].needs_wipe);self.assertEqual(w.clean,20)
        self.assertGreater(w.totals()['2026-10-02']['wages'],0)

    def test_leave_schedule_hidden_traits_and_contract_fees(self):
        w=self.world();a=self.hire(w,'baito');b=self.hire(w,'contract')
        for e in (a,b):
            e['leaves']={};days=w.ensure_leave(e,self.clock[0].date())
            self.assertEqual(len(days),9)
            self.assertTrue(all(date.fromisoformat(d).weekday()<4 and not holiday_name(date.fromisoformat(d)) for d in days))
            self.assertEqual(e['observed'],[])
        w.request_leave();self.assertEqual(a['leave_sent'],'2026-10')
        self.assertEqual(w.termination_fee(a['id']),0)
        self.assertEqual(w.termination_fee(b['id']),b['wage']/2)
        cash=w.cash;w.fire(a['id']);self.assertEqual(w.cash,cash)
        w.fire(b['id']);self.assertEqual(w.cash,cash-b['wage']/2)

    def test_daily_pay_exact_once_and_shift_gate(self):
        w=self.world();a=self.hire(w,'baito');w.staff_auto_open=False
        self.clock[0]+=timedelta(hours=1);w.update(3600);gross=a['agreed_wage']
        self.assertEqual(a['attendance']['2026-10-02']['gross'],gross)
        self.clock[0]=self.clock[0].replace(hour=19);before=w.cash
        w.update(0);self.assertEqual(w.cash,before-gross);self.assertEqual(w.payroll[-1]['net'],gross)
        w.update(30);self.assertEqual(w.cash,before-gross)
        self.assertFalse(a['present'])

    def test_overtime_insurance_cutoff_payday_and_no_double_expense(self):
        w=self.world();e=self.hire(w,'contract');w.staff_auto_open=False
        self.clock[0]=self.clock[0].replace(hour=8);w.update(0)
        self.clock[0]+=timedelta(hours=9,minutes=30);w.update(9.5*3600);r=e['attendance']['2026-10-02']
        hour=e['agreed_wage']/22/8
        self.assertAlmostEqual(r['gross'],hour*10) # Friday overtime 200%.
        self.assertAlmostEqual(r['insurance'],hour*8*.105)
        self.assertEqual(cycle_key(date(2026,10,17)),'2026-10')
        self.assertEqual(cycle_key(date(2026,10,18)),'2026-11')
        self.clock[0]=datetime(2026,10,26,23,tzinfo=VIETNAM);before=w.cash;w.update(0);self.assertEqual(w.cash,before)
        cost=round(r['gross'])+round(r['employer'])
        self.clock[0]+=timedelta(days=1);w.update(0);self.assertEqual(w.cash,before-cost)
        profit=w.totals()['2026-10-02']['profit'];w.update(0)
        self.assertEqual(w.cash,before-cost);self.assertEqual(w.totals()['2026-10-02']['profit'],profit)
        pay=w.payroll[-1];self.assertEqual(pay['net'],pay['gross']-pay['insurance']-pay['tax'])
        self.assertEqual(income_tax(15_500_000),0);self.assertEqual(income_tax(45_500_000),2_500_000)

    def test_save_migrates_inventory_reputation_and_active_staff(self):
        w=self.world();e=self.hire(w,'contract');w.update(1)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);loaded=World.load(path)
            self.assertEqual(loaded.employees,w.employees)
            data=json.loads(path.read_text(encoding='utf-8'));data['version']=4;data['reputation']=0
            for name in ('Măng','Kaeshi',*DRINKS):data['stock'].pop(name);data['stock_value'].pop(name)
            for key in ('employees','candidates','staff_cooking','payroll'):data.pop(key)
            path.write_text(json.dumps(data),encoding='utf-8');loaded=World.load(path)
            self.assertEqual(loaded.reputation,5);self.assertEqual(loaded.stock['Măng'],0)
            self.assertTrue(path.with_suffix('.v4.bak').exists())

    def test_drink_ticket_and_delivery_separate_from_recipe(self):
        w=self.world();w.open_shop();p=w.add_party(1)
        p.drinks=['Bò húc'];p.drinks_served=[''];w.respond(p.id,'accept');w.update(p.buy_seconds)
        self.assertEqual(p.paid,p.prices[0]+DRINK_PRICES['Bò húc'])
        w.collect(p.id);w.seat(p.id,0);count=w.stock['Bò húc']
        self.assertFalse(w.serve_drink('Trà xanh',0))
        self.assertTrue(w.serve_drink('Bò húc',0));self.assertEqual(w.stock['Bò húc'],count-1)
        self.assertFalse(w.serve_drink('Bò húc',0))
        self.assertFalse(w.save_menu_item('Sai',1,{'Bò húc':1}))

    def test_reviews_zero_floor_and_unlimited_reputation(self):
        w=self.world();p=w.add_party(1);p.temper=['Khó tính'];p.drinks=['Bò húc'];p.drinks_served=['']
        p.meals=[dict(toppings=['Bột ớt']*10,mushy=True,wait=4000,cleanliness=4)]
        w.reputation=5;w.review(p);self.assertIn('0/5',w.reviews[-1]);self.assertEqual(w.reputation,5)
        p.drinks=[''];p.meals=[dict(toppings=p.recipes[0],mushy=False,wait=210,cleanliness=0)]
        w.reputation=300;w.review(p);self.assertGreater(w.reputation,300);self.assertEqual(w.chance,100)

    def test_ready_sound_only_crossing_and_no_instant_cook(self):
        w=self.world();w.open_shop();w.start_pot(0);w.update(209);self.assertFalse(w.sound_events)
        w.update(1);self.assertEqual(w.sound_events,[0]);w.update(2);self.assertEqual(w.sound_events,[0])

if __name__=='__main__':unittest.main()
