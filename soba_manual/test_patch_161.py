"""Regressions for abandoned cleaning and finite drink reservations."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from main import App
from model import World, STOCK_COST, DRINKS


class Patch161Tests(unittest.TestCase):
    def world(self):
        w=World(seed=7)
        for name in ('Bát/đĩa',*STOCK_COST):w.restock(name,20)
        w.open_shop();w.spawn_left=1e9
        return w

    def test_resume_dismissed_employee_cleaning_including_saved_progress(self):
        app=App(headless=True,persistent=False)
        for kind,index in [('wash',None),('wipe',0),('sweep',0)]:
            with self.subTest(kind=kind):
                w=self.world();w.post_recruitment();w.hire(w.candidates[0]['id'])
                e=w.employees[0];e['present']=True
                if kind=='wash':w.clean-=2;w.sink=2;w.wash(owner=e['id'])
                elif kind=='wipe':w.tables[0].needs_wipe=True;w.wipe(0,owner=e['id'])
                else:w.mark_dirty(0,'Kiểm thử',0);w.sweep(0,owner=e['id'])
                left=getattr(w,kind+'_left');self.assertTrue(w.fire(e['id']))
                with tempfile.TemporaryDirectory() as d:
                    path=Path(d)/'save.json';w.save(path);w=World.load(path)
                app.world=w
                self.assertEqual(getattr(w,kind+'_left'),left)
                self.assertTrue(app.start_clean_hold((kind,index)))
                # Taking ownership neither restarts work nor charges water twice.
                self.assertEqual(getattr(w,kind+'_left'),left)
                reading=w.meters['water']['reading']
                w.update(left+1)
                self.assertEqual(w.meters['water']['reading'],reading+(.01 if kind=='sweep' else 0))
                if kind=='wash':self.assertEqual(w.washing,0);self.assertEqual(w.clean,20)
                elif kind=='wipe':self.assertFalse(w.tables[0].needs_wipe)
                else:self.assertNotIn(0,w.dirt)
                self.assertTrue(w.close_shop())

    def test_active_employee_keeps_cleaning_but_absent_employee_can_be_replaced(self):
        app=App(headless=True,persistent=False);w=self.world();app.world=w
        w.post_recruitment();w.hire(w.candidates[0]['id']);e=w.employees[0]
        e['present']=True;w.sink=1;w.wash(owner=e['id'])
        self.assertFalse(app.start_clean_hold(('wash',None)))
        e['present']=False
        self.assertTrue(app.start_clean_hold(('wash',None)))

    def test_group_drinks_never_exceed_stock(self):
        w=self.world()
        for name in DRINKS:w.stock[name]=0
        name=next(iter(DRINKS));w.stock[name]=1
        with patch.object(w.rng,'random',return_value=.1):p=w.add_party(4)
        self.assertEqual(p.drinks.count(name),1)
        self.assertTrue(w.respond(p.id,'accept'))
        w.update(p.buy_seconds+1)
        self.assertEqual(p.phase,'ticket')

    def test_two_door_groups_cannot_reserve_same_last_drink(self):
        w=self.world()
        for name in DRINKS:w.stock[name]=0
        name=next(iter(DRINKS));w.stock[name]=1
        with patch.object(w.rng,'random',return_value=.1):
            first=w.add_party(1);second=w.add_party(1)
        self.assertEqual(first.drinks,[name]);self.assertEqual(second.drinks,[name])
        self.assertTrue(w.respond(first.id,'accept'))
        self.assertFalse(w.respond(second.id,'accept'))
        self.assertEqual(second.phase,'door');self.assertEqual(second.paid,0)
        with patch.object(w.rng,'random',return_value=.1):third=w.add_party(1)
        self.assertEqual(third.drinks,[''])


if __name__=='__main__':unittest.main()
