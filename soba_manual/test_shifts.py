import tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta
from model import World
from vn_calendar import VIETNAM

class ShiftTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,5,8,tzinfo=VIETNAM)
        self.w=World(seed=55,clock=lambda:self.now)
    def hire(self,role):
        self.w.post_recruitment();c=next(c for c in self.w.candidates if c['role']==role)
        self.assertTrue(self.w.hire(c['id']));e=self.w.employee(c['id']);e['enabled']=True;e['leaves']['2026-10']=[]
        return e
    def test_custom_shift_validation_and_cv_locked_snapshot(self):
        w=self.w;self.assertTrue(w.create_shift('Ca của tôi',600,1140))
        self.assertFalse(w.create_shift('Ca của tôi',600,1140));self.assertFalse(w.create_shift('Sai',1200,600))
        w.shifts[0]['enabled']=False;e=self.hire('contract')
        self.assertEqual(e['agreed_shift']['name'],'Ca của tôi')
        self.assertFalse(w.set_shift(e['id'],480,8));self.assertEqual(e['shift_start'],600)
        w.shifts[-1]['enabled']=False;self.assertEqual(e['agreed_shift']['end'],1140)
        p=w.day_plan(e,self.now.date());self.assertEqual(sum(b-a for a,b,m in p['segments']),480)
        self.assertEqual(len(p['breaks']),1);self.assertEqual(p['breaks'][0][1]-p['breaks'][0][0],60)
    def test_baito_changes_daily_and_all_breaks_unpaid(self):
        w=self.w;w.create_shift('Ca tối',720,1410);e=self.hire('baito');e['traits']=['Chăm','Cẩn thận','Nhanh']
        plans=[w.day_plan(e,self.now.date()+timedelta(days=d)) for d in range(15)]
        self.assertGreater(len({p['shift_name'] for p in plans}),1)
        p=next(p for p in plans if len(p['breaks'])>1 and p['segments'])
        day=next(d for d in e['plans'] if e['plans'][d] is p);self.now=datetime.fromisoformat(day).replace(tzinfo=VIETNAM)
        begin=self.now+timedelta(minutes=p['start']);end=self.now+timedelta(minutes=p['end'])
        worked=w.work_overlap(e,begin,end);expected=sum(b-a for a,b,m in p['segments'])*60
        self.assertEqual(worked,expected);self.assertLess(worked,(p['end']-p['start'])*60)
        self.assertAlmostEqual(e['attendance'][day]['gross'],expected/3600*e['wage'])
        self.assertIs(w.day_plan(e,self.now.date()),p)
    def test_contract_one_break_eight_hours_and_stable_rebuild(self):
        e=self.hire('contract');w=self.w;p=w.day_plan(e,self.now.date())
        first=p['breaks'];e['plans'].clear();self.assertEqual(w.day_plan(e,self.now.date())['breaks'],first)
        self.assertEqual(sum(b-a for a,b,m in p['segments']),480)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);loaded=World.load(path)
            self.assertEqual(loaded.shifts,w.shifts);self.assertEqual(loaded.employee(e['id'])['agreed_shift'],e['agreed_shift'])
            self.assertEqual(loaded.employee(e['id'])['plans'],e['plans'])
    def test_no_suitable_cv_shift_blocks_contract_hire(self):
        w=self.w;w.shifts[0]['enabled']=False;w.create_shift('Ca ngắn',600,840);w.post_recruitment()
        c=next(c for c in w.candidates if c['role']=='contract')
        self.assertIsNone(c['requested_shift']);self.assertFalse(w.hire(c['id']))
