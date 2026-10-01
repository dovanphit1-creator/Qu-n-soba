"""Exercise shortage recovery through the running staff loop, not direct jobs."""
import unittest,tempfile
from pathlib import Path
from model import World
from operations import missing_stock,required_stock
import test_baito_kitchen as fixtures


class StockShutdownTests(unittest.TestCase):
    def fixture(self,policy):
        f=fixtures.BaitoKitchenTests();f.setUp();f.e['shortage_policy']=policy
        return f

    def empty(self,w):
        for n in w.stock:w.stock[n]=0

    def test_empty_idle_shop_buys_supplies_without_owner_money(self):
        f=self.fixture('restock');w=f.w;self.empty(w);cash=w.cash
        self.assertTrue(missing_stock(w));w.update(0)
        self.assertEqual(f.e['job']['action'][0],'shop')
        f.tick(300)
        self.assertTrue(w.open);self.assertFalse(w.closing)
        self.assertTrue(w.staff_purchases);self.assertEqual(w.cash,cash)
        self.assertEqual(w.opening_blocker(),'')
        self.assertIn('đã ứng',w.staff_reports[-1]['text'])

    def test_empty_idle_shop_finishes_abandoned_cleaning_and_closes(self):
        f=self.fixture('close');w=f.w;self.empty(w)
        w.clean-=2;w.sink=2;w.wash(owner='player')
        w.tables[0].needs_wipe=True;w.tables[0].soil=2
        w.mark_dirty(0,'Nước rửa bát',2)
        w.update(0);self.assertTrue(w.closing)
        f.tick(450)
        self.assertFalse(w.open);self.assertFalse(w.dirt)
        self.assertFalse(w.sink);self.assertFalse(w.washing)
        self.assertFalse(w.tables[0].needs_wipe)
        self.assertIn('Đã dọn sạch và đóng quán',w.staff_reports[-1]['text'])
        w.update(0);self.assertFalse(w.open)

    def test_finishes_covered_last_order_before_closing(self):
        f=self.fixture('close');w=f.w;p=f.seat_customer()
        needed=required_stock(w);self.empty(w)
        for n,q in needed.items():w.stock[n]=q
        self.assertFalse(missing_stock(w));w.update(0)
        self.assertFalse(w.closing)
        f.tick(1600)
        self.assertEqual(w.served,1);self.assertEqual(p.refunded,0)
        self.assertFalse(w.open)

    def test_unpaid_queue_leaves_and_paid_unservable_ticket_is_refunded(self):
        f=self.fixture('close');w=f.w;p=f.seat_customer()
        q=w.add_party(1);q.drinks=[''];q.drinks_served=['']
        self.assertTrue(w.respond(q.id,'accept'))
        self.empty(w);w.update(0)
        self.assertEqual(q.phase,'leaving');self.assertEqual(q.paid,0)
        self.assertEqual(p.refunded,p.paid)
        f.tick(500);self.assertFalse(w.open)

    def test_advance_budget_exhaustion_falls_back_to_cleanup(self):
        f=self.fixture('restock');w=f.w;self.empty(w)
        w.staff_purchases.append({'employee':f.e['id'],'date':w.now.date().isoformat(),'cost':500000,'reimbursed':True})
        w.mark_dirty(0,'Nước rửa bát',1)
        w.update(0);self.assertTrue(w.closing)
        f.tick(100);self.assertFalse(w.open)

    def test_other_menu_cannot_reopen_stock_shutdown_until_new_delivery(self):
        f=self.fixture('close');w=f.w;p=f.seat_customer()
        w.menu={'Món khác':{'toppings':['Hành'],'price':30000}}
        w.stock[p.recipes[0][0]]=0
        w.update(0);self.assertTrue(w.closing)
        f.tick(500);self.assertFalse(w.open)
        self.assertIn('Đã đóng sớm',w.opening_blocker(automatic=True))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);loaded=World.load(path)
            loaded._clock=lambda:f.clock[0]
            self.assertIn('Đã đóng sớm',loaded.opening_blocker(automatic=True))
        w.restock('Hành',1);w.update(0)
        self.assertTrue(w.open)


if __name__=='__main__':unittest.main()
