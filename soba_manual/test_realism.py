"""Regression checks for paid queues, per-person timing and manual cleaning."""
import json
import tempfile
from pathlib import Path
import test_game
from model import World, Bowl
import unittest

class RealismTests(unittest.TestCase):
    def world(self):
        return test_game.RulesTest().world()

    def test_profiles_and_paid_customers_wait(self):
        w=self.world();p=w.add_party(4)
        self.assertEqual(len(set(p.eat_seconds)),4)
        self.assertTrue(all(180<=v<=720 for v in p.eat_seconds))
        self.assertTrue(all(6<=v<=27 for v in p.choose_seconds))
        w.respond(p.id,'accept');w.update(p.buy_seconds)
        self.assertEqual(p.phase,'ticket');cash=w.cash
        w.update(7200);self.assertEqual(p.phase,'ticket');self.assertEqual(w.cash,cash)
        w.collect(p.id);w.update(7200);self.assertEqual(p.phase,'ready')
        w.seat(p.id,0);w.update(7200);self.assertEqual(p.phase,'seated')

    def test_queue_patience_and_machine_not_blocked_by_paid_ticket(self):
        w=self.world();p=w.add_party(1);q=w.add_party(1)
        w.respond(p.id,'accept');w.respond(q.id,'accept');q.queue_patience=[1]
        before=w.cash;w.update(2)
        self.assertEqual(q.phase,'leaving');self.assertEqual(w.cash,before)
        w.update(p.buy_seconds);self.assertEqual(p.phase,'ticket')
        r=w.add_party(1);w.respond(r.id,'accept');w.update(r.buy_seconds)
        self.assertEqual(r.phase,'ticket');self.assertEqual(p.phase,'ticket')

    def test_individual_eating_starts_at_service(self):
        w=self.world();p=w.add_party(2);w.respond(p.id,'accept');w.update(p.buy_seconds)
        w.collect(p.id);w.seat(p.id,0)
        for i in range(2):w.start_pot(i)
        w.update(210)
        for i in range(2):w.lift(i)
        b=w.bowls[0];w.move_prep(b.id,0);w.serve(b.id,0)
        duration=p.meals[0]['eat_left'];w.update(60)
        self.assertEqual(p.meals[0]['eat_left'],duration-60);self.assertEqual(p.phase,'seated')
        b=w.bowls[0];w.move_prep(b.id,0);w.serve(b.id,0)
        w.update(min(m['eat_left'] for m in p.meals))
        self.assertEqual(p.phase,'eating')
        w.update(w.eating_remaining(p)+1);self.assertEqual(p.phase,'leaving')

    def test_wash_batch_and_wipe_are_timed(self):
        w=self.world();w.sink=4;clean=w.clean;w.wash()
        self.assertTrue(57<=w.wash_left<=105)
        w.sink=2;w.update(w.wash_left-1);self.assertEqual(w.clean,clean)
        w.update(1);self.assertEqual(w.clean,clean+4);self.assertEqual(w.sink,2)
        self.assertEqual(w.washing,0)
        t=w.tables[0];t.needs_wipe=True;t.soil=4
        w.wipe(0);self.assertTrue(21<=w.wipe_left<=27)
        self.assertTrue(t.needs_wipe);self.assertFalse(w.wipe(0))
        w.update(w.wipe_left);self.assertFalse(t.needs_wipe)

    def test_no_spontaneous_dirt_and_explained_spill(self):
        w=self.world();w.update(7200);self.assertFalse(w.dirt)
        w.mark_dirty(0,'Nước dùng bị đổ khi phục vụ',2)
        self.assertEqual(w.dirt,[2]);self.assertIn('Nước dùng',w.dirt_reasons['2'])
        self.assertFalse(w.close_shop());w.sweep(2);w.update(w.sweep_left)
        self.assertFalse(w.dirt_reasons)

    def test_timer_save_and_v3_migration(self):
        w=self.world();p=w.add_party(2);w.sink=3;w.wash()
        t=w.tables[0];t.needs_wipe=True;t.soil=2;w.wipe(0)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);r=World.load(path)
            self.assertEqual(r.parties[0].eat_seconds,p.eat_seconds)
            self.assertEqual((r.wash_left,r.wipe_left),(w.wash_left,w.wipe_left))
            data=json.loads(path.read_text(encoding="utf-8"));data['version']=3
            for key in ('eat_seconds','choose_seconds','door_patience','wait_patience','queue_patience','buy_seconds','paid_age'):data['parties'][0].pop(key)
            for key in ('wipe_table','wipe_left','dirt_reasons'):data.pop(key)
            data['wash_left']=3;path.write_text(json.dumps(data),encoding="utf-8");r=World.load(path)
            self.assertEqual(len(r.parties[0].eat_seconds),2)
            self.assertGreater(r.wash_left,3);self.assertEqual(r.cash,w.cash)

    def test_existing_timers_scale_once_and_payment_is_unchanged(self):
        w=self.world();p=w.add_party(1)
        p.phase='buying';p.phase_time=30
        p.eat_seconds=[600];p.choose_seconds=[50];p.buy_seconds=70
        p.meals=[dict(eat_total=600,eat_left=400,spill_at=200,wait=90)]
        w.wash_left=100;w.wipe_left=20
        patience=p.door_patience[:]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'old.json';w.save(path)
            data=json.loads(path.read_text(encoding='utf-8'))
            data.pop('service_time_scale')
            path.write_text(json.dumps(data),encoding='utf-8')
            r=World.load(path);q=r.parties[0]
            self.assertEqual((q.eat_seconds,q.choose_seconds,q.buy_seconds),([360],[30],50))
            self.assertEqual(q.phase_time,18)
            self.assertEqual((q.meals[0]['eat_left'],q.meals[0]['spill_at'],q.meals[0]['wait']),(240,120,90))
            self.assertEqual((r.wash_left,r.wipe_left),(60,12))
            self.assertEqual(q.door_patience,patience)
            r.save(path);again=World.load(path)
            self.assertEqual(again.parties,r.parties)
            self.assertEqual((again.wash_left,again.wipe_left),(60,12))
