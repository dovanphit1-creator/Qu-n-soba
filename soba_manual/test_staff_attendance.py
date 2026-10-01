import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timedelta
from model import World,STOCK_COST
from vn_calendar import VIETNAM

class AttendanceTests(unittest.TestCase):
    def setUp(self):
        self.clock=datetime(2026,10,5,8,tzinfo=VIETNAM)
        self.w=World(seed=4,clock=lambda:self.clock);self.w.staff_auto_open=False
    def hire(self,role):
        if not self.w.applicants():self.w.post_recruitment()
        c=next(c for c in self.w.applicants() if c['role']==role)
        self.w.hire(c['id']);e=self.w.employee(c['id']);e['leaves']['2026-10']=[]
        self.w.set_shift(e['id'],480,8 if role=='contract' else 6)
        e['traits']=['Chăm','Cẩn thận','Nhanh'];return e
    def advance(self,seconds):
        self.clock+=timedelta(seconds=seconds);self.w.update(seconds)
    def test_no_cv_before_post_and_no_auto_refill(self):
        self.assertEqual(self.w.applicants(),[]);self.assertTrue(self.w.post_recruitment())
        self.assertFalse(self.w.post_recruitment())
        for c in list(self.w.applicants()):
            self.assertTrue(18<self.clock.year-c['birth_year']<=45)
            self.assertTrue(c['hometown']);self.assertTrue(c['cv_traits'])
            self.w.dismiss_applicant(c['id'])
        self.assertEqual(self.w.applicants(),[]);self.assertTrue(self.w.post_recruitment())
    def test_baito_late_break_early_exact_pay_and_machine_entries(self):
        e=self.hire('baito');e['plans']['2026-10-05']=dict(segments=[[495,600,'baito'],[630,780,'baito']],start=480,end=840,late=15,early=60,absence=False)
        self.w.update(0);self.assertFalse(e['present']);self.assertEqual(self.w.clock_events,[])
        self.advance(6*3600)
        r=e['attendance']['2026-10-05'];self.assertEqual(r['seconds'],255*60)
        self.assertEqual(r['gross'],e['wage']*255/60)
        self.assertEqual(sum(p['gross'] for p in self.w.payroll),round(r['gross']))
        self.assertEqual([r['event'] for r in self.w.clock_events],['Điểm danh','Chốt công','Điểm danh','Chốt công'])
        self.assertFalse(e['present']);cash=self.w.cash;self.advance(1800);self.assertEqual(self.w.cash,cash)
    def test_absent_baito_has_no_work_no_wages_no_clock(self):
        e=self.hire('baito');e['plans']['2026-10-05']=dict(segments=[],start=480,end=840,late=0,early=0,absence=True)
        self.advance(3600);self.assertEqual(e['status'],'Nghỉ đột xuất');self.assertFalse(e['attendance']);self.assertFalse(self.w.clock_events)
    def test_contract_fixed_eight_break_and_overtime_only_clock(self):
        e=self.hire('contract');self.assertFalse(self.w.set_shift(e['id'],480,7));self.assertFalse(self.w.set_shift(e['id'],480,9))
        self.assertTrue(self.w.set_overtime(e['id'],2));self.w.update(0)
        self.advance(4*3600);self.assertFalse(e['present']);self.assertEqual(e['status'],'Giải lao · không tính công')
        self.advance(30*60);self.assertTrue(e['present']);self.advance(4*3600)
        self.assertEqual(e['attendance']['2026-10-05']['seconds'],8*3600)
        self.assertEqual(len(self.w.clock_events),1);self.assertEqual(self.w.clock_events[0]['event'],'Vào tăng ca')
        self.advance(2*3600);self.assertFalse(e['present']);r=e['attendance']['2026-10-05']
        hour=e['wage']/22/8;self.assertAlmostEqual(r['gross'],hour*(8+2*1.5))
        self.assertAlmostEqual(r['insurance'],hour*8*.105)
        self.assertEqual([x['mode'] for x in self.w.clock_events],['overtime','overtime'])
    def test_disabled_closed_and_offline_time_not_paid(self):
        e=self.hire('baito');self.w.set_shift(e['id'],480,6,False);self.advance(3600);self.assertFalse(e['attendance'])
        self.w.set_shift(e['id'],480,6,True);self.w.decide_day('2026-10-05','closed');self.advance(3600);self.assertFalse(e['attendance'])
        self.w.decide_day('2026-10-05','normal');self.clock+=timedelta(days=1);self.w.update(0)
        self.assertFalse(e['attendance'])
    def test_leave_coverage_gap_invite_answer_and_closure(self):
        a=self.hire('baito');b=self.hire('contract');self.w.request_leave()
        key='2026-10-06';a['leaves']['2026-10']=[key];b['leaves']['2026-10']=[key]
        rows=[r for r in self.w.coverage_report() if r['date']==key]
        self.assertEqual({r['position'] for r in rows},{'floor','kitchen'})
        # Force deterministic refusal; it is saved and cannot be rerolled by pressing again.
        from unittest.mock import patch
        with patch.object(self.w.rng,'random',return_value=.99):self.assertFalse(self.w.invite_cover(a['id'],key,'floor',480,10))
        with patch.object(self.w.rng,'random',return_value=0):self.assertFalse(self.w.invite_cover(a['id'],key,'floor',480,10))
        c=next(c for c in self.w.applicants() if c['role']=='baito');self.w.hire(c['id']);helper=self.w.employee(c['id']);helper['leave_sent']='2026-10'
        with patch.object(self.w.rng,'random',return_value=0):self.assertTrue(self.w.invite_cover(helper['id'],key,'floor',480,10))
        rows=[r for r in self.w.coverage_report() if r['date']==key];self.assertEqual([r['position'] for r in rows],['kitchen'])
        self.w.decide_day(key,'closed');self.assertFalse([r for r in self.w.coverage_report() if r['date']==key])
        self.w.decide_day(key,'normal');self.assertTrue([r for r in self.w.coverage_report() if r['date']==key])
    def test_v5_migration_preserves_money_hours_and_contract(self):
        e=self.hire('contract');self.advance(3600)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';self.w.save(p);data=json.loads(p.read_text(encoding="utf-8"));data['version']=5
            for k in ('recruitment_posted','recruitment_round','coverage_start','coverage_end','day_decisions','cover_invites','clock_events'):data.pop(k)
            for e0 in data['employees']:
                e0['shift_hours']=10
                for k in ('plans','clocked_in','clock_mode','clock_date','cover_days','announced_plan','overtime_hours'):e0.pop(k)
            p.write_text(json.dumps(data),encoding="utf-8");w=World.load(p);new=w.employees[0]
            self.assertEqual(w.cash,self.w.cash);self.assertEqual(new['attendance'],e['attendance']);self.assertEqual(new['shift_hours'],8);self.assertEqual(new['overtime_hours'],2)
            self.assertTrue(p.with_suffix('.v5.bak').exists())

if __name__=='__main__':unittest.main()
