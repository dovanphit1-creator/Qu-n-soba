"""Checks the complete manual service cycle and the user-requested timing rules."""
import tempfile
from pathlib import Path
import unittest
from model import World, COOK_SECONDS, RECIPES


class RulesTest(unittest.TestCase):
    def world(self):
        w = World(seed=42)
        w.spawn_left = 100000
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
        self.assertGreater(w.reputation, 2)

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
        for day, normal, peak in [(1,2,12),(5,7,22),(6,7,22),(7,7,22),(14,17,32)]:
            w.day=day
            w.elapsed=0
            self.assertEqual(w.chance,normal)
            w.elapsed=60*3
            self.assertEqual(w.chance,peak)
            w.elapsed=7*60*3
            self.assertEqual(w.chance,peak)
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
        self.assertLess(w.reputation,2)

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
        self.assertEqual(loaded.reputation,2)


if __name__ == '__main__':
    unittest.main()
