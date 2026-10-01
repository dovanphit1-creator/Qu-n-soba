import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
from model import World,STOCK_COST,COOK_SECONDS
from vn_calendar import VIETNAM


class BaitoKitchenTests(unittest.TestCase):
    def setUp(self):
        self.clock=[datetime(2026,10,2,9,tzinfo=VIETNAM)]
        self.w=World(seed=140,clock=lambda:self.clock[0]);self.w.spawn_left=1e9
        for name in ('Bát/đĩa',*STOCK_COST):self.w.restock(name,20)
        self.w.post_recruitment();c=next(c for c in self.w.applicants() if c['role']=='baito')
        self.w.hire(c['id']);self.e=self.w.employee(c['id']);self.e['leaves']['2026-10']=[]
        self.e['traits']=['Chăm','Cẩn thận','Nhanh'];self.w.set_shift(c['id'],480,10)
        self.e['plans']['2026-10-02']=dict(segments=[[480,1080,'baito']],start=480,end=1080,late=0,absence=False,early=0)
        self.w.update(0);self.e['job']=None
    def seat_customer(self):
        p=self.w.add_party(1);p.drinks=[''];p.drinks_served=['']
        self.w.respond(p.id,'accept');self.w.update(p.buy_seconds);self.w.collect(p.id);self.w.seat(p.id,0)
        self.e['job']=None
        return p
    def tick(self,seconds):
        with patch.object(self.w.rng,'random',return_value=.99):
            for _ in range(seconds):self.clock[0]+=timedelta(seconds=1);self.w.update(1)
    def test_one_baito_performs_entire_service_cycle_without_contract(self):
        p=self.w.add_party(2);p.drinks=['Bò húc','Trà xanh'];p.drinks_served=['','']
        initial=self.w.stock['Mì tươi'];self.tick(2000)
        self.assertEqual(self.w.served,2);self.assertEqual(self.w.stock['Mì tươi'],initial-2)
        self.assertTrue(p.ticket_read);self.assertEqual(p.drinks_served,p.drinks)
        self.assertTrue(self.w.reviews);self.assertFalse(self.w.staff_cooking)
        self.assertEqual(self.w.clean,20);self.assertFalse(self.w.tables[0].dirty)
        self.assertFalse(self.w.tables[0].needs_wipe)
    def test_waiting_group_without_seats_does_not_block_cooking(self):
        self.seat_customer();q=self.w.add_party(4);self.w.respond(q.id,'wait')
        job=self.w.choose_staff_job(self.e,[self.e]);self.assertEqual(job[0][0],'start')
    def test_actionable_horu_precedes_starting_another_pot(self):
        self.seat_customer();q=self.w.add_party(1)
        job=self.w.choose_staff_job(self.e,[self.e]);self.assertEqual(job[0],('door',q.id,'accept'))
    def test_ready_pot_is_lifted_before_horu_task(self):
        p=self.seat_customer();self.w.start_pot(0);self.w.staff_cooking['0']={'gid':p.id,'index':0}
        self.w.pots[0]=COOK_SECONDS;self.w.add_party(1)
        job=self.w.choose_staff_job(self.e,[self.e]);self.assertEqual(job[0],('lift',0))
    def test_support_can_be_disabled_and_resumed(self):
        self.seat_customer();self.assertTrue(self.w.set_kitchen_support(self.e['id'],False))
        self.tick(360);self.assertEqual(self.w.served,0);self.assertTrue(all(p is None for p in self.w.pots))
        self.assertTrue(self.w.set_kitchen_support(self.e['id'],True));self.tick(1000)
        self.assertEqual(self.w.served,1)
    def test_setting_does_not_cancel_task_in_progress(self):
        p=self.seat_customer();task=self.w.choose_staff_job(self.e,[self.e])
        self.e['job']={'action':list(task[0]),'target':list(task[1]),'left':10}
        job=self.e['job'];self.w.set_kitchen_support(self.e['id'],False)
        self.assertIs(self.e['job'],job);self.tick(10)
        self.assertIsNotNone(self.w.pots[0]);self.assertEqual(self.w.staff_cooking['0']['gid'],p.id)
    def test_saved_setting_and_old_employee_migration(self):
        self.w.set_kitchen_support(self.e['id'],False)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';self.w.save(path);loaded=World.load(path)
            self.assertFalse(loaded.employees[0]['kitchen_support'])
            data=json.loads(path.read_text());data['employees'][0].pop('kitchen_support');path.write_text(json.dumps(data))
            migrated=World.load(path);self.assertTrue(migrated.employees[0]['kitchen_support'])
            self.assertEqual(migrated.cash,self.w.cash);self.assertEqual(migrated.employees[0]['wage'],self.e['wage'])

if __name__=='__main__':unittest.main()
