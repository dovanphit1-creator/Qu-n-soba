"""Checks the complete manual service cycle and the user-requested timing rules."""
import tempfile
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone, date
from vn_calendar import VIETNAM, holiday_name
from model import World, COOK_SECONDS, RECIPES


class RulesTest(unittest.TestCase):
    def world(self):
        w = World(seed=42)
        w.spawn_left = 100000
        for name in ['Mì tươi','Nước dùng','Hành','Tôm','Bò','Trứng']:
            w.restock(name,20)
        w.restock('Bát/đĩa',24)
        w.open_shop()
        return w

    def ready_party(self, size=2):
        w = self.world()
        p = w.add_party(size)
        self.assertFalse(w.seat(p.id, 1))
        self.assertTrue(w.respond(p.id, 'accept'))
        w.update(8)
        self.assertEqual(p.phase, 'ticket')
        self.assertFalse(w.seat(p.id, 1))
        self.assertTrue(w.collect(p.id))
        return w, p

    def test_full_manual_cycle(self):
        w, p = self.ready_party(2)
        self.assertTrue(w.seat(p.id, 0))
        for i in range(2):
            self.assertTrue(w.start_pot(i))
        w.update(210)
        for i in range(2):
            self.assertTrue(w.lift(i))
            b = w.bowls[-1]
            self.assertFalse(w.topping(b.id, 'Hành'))
            self.assertTrue(w.move_prep(b.id, 0))
            for top in RECIPES[p.orders[i]]:
                self.assertTrue(w.topping(b.id, top))
            self.assertTrue(w.serve(b.id, 0))
        self.assertEqual(p.phase, 'eating')
        w.update(35)
        self.assertEqual(w.tables[0].dirty, 2)
        self.assertEqual(w.clean, 22)
        self.assertFalse(w.wipe(0))
        self.assertTrue(w.clear_table(0))
        self.assertEqual(w.sink, 2)
        w.update(30)
        self.assertEqual(w.sink, 2, 'Sink must never wash automatically')
        self.assertTrue(w.tables[0].needs_wipe)
        self.assertTrue(w.wipe(0))
        self.assertTrue(w.wash())
        w.update(4)
        self.assertEqual(w.clean, 24)
        self.assertEqual(w.sink, 0)
        self.assertGreater(w.reputation, 7)

    def test_exact_cook_and_grace_window(self):
        w = self.world()
        w.start_pot(0)
        w.update(209.99)
        self.assertEqual(w.pot_state(0), 'cooking')
        self.assertFalse(w.lift(0))
        w.update(.01)
        self.assertEqual(w.pot_state(0), 'ready')
        w.update(10)
        self.assertEqual(w.pot_state(0), 'ready')
        w.update(.001)
        self.assertEqual(w.pot_state(0), 'mushy')
        self.assertTrue(w.lift(0))
        self.assertTrue(w.bowls[0].mushy)
        self.assertTrue(w.move_prep(w.bowls[0].id, 0))
        self.assertTrue(w.start_pot(0))
        self.assertTrue(w.discard_pot(0))
        self.assertIsNone(w.pots[0])

    def test_arrival_bonuses_and_no_reputation_ceiling(self):
        w = self.world()
        for day, normal, peak in [(date(2026,9,30),2,7), (date(2026,10,2),7,12),
                                  (date(2026,10,3),7,12), (date(2026,10,4),7,12),
                                  (date(2026,9,2),12,17), (date(2026,2,17),12,17)]:
            for hour, expected in [(10, normal), (11, peak), (17, peak), (20, normal)]:
                w._clock=lambda d=day,h=hour: datetime(d.year,d.month,d.day,h,tzinfo=VIETNAM)
                self.assertEqual(w.chance,expected)
        w.reputation=400
        self.assertEqual(w.chance,100)
        self.assertEqual(w.reputation,400)

    def test_capacity_bad_food_and_reviews(self):
        w,p=self.ready_party(3)
        self.assertFalse(w.seat(p.id,0))
        self.assertTrue(w.seat(p.id,1))
        p.temper=['Dễ tính','Bình thường','Khó tính']
        for i in range(3):
            w.start_pot(i)
        w.update(221)
        for i in range(3):
            w.lift(i)
            w.move_prep(w.bowls[0].id, 0)
            # Intentionally missing every topping: serving is allowed.
            w.serve(w.bowls[0].id,1)
        w.update(35)
        self.assertEqual(len(w.reviews),3)
        self.assertGreaterEqual(w.reputation,0)
        self.assertLess(w.reputation,7)

    def test_vietnam_time_and_holidays(self):
        w=self.world()
        w._clock=lambda: datetime(2026,9,29,17,30,tzinfo=timezone.utc)
        self.assertEqual(w.now.date(),date(2026,9,30))
        self.assertEqual(w.minute,30)
        self.assertIn('Tết',holiday_name(date(2026,2,17)))
        self.assertIn('Hùng Vương',holiday_name(date(2026,4,26)))
        self.assertIn('nghỉ bù',holiday_name(date(2026,4,27)))
        self.assertIn('Văn hóa',holiday_name(date(2026,11,24)))
        self.assertFalse(holiday_name(date(2026,9,30)))
        before=w.now
        w.update(1000)
        self.assertEqual(w.now,before, 'Game elapsed time cannot advance the calendar')

    def test_new_economy_and_purchase_gate(self):
        w=World()
        self.assertEqual(w.cash,10000000)
        self.assertEqual(w.reputation,7)
        self.assertFalse(w.open)
        self.assertEqual(w.clean,0)
        self.assertTrue(all(v==0 for v in w.stock.values()))
        self.assertFalse(w.open_shop())
        for name in ('Bát/đĩa','Mì tươi','Nước dùng','Hành'):
            self.assertTrue(w.restock(name,10))
        self.assertTrue(w.open_shop())
        cash=w.cash
        self.assertFalse(w.restock('Mì tươi',10))
        self.assertFalse(w.restock('Bát/đĩa',1))
        self.assertEqual(w.cash,cash)

    def test_closing_cleanup_and_costs_no_double_charge(self):
        w=self.world()
        start_cash=w.cash
        w.start_pot(0)
        w.update(210)
        self.assertFalse(w.close_shop())
        self.assertTrue(w.open)
        self.assertTrue(w.closing)
        w.discard_pot(0)
        self.assertFalse(w.close_shop())
        self.assertTrue(w.dirt)
        for spot in w.dirt[:]:w.sweep(spot)
        self.assertTrue(w.close_shop())
        report=w.last_report
        self.assertEqual(report['ingredients'],6000)
        self.assertEqual(report['gas'],800)
        self.assertEqual(report['electricity'],350)
        self.assertEqual(report['water'],500)
        self.assertEqual(report['profit'],-7650)
        self.assertEqual(w.cash,start_cash-1650)
        cash=w.cash
        self.assertFalse(w.close_shop())
        self.assertEqual(w.cash,cash)
        w.open_shop()
        self.assertTrue(w.close_shop())
        self.assertEqual(w.cash,cash)
        self.assertEqual(w.last_report['payment'],0)

    def test_history_daily_monthly_yearly_and_reload(self):
        w=World()
        for day,revenue in [(date(2026,9,29),100000),(date(2026,9,30),200000),(date(2026,10,1),300000)]:
            w._clock=lambda d=day:datetime(d.year,d.month,d.day,12,tzinfo=VIETNAM)
            w.record('revenue',revenue)
            w.record('ingredients',10000)
        self.assertEqual(w.totals('month')['2026-09']['profit'],280000)
        self.assertEqual(w.totals('year')['2026']['profit'],570000)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.json';w.save(path);loaded=World.load(path)
        self.assertEqual(loaded.ledger,w.ledger)

    def test_save_restores_active_game(self):
        w,p=self.ready_party(2)
        w.seat(p.id,1)
        w.start_pot(0)
        w.update(13)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json'
            w.save(path)
            loaded=World.load(path)
        self.assertEqual(loaded.pots[0],13)
        self.assertEqual(loaded.group(p.id).orders,p.orders)
        self.assertEqual(loaded.tables[1].group,p.id)
        self.assertEqual(loaded.reputation,7)


if __name__ == '__main__':
    unittest.main()
