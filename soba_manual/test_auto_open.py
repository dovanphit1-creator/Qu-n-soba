import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from datetime import timedelta
from main import App
from auto_open_smoke import scheduled_world


class AutoOpenScreenTests(unittest.TestCase):
    def setUp(self):
        self.app=App(headless=True,persistent=False)
        self.app.world,self.now,self.employee=scheduled_world()
        self.app.modal=None
    def arrive(self):
        self.now[0]+=timedelta(seconds=1);self.app.step(1)
    def test_arrival_exits_each_closed_management_page(self):
        for tab in ('overview','market','menu','staff','day'):
            with self.subTest(tab=tab):
                self.setUp();a=self.app;a.manager_tab=tab;a.input_focus='name'
                self.arrive();a.draw()
                self.assertTrue(a.world.open);self.assertTrue(self.employee['present'])
                self.assertIsNone(a.input_focus);self.assertEqual(a.manager_tab,'overview')
                self.assertIn(('close',),[action for r,action in a.buttons])
    def test_arrival_dismisses_old_report_and_staff_dialogs(self):
        for modal in ('report','hire_contract','fire_staff','cover_shift','confirm_new'):
            with self.subTest(modal=modal):
                self.setUp();a=self.app;a.staff_panel=True;a.modal=modal
                a.drag=('raw',0);a.down=(100,100);a.pending_drag=('raw',0)
                self.arrive();a.draw()
                self.assertIsNone(a.modal);self.assertFalse(a.staff_panel)
                self.assertIsNone(a.drag);self.assertIsNone(a.down);self.assertIsNone(a.pending_drag)
                self.assertIn(('close',),[action for r,action in a.buttons])
    def test_staff_view_remains_available_after_opening_and_has_return(self):
        self.arrive();a=self.app;a.staff_panel=True;a.staff_tab='settings'
        a.step(1);a.draw();self.assertTrue(a.staff_panel)
        r=next(r for r,action in a.buttons if action==('enter_shop',));a.click(r.center)
        a.draw();self.assertFalse(a.staff_panel)
        self.assertIn(('close',),[action for r,action in a.buttons])
    def test_unstocked_shop_stays_closed_when_employee_arrives(self):
        self.app.world.clean=0;self.arrive();self.app.draw()
        self.assertTrue(self.employee['present']);self.assertFalse(self.app.world.open)
        self.assertIn(('open',),[action for r,action in self.app.buttons])
    def test_draw_handles_opened_state_without_waiting_for_next_step(self):
        a=self.app;a.modal='report';a.staff_panel=True
        self.assertTrue(a.world.open_shop());a.draw()
        self.assertIsNone(a.modal);self.assertFalse(a.staff_panel)
        self.assertIn(('close',),[action for r,action in a.buttons])

    def test_restock_after_stock_shutdown_reopens_during_same_shift(self):
        w=self.app.world;w.staff_shutdown_date=w.now.date().isoformat()
        w.stock['Mì tươi']=0
        self.arrive();self.assertFalse(w.open)
        self.assertIn('nguyên liệu',self.employee['status'])
        w.restock('Mì tươi',4)
        self.app.modal='report';self.app.staff_panel=True
        self.app.step(1);self.app.draw()
        self.assertTrue(w.open);self.assertEqual(w.staff_shutdown_date,'')
        self.assertIsNone(self.app.modal);self.assertFalse(self.app.staff_panel)
        self.assertIn(('close',),[a for r,a in self.app.buttons])

    def test_closed_save_with_stale_closing_flag_and_normal_decision(self):
        w=self.app.world;w.closing=True
        w.day_decisions[w.now.date().isoformat()]='normal'
        self.arrive();self.assertTrue(w.open);self.assertFalse(w.closing)

    def test_explicit_manual_and_auto_off_choices_remain_respected(self):
        w=self.app.world;w.staff_auto_open=False
        self.arrive();self.assertFalse(w.open)
        self.assertIn('TẮT',self.employee['status'])
        count=len(w.logs);self.app.step(1);self.assertEqual(len(w.logs),count)
        w.staff_auto_open=True;w.day_decisions[w.now.date().isoformat()]='player'
        self.app.step(1);self.assertFalse(w.open)
        self.assertIn('chủ quán',self.employee['status'])
        w.decide_day(w.now.date().isoformat(),'normal')
        self.app.step(1);self.assertTrue(w.open)

if __name__=='__main__':unittest.main()
