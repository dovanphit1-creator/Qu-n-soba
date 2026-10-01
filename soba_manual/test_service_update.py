import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import unittest,tempfile,json
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
import pygame as pg
from main import App,SINK,TABLE_LAYOUT,DIRT_POS
from model import World,STOCK_COST
import test_baito_kitchen as fixtures
from operations import manage_shortage,complete_purchase,reimburse


class ServiceUpdateTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.BaitoKitchenTests();f.setUp();f.e['shortage_policy']='restock'
        return f
    def test_helpers_do_not_take_idle_colleagues_position(self):
        f=self.fixture();w=f.w;e=f.e;f.seat_customer()
        c=next(c for c in w.applicants() if c['role']=='contract');w.hire(c['id']);chef=w.employee(c['id']);chef['present']=True;chef['job']=None
        self.assertIsNone(w.choose_staff_job(e,[e,chef]))
        w.parties.clear();q=w.add_party(1);w.player_idle=True
        self.assertIsNone(w.choose_staff_job(chef,[e,chef]))
        self.assertEqual(w.choose_staff_job(e,[e,chef])[0][0],'door')
    def test_baito_supports_overloaded_chef_after_finishing_horu(self):
        f=self.fixture();w=f.w;e=f.e;p=f.seat_customer();p.size=2;p.recipes*=2;p.orders*=2;p.prices*=2;p.drinks*=2;p.drinks_served*=2
        c=next(c for c in w.applicants() if c['role']=='contract');w.hire(c['id']);chef=w.employee(c['id']);chef['present']=True
        chef['job']={'action':['start',0,p.id,0],'left':10,'target':[836,396,0]}
        self.assertEqual(w.choose_staff_job(e,[e,chef])[0],('start',1,p.id,1))
    def test_reserved_horu_task_does_not_hide_other_primary_work(self):
        f=self.fixture();w=f.w;e=f.e;f.seat_customer();first=w.add_party(1);second=w.add_party(1)
        c=next(c for c in w.applicants() if c['role']=='baito');w.hire(c['id']);other=w.employee(c['id']);other['present']=True
        other['job']={'action':['door',first.id,'accept'],'left':10,'target':[first.x,first.y,0]}
        task=w.choose_staff_job(e,[e,other]);self.assertEqual(task[0],('door',second.id,'accept'))

    def test_wait_decision_persists_and_card_numbers_are_unique(self):
        f=self.fixture();w=f.w
        q=w.add_party(1);q.in_a_hurry=True;self.assertTrue(w.respond(q.id,'wait'));self.assertEqual(q.phase,'leaving');self.assertEqual(q.wait_number,0)
        for _ in range(2):
            p=w.add_party(1);p.in_a_hurry=False;w.respond(p.id,'wait')
        self.assertEqual([p.wait_number for p in w.parties if p.phase=='waiting'],[1,2])
        self.assertFalse(w.respond(p.id,'wait'));self.assertEqual(w.next_wait_number,3)
    def test_counts_are_people_and_star_average_is_weighted_over_all_ratings(self):
        f=self.fixture();w=f.w;p=w.add_party(2);p.drinks=['',''];p.drinks_served=['',''];w.respond(p.id,'accept')
        self.assertEqual(w.totals()[w.now.date().isoformat()]['customers'],2)
        w.respond(p.id,'accept');self.assertEqual(w.totals()[w.now.date().isoformat()]['customers'],2)
        for score in [5]*20+[0,1]:w.record('star_sum',score);w.record('rating_count',1)
        row=w.totals()[w.now.date().isoformat()];self.assertEqual(row['rating_count'],22);self.assertAlmostEqual(row['average_stars'],101/22)
    def test_player_cleaning_requires_hold_and_releasing_pauses(self):
        a=App(headless=True,persistent=False);a.world=self.fixture().w;a.world.employees=[];a.modal=None;a.screen_open=True;a.draw()
        a.world.sink=3;initial=a.world.clean
        def event(kind,point):
            pos=(int(point[0]*a.scale+a.offset[0]),int(point[1]*a.scale+a.offset[1]));a.event(pg.event.Event(kind,button=1,pos=pos))
        event(pg.MOUSEBUTTONDOWN,SINK.center);left=a.world.wash_left;a.step(1);self.assertLess(a.world.wash_left,left)
        event(pg.MOUSEBUTTONUP,SINK.center);left=a.world.wash_left;a.step(60);self.assertEqual(a.world.wash_left,left);self.assertEqual(a.world.clean,initial)
        event(pg.MOUSEBUTTONDOWN,SINK.center);a.step(left+1);event(pg.MOUSEBUTTONUP,SINK.center);self.assertEqual(a.world.clean,initial+3)
        a.world.tables[0].needs_wipe=True;a.world.tables[0].soil=2
        event(pg.MOUSEBUTTONDOWN,TABLE_LAYOUT[0][:2]);a.step(1);event(pg.MOUSEBUTTONUP,TABLE_LAYOUT[0][:2]);left=a.world.wipe_left;a.step(50);self.assertEqual(a.world.wipe_left,left)
        event(pg.MOUSEBUTTONDOWN,TABLE_LAYOUT[0][:2]);a.step(left+1);event(pg.MOUSEBUTTONUP,TABLE_LAYOUT[0][:2]);self.assertFalse(a.world.tables[0].needs_wipe)
        a.world.mark_dirty(0,'Thử vết nước',2);point=DIRT_POS[2]
        event(pg.MOUSEBUTTONDOWN,point);a.step(1);a.event(pg.event.Event(pg.WINDOWFOCUSLOST));left=a.world.sweep_left;a.step(60);self.assertEqual(a.world.sweep_left,left)
        event(pg.MOUSEBUTTONDOWN,point);a.step(left+1);event(pg.MOUSEBUTTONUP,point);self.assertNotIn(2,a.world.dirt)
    def test_staff_cleans_for_real_duration_and_break_pauses(self):
        f=self.fixture();w=f.w;e=f.e;w.sink=4
        w.finish_staff_job(e,{'action':['wash'],'target':[965,320,0]});self.assertEqual(e['job']['action'],['clean_wait','wash']);self.assertEqual(w.wash_owner,e['id'])
        initial=w.wash_left;w.update(1);self.assertLess(w.wash_left,initial);self.assertTrue(w.washing)
        e['present']=False;left=w.wash_left;self.assertFalse(w.cleanup_active('wash',e['id']))
        e['present']=True;self.assertTrue(w.cleanup_active('wash',e['id']))
    def test_shortage_refunds_unservable_guests_and_closes_without_reopening(self):
        f=self.fixture();w=f.w;e=f.e;e['shortage_policy']='close';p=f.seat_customer();cash=w.cash
        for n in p.recipes[0]:w.stock[n]=0
        e['job']=None;manage_shortage(w,[e]);self.assertTrue(w.closing);self.assertEqual(p.refunded,p.paid);self.assertEqual(w.cash,cash-p.paid)
        with patch.object(w.rng,'random',return_value=.99):f.tick(500)
        self.assertFalse(w.open);self.assertTrue(w.staff_reports);self.assertEqual(w.staff_shutdown_date,w.now.date().isoformat())
        w.update(0);self.assertFalse(w.open)
    def test_restock_uses_advance_and_reimburses_exactly_once(self):
        f=self.fixture();w=f.w;e=f.e;p=f.seat_customer();w.stock['Nước dùng']=0;e['job']=None;cash=w.cash
        manage_shortage(w,[e]);self.assertEqual(e['job']['action'][0],'shop');self.assertEqual(w.cash,cash)
        items=e['job']['action'][1];self.assertGreater(items['Nước dùng'],0)
        complete_purchase(w,e,items);cost=sum(STOCK_COST[n]*q for n,q in items.items());self.assertEqual(w.cash,cash)
        self.assertEqual(w.staff_purchases[-1]['items'],items)
        advance=reimburse(w,e,w.now.date().isoformat());self.assertEqual(advance,cost);self.assertEqual(w.cash,cash-cost)
        self.assertEqual(reimburse(w,e,w.now.date().isoformat()),0)
    def test_refuses_group_without_required_topping_even_with_noodles(self):
        f=self.fixture();w=f.w;p=w.add_party(1);w.stock[p.recipes[0][0]]=0
        self.assertFalse(w.party_stock_available(p));self.assertFalse(w.respond(p.id,'accept'))
    def test_cleanup_and_receipts_survive_reload_paused(self):
        f=self.fixture();w=f.w;w.sink=3;w.wash(owner='player');w.player_cleaning='wash';w.update(1)
        complete_purchase(w,f.e,{'Hành':2});w.mark_dirty(0,'Nước',1);w.sweep(1,owner='player')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);loaded=World.load(path)
            self.assertEqual(loaded.staff_purchases,w.staff_purchases);self.assertEqual(loaded.sweep_left,w.sweep_left);self.assertIsNone(loaded.player_cleaning)
            self.assertEqual(loaded.wash_owner,'player')

if __name__=='__main__':unittest.main()
