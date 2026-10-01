import json,tempfile,unittest
from datetime import timedelta
from pathlib import Path
from model import World,STOCK_COST
import test_baito_kitchen as fixtures


class EarlyClosePayTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.BaitoKitchenTests();f.setUp();f.e['shortage_policy']='close'
        for n in f.w.stock:f.w.stock[n]=0
        return f

    def close(self,f):
        f.w.mark_dirty(0,'Vết nước cạnh bồn',1)
        for _ in range(200):
            f.tick(1)
            if not f.w.open:break
        self.assertFalse(f.w.open)
        return f.w.now.date().isoformat()

    def test_cleanup_is_paid_then_baito_clocks_out_and_money_stops(self):
        f=self.fixture();w=f.w;key=self.close(f);e=f.e
        self.assertGreater(e['attendance'][key]['seconds'],0)
        self.assertFalse(e['present']);self.assertFalse(e['clocked_in'])
        self.assertEqual(e['job'],None);self.assertIn('Đã nghỉ hôm nay',e['status'])
        self.assertEqual(w.clock_events[-1]['event'],'Chốt công')
        row=dict(e['attendance'][key]);cash=w.cash;events=len(w.clock_events);paid=len(w.payroll)
        self.assertEqual(row['paid_gross'],round(row['gross']))
        f.tick(1200)
        self.assertEqual(e['attendance'][key],row);self.assertEqual(w.cash,cash)
        self.assertEqual(len(w.clock_events),events);self.assertEqual(len(w.payroll),paid)
        self.assertFalse(e['present'])

    def test_contract_base_ot_and_later_baito_shift_stop_for_today(self):
        f=self.fixture();w=f.w
        c=next(c for c in w.applicants() if c['role']=='contract');w.hire(c['id']);chef=w.employee(c['id'])
        chef['leaves']['2026-10']=[]
        chef['plans']['2026-10-02']={'segments':[[480,720,'regular'],[750,990,'regular'],[990,1050,'overtime']], 'start':480,'end':1050,'late':0,'early':0,'absence':False}
        c=next(c for c in w.applicants() if c['role']=='baito');w.hire(c['id']);later=w.employee(c['id']);later['leaves']['2026-10']=[]
        later['plans']['2026-10-02']={'segments':[[720,1080,'baito']], 'start':720,'end':1080,'late':0,'early':0,'absence':False}
        key=self.close(f);gross=chef['attendance'][key]['gross']
        self.assertFalse(chef['present']);self.assertFalse(later['present'])
        f.clock[0]+=timedelta(hours=8);w.update(8*3600)
        self.assertEqual(chef['attendance'][key]['gross'],gross)
        self.assertEqual(chef['attendance'][key]['ot_premium'],0)
        self.assertFalse(later['attendance']);self.assertFalse(later['clocked_in'])
        self.assertTrue(w.set_overtime(chef['id'],1));w.update(0)
        self.assertFalse(chef['present']);self.assertIn('Đã nghỉ hôm nay',chef['status'])

    def test_saved_release_survives_reload_without_duplicate_pay(self):
        f=self.fixture();w=f.w;key=self.close(f)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';w.save(p);loaded=World.load(p);loaded._clock=lambda:f.clock[0]
            cash=loaded.cash;row=dict(loaded.employees[0]['attendance'][key]);count=len(loaded.payroll)
            f.clock[0]+=timedelta(minutes=30);loaded.update(1800)
            self.assertEqual(loaded.cash,cash);self.assertEqual(loaded.employees[0]['attendance'][key],row)
            self.assertEqual(len(loaded.payroll),count);self.assertFalse(loaded.employees[0]['present'])

    def test_active_contract_overtime_is_clocked_out_when_shop_closes(self):
        f=self.fixture();w=f.w
        c=next(c for c in w.applicants() if c['role']=='contract');w.hire(c['id']);e=w.employee(c['id']);e['leaves']['2026-10']=[]
        e['plans']['2026-10-02']={'segments':[[480,720,'regular'],[750,990,'regular'],[990,1110,'overtime']], 'start':480,'end':1110,'late':0,'early':0,'absence':False}
        f.clock[0]=f.clock[0].replace(hour=17)
        w.mark_dirty(0,'Vết nước cạnh bồn',1);w.update(0)
        self.assertTrue(e['clocked_in']);self.assertEqual(e['clock_mode'],'overtime')
        key=self.close(f);row=dict(e['attendance'][key]);self.assertGreater(row['ot_premium'],0)
        self.assertFalse(e['clocked_in']);self.assertFalse(e['present'])
        self.assertEqual([r['event'] for r in w.clock_events if r['employee']==e['id']],['Vào tăng ca','Chốt công'])
        f.tick(600);self.assertEqual(e['attendance'][key],row)

    def test_already_closed_171_save_releases_before_first_frame_pay(self):
        f=self.fixture();w=f.w;key=self.close(f)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';w.save(p);data=json.loads(p.read_text(encoding='utf-8'))
            data['staff_reports']=[r for r in data['staff_reports'] if r.get('reason')!='staff_released']
            e=data['employees'][0];e['plans'][key].pop('released_at')
            e['plans'][key]['segments']=[[480,1080,'baito']]
            e['clock_mode']='baito';e['clocked_in']=True;e['present']=True
            p.write_text(json.dumps(data),encoding='utf-8');loaded=World.load(p);loaded._clock=lambda:f.clock[0]
            row=dict(loaded.employees[0]['attendance'][key]);cash=loaded.cash
            f.clock[0]+=timedelta(seconds=10);loaded.update(10)
            self.assertEqual(loaded.employees[0]['attendance'][key],row);self.assertEqual(loaded.cash,cash)
            self.assertFalse(loaded.employees[0]['present']);self.assertFalse(loaded.employees[0]['clocked_in'])

    def test_tomorrow_shift_and_signed_contract_remain_available(self):
        f=self.fixture();w=f.w;key=self.close(f)
        for n in STOCK_COST:w.restock(n,5)
        w.update(0);self.assertFalse(w.open);self.assertFalse(f.e['present'])
        f.clock[0]+=timedelta(days=1)
        tomorrow=w.now.date().isoformat()
        f.e['plans'][tomorrow]={'segments':[[480,1080,'baito']], 'start':480,'end':1080,'late':0,'early':0,'absence':False}
        w.update(0);self.assertTrue(w.open);self.assertTrue(f.e['present'])
        self.assertNotIn('released_at',w.day_plan(f.e,w.now.date()))


if __name__=='__main__':unittest.main()
