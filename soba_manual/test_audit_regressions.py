import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from model import World,COOK_SECONDS,DRINK_PRICES
from main import App,SINK,DIRT_POS
import operations
import test_baito_kitchen as fixtures


class AuditRegressionTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.BaitoKitchenTests();f.setUp();f.e['shortage_policy']='restock';return f

    def test_failed_load_preserves_original_through_autosave_and_exit(self):
        for version in (None,999):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as d:
                path=Path(d)/'save.json';w=World();w.cash=7654321;w.save(path)
                data=json.loads(path.read_text(encoding='utf-8'))
                if version is None:data.pop('version')
                else:data['version']=version
                path.write_text(json.dumps(data),encoding='utf-8');original=path.read_bytes()
                with patch('main.save_path',return_value=path):
                    a=App(headless=True);self.assertTrue(a.save_blocked);self.assertEqual(a.modal,'save_error')
                    a.draw();self.assertIn(('quit',),[action for r,action in a.buttons])
                    a.step(16);self.assertFalse(a.persist());a.action(('quit',))
                self.assertEqual(path.read_bytes(),original);self.assertEqual(list(Path(d).glob('*.bak')),[])

    def test_confirmed_new_game_keeps_exact_backup_before_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';original=b'{"cash":7654321}';path.write_bytes(original)
            with patch('main.save_path',return_value=path):
                a=App(headless=True);a.action(('modal','confirm_new'))
                self.assertEqual(path.read_bytes(),original);self.assertTrue(a.save_blocked)
                a.action(('new',));self.assertFalse(a.save_blocked)
                backups=list(Path(d).glob('save.json.*.bak'));self.assertEqual(len(backups),1)
                self.assertEqual(backups[0].read_bytes(),original)
                self.assertEqual(World.load(path).cash,10000000)
                a.world.cash=1234567;a.persist();self.assertEqual(World.load(path).cash,1234567)

    def test_failed_backup_does_not_replace_or_unlock_profile(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';original=b'{"cash":7654321}';path.write_bytes(original)
            with patch('main.save_path',return_value=path):
                a=App(headless=True);old=a.world
                with patch('shutil.copy2',side_effect=PermissionError('read only')):a.action(('new',))
                self.assertIs(a.world,old);self.assertTrue(a.save_blocked);a.step(16)
                self.assertEqual(path.read_bytes(),original)

    def test_player_resumes_all_cleaning_after_worker_leaves_or_is_deleted(self):
        for kind in ('wash','wipe','sweep'):
            for deleted in (False,True):
                with self.subTest(kind=kind,deleted=deleted):
                    f=self.fixture();w=f.w;e=f.e;a=App(headless=True,persistent=False)
                    a.world=w;a.modal=None;a.screen_open=True
                    if kind=='wash':
                        w.clean-=2;w.sink=2;w.wash(owner=e['id']);target=('wash',None);point=SINK.center
                    elif kind=='wipe':
                        w.tables[0].needs_wipe=True;w.tables[0].soil=2;w.wipe(0,owner=e['id']);target=('wipe',0);point=w.table_position(0)
                    else:
                        w.mark_dirty(0,'Vết nước',2);w.sweep(2,owner=e['id']);target=('sweep',2);point=DIRT_POS[2]
                    w.update(1);left=getattr(w,kind+'_left');water=w.totals()[w.now.date().isoformat()]['water']
                    if deleted:w.employees.remove(e)
                    else:e['present']=False;e['plans'][w.now.date().isoformat()]['segments']=[]
                    self.assertTrue(a.start_clean_hold(target));self.assertEqual(getattr(w,kind+'_left'),left)
                    self.assertEqual(w.totals()[w.now.date().isoformat()]['water'],water)
                    a.mouse=a.down=point
                    with patch.object(w.rng,'random',return_value=.99):a.step(1);a.step(left+1)
                    self.assertEqual(getattr(w,kind+'_left'),0)
                    if kind=='wash':self.assertEqual(w.washing,0);self.assertEqual(w.clean,20)
                    elif kind=='wipe':self.assertFalse(w.tables[0].needs_wipe)
                    else:self.assertNotIn(2,w.dirt)

    def test_player_does_not_steal_cleaning_from_present_worker(self):
        f=self.fixture();a=App(headless=True,persistent=False);a.world=f.w;a.modal=None
        f.w.sink=2;f.w.wash(owner=f.e['id'])
        self.assertFalse(a.start_clean_hold(('wash',None)))
        self.assertEqual(f.w.wash_owner,f.e['id'])

    def start_order(self,f):
        p=f.seat_customer()
        for _ in range(30):
            f.tick(1)
            if f.w.staff_cooking:break
        self.assertTrue(f.w.staff_cooking)
        pot=int(next(iter(f.w.staff_cooking)));return p,pot

    def test_manual_discard_and_lift_do_not_strand_staff_order(self):
        for action in ('discard_pot','discard_bowl','lift'):
            with self.subTest(action=action):
                f=self.fixture();w=f.w;p,pot=self.start_order(f)
                if action=='discard_pot':
                    self.assertTrue(w.discard_pot(pot));self.assertNotIn(str(pot),w.staff_cooking)
                else:
                    w.pots[pot]=COOK_SECONDS;self.assertTrue(w.lift(pot));bid=w.bowls[-1].id
                    self.assertEqual(w.staff_cooking[str(pot)]['bid'],bid)
                    if action=='discard_bowl':
                        self.assertTrue(w.discard_bowl(bid));self.assertNotIn(str(pot),w.staff_cooking)
                f.tick(1600);self.assertEqual(w.served,1);self.assertEqual(p.refunded,0)
                self.assertFalse(w.staff_cooking)

    def test_old_save_orphans_are_repaired_without_reconsuming_noodles(self):
        f=self.fixture();w=f.w;p,pot=self.start_order(f);stock=w.stock['Mì tươi']
        w.pots[pot]=COOK_SECONDS;w.lift(pot);bid=w.bowls[-1].id
        w.staff_cooking[str(pot)].pop('bid');operations.reconcile_cooking(w)
        self.assertEqual(w.staff_cooking[str(pot)]['bid'],bid);self.assertEqual(w.stock['Mì tươi'],stock)
        w.bowls.clear();operations.reconcile_cooking(w);self.assertFalse(w.staff_cooking)
        f.tick(1600);self.assertEqual(w.served,1)

    def test_manual_close_stays_closed_for_market_and_survives_reload(self):
        f=self.fixture();w=f.w;self.assertTrue(w.close_shop())
        w.update(0);self.assertFalse(w.open);self.assertTrue(w.restock('Mì tươi',2))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';w.save(path);loaded=World.load(path);loaded._clock=lambda:f.clock[0]
            loaded.update(0);self.assertFalse(loaded.open)
            self.assertTrue(loaded.open_shop());loaded.update(0);self.assertTrue(loaded.open)

    def test_manual_close_request_is_respected_after_staff_cleanup(self):
        f=self.fixture();w=f.w;w.mark_dirty(0,'Vết nước',2)
        self.assertFalse(w.close_shop());f.tick(300)
        self.assertFalse(w.open);w.update(0);self.assertFalse(w.open)
        self.assertEqual(w.day_decisions[w.now.date().isoformat()],'player')

    def test_group_drinks_and_accepted_reservations_never_exceed_stock(self):
        f=self.fixture();w=f.w;w.employees=[]
        for name in DRINK_PRICES:w.stock[name]=0
        w.stock['Coca-Cola']=1
        with patch.object(w.rng,'random',return_value=0):p=w.add_party(4)
        self.assertEqual(p.drinks.count('Coca-Cola'),1)
        self.assertTrue(w.respond(p.id,'accept'))
        q=w.add_party(1);q.drinks=['Coca-Cola'];q.drinks_served=['']
        self.assertFalse(w.party_stock_available(q));self.assertFalse(w.respond(q.id,'accept'))
        cash=w.cash;w.update(p.buy_seconds)
        self.assertEqual(p.paid,sum(p.prices)+DRINK_PRICES['Coca-Cola']);self.assertEqual(w.cash,cash+p.paid)
        self.assertEqual(q.paid,0);self.assertEqual(w.stock['Coca-Cola'],1)

    def test_acceptance_rechecks_drinks_if_stock_changes_at_door(self):
        f=self.fixture();w=f.w;p=w.add_party(1);p.drinks=['Coca-Cola'];p.drinks_served=['']
        w.stock['Coca-Cola']=0;cash=w.cash
        self.assertFalse(w.respond(p.id,'accept'));self.assertEqual(p.phase,'door');self.assertEqual(w.cash,cash)


if __name__=='__main__':unittest.main()
