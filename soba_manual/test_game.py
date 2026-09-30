"""Checks the complete manual service cycle and the user-requested timing rules."""
import tempfile
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone, date
from vn_calendar import VIETNAM, holiday_name
from model import World, COOK_SECONDS, RECIPES, STOCK_COST, TABLE_COST, CHAIR_COST


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
        w.tables[0].capacity=2
        self.assertFalse(w.seat(p.id,0))
        w.tables[0].capacity=4
        self.assertTrue(w.seat(p.id,0))
        p.temper=['Dễ tính','Bình thường','Khó tính']
        for i in range(3):
            w.start_pot(i)
        w.update(221)
        for i in range(3):
            w.lift(i)
            w.move_prep(w.bowls[0].id, 0)
            # Intentionally missing every topping: serving is allowed.
            w.serve(w.bowls[0].id,0)
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
        w.seat(p.id,0)
        w.start_pot(0)
        w.update(13)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json'
            w.save(path)
            loaded=World.load(path)
        self.assertEqual(loaded.pots[0],13)
        self.assertEqual(loaded.group(p.id).orders,p.orders)
        self.assertEqual(loaded.tables[0].group,p.id)
        self.assertEqual(loaded.reputation,7)

    def test_shared_seats_service_and_cleanup_while_occupied(self):
        w,p=self.ready_party(2)
        self.assertTrue(w.seat(p.id,0))
        q=w.add_party(2)
        w.respond(q.id,'accept');w.update(8);w.collect(q.id)
        self.assertTrue(w.seat(q.id,0))
        self.assertFalse(w.can_fit(1))
        self.assertFalse(set(p.seats)&set(q.seats))
        for i in range(4):w.start_pot(i)
        w.update(210)
        for i in range(4):w.lift(i)
        b=w.bowls[0];w.move_prep(b.id,0)
        self.assertFalse(w.serve(b.id,0), 'Shared table requires an explicit group')
        for i in range(2):
            b=w.bowls[0];w.move_prep(b.id,0)
            for name in q.recipes[i]:w.topping(b.id,name)
            self.assertTrue(w.serve(b.id,0,q.id))
        w.update(35)
        self.assertEqual(p.phase,'seated')
        self.assertEqual(w.tables[0].dirty,2)
        self.assertTrue(w.clear_table(0))
        self.assertTrue(w.wipe(0))
        self.assertTrue(w.can_fit(2))
        for i in range(2):
            b=w.bowls[0];w.move_prep(b.id,0)
            self.assertTrue(w.serve(b.id,0,p.id))
        self.assertEqual(p.phase,'eating')
        self.assertEqual(w.tables[0].group,p.id)

    def test_purchase_expansion_and_floor_limit(self):
        w=World()
        self.assertEqual([(t.capacity,t.floor,t.slot) for t in w.tables],[(4,0,0)])
        start=w.cash
        self.assertTrue(w.buy_table(0))
        self.assertEqual(w.tables[1].capacity,0)
        for _ in range(4):self.assertTrue(w.buy_chair(1))
        self.assertFalse(w.buy_chair(1))
        self.assertEqual(w.cash,start-TABLE_COST-4*CHAIR_COST)
        self.assertTrue(w.build_floor())
        self.assertTrue(w.buy_table(1))
        self.assertEqual(w.tables[-1].floor,1)
        w.cash=20_000_000
        self.assertTrue(w.build_floor())
        self.assertFalse(w.build_floor())
        for _ in range(4):self.assertTrue(w.buy_table(0))
        self.assertFalse(w.buy_table(0))
        w.open=True
        self.assertFalse(w.buy_table(2));self.assertFalse(w.buy_chair(2))
        w.mark_dirty(2)
        self.assertTrue(all(8<=i<12 for i in w.dirt))
        self.assertFalse(w.close_shop())

    def test_supplier_deadline_timezone_offline_and_price(self):
        clock=[datetime(2026,9,30,22,59,59,tzinfo=VIETNAM)]
        w=World(clock=lambda:clock[0])
        self.assertFalse(w.place_order({'Mì tươi':10}))
        self.assertTrue(w.sign_contract())
        self.assertEqual(w.contract_until,'2026-10-30')
        self.assertTrue(w.place_order({'Mì tươi':10,'Trứng':5}))
        self.assertEqual(w.cash,10_000_000-81600)
        self.assertEqual(w.stock['Mì tươi'],0)
        self.assertFalse(w.place_order({'Mì tươi':1}))
        clock[0]=datetime(2026,10,1,0,59,59,tzinfo=timezone.utc) # 07:59:59 VN
        w.update(0);self.assertEqual(w.stock['Mì tươi'],0)
        clock[0]+=timedelta(seconds=1)
        w.update(0);self.assertEqual(w.stock['Mì tươi'],10)
        w.update(0);self.assertEqual(w.stock['Mì tươi'],10)
        self.assertEqual(w.unit_cost('Mì tươi'),6120)
        w.consume('Mì tươi')
        self.assertEqual(w.totals()['2026-10-01']['ingredients'],6120)
        clock[0]=datetime(2026,10,1,23,tzinfo=VIETNAM)
        self.assertFalse(w.place_order({'Mì tươi':1}))
        clock[0]=datetime(2026,10,2,22,tzinfo=VIETNAM)
        self.assertTrue(w.place_order({'Mì tươi':1}))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);loaded=World.load(path)
            loaded._clock=lambda:datetime(2026,10,4,9,tzinfo=VIETNAM)
            loaded.update(0);self.assertEqual(loaded.stock['Mì tươi'],10)
            loaded.save(path);loaded=World.load(path)
            loaded._clock=lambda:datetime(2026,10,4,9,tzinfo=VIETNAM)
            loaded.update(0);self.assertEqual(loaded.stock['Mì tươi'],10)
        clock[0]=datetime(2026,10,30,10,tzinfo=VIETNAM)
        self.assertFalse(w.contract_active)
        self.assertFalse(w.place_order({'Mì tươi':1}))

    def test_contract_calendar_month_and_last_day_order(self):
        clock=[datetime(2028,1,31,22,tzinfo=VIETNAM)]
        w=World(clock=lambda:clock[0]);w.sign_contract()
        self.assertEqual(w.contract_until,'2028-02-29')
        clock[0]=datetime(2028,2,28,22,tzinfo=VIETNAM)
        self.assertTrue(w.place_order({'Mì tươi':1}))
        clock[0]=datetime(2028,2,29,8,tzinfo=VIETNAM)
        w.update(0);self.assertEqual(w.stock['Mì tươi'],1)

    def test_custom_menu_ticket_snapshot_cost_and_rating(self):
        w=World()
        self.assertTrue(w.save_menu_item('Soba đôi trứng',65000,{'Trứng':2,'Hành':1}))
        item=w.menu['Soba đôi trứng']
        self.assertEqual(w.recipe_cost(item['toppings']),15000)
        self.assertFalse(w.save_menu_item('Soba đôi trứng',10,{}))
        self.assertFalse(w.save_menu_item('Lỗi',100,{'Trứng':7}))
        self.assertFalse(w.save_menu_item('Lỗi',0,{}))
        for name in list(RECIPES):self.assertTrue(w.delete_menu_item(name))
        self.assertFalse(w.delete_menu_item('Soba đôi trứng'))
        for name in ['Bát/đĩa',*STOCK_COST]:w.restock(name,10)
        w.open_shop();w.spawn_left=100000
        p=w.add_party(1);w.respond(p.id,'accept');w.update(8)
        self.assertEqual(p.orders,['Soba đôi trứng']);self.assertEqual(p.paid,65000)
        self.assertFalse(w.save_menu_item('Món khác',10000,{}))
        w.collect(p.id);w.seat(p.id,0);w.start_pot(0);w.update(210);w.lift(0)
        b=w.bowls[0];w.move_prep(b.id,0)
        for name in p.recipes[0]:w.topping(b.id,name)
        w.serve(b.id,0);w.update(35)
        self.assertIn('5/5',w.reviews[-1])

    def test_migrate_v2_keeps_old_tables_and_active_tickets(self):
        import json
        w,p=self.ready_party(2);w.seat(p.id,0)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);data=json.loads(path.read_text())
            data['version']=2
            for key in ['menu','floors','stock_value','contract_until','deliveries']:data.pop(key)
            data['tables']=[{'capacity':4,'group':p.id if i==0 else 0,'dirty':0,'needs_wipe':False} for i in range(6)]
            for party in data['parties']:
                for key in ['seats','prices','recipes']:party.pop(key)
            path.write_text(json.dumps(data));loaded=World.load(path)
        self.assertEqual(len(loaded.tables),6)
        self.assertEqual(loaded.cash,w.cash)
        self.assertEqual(loaded.group(p.id).seats,[0,1])
        self.assertEqual(loaded.tables[-1].slot,5)
        self.assertEqual(loaded.unit_cost('Mì tươi'),6000)


if __name__ == '__main__':
    unittest.main()
