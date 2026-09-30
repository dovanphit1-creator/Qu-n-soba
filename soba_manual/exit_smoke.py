"""Real event-loop regression, also run inside the built Windows executable."""
import os
import tempfile
import pygame as pg
from model import World, STOCK_COST, save_path


def check_window_exit(App):
    previous=os.environ.get('LOCALAPPDATA')
    try:
        with tempfile.TemporaryDirectory(prefix='quanmi-exit-test-') as profile:
            os.environ['LOCALAPPDATA']=profile
            app=App(headless=True)
            w=app.world
            for name in ['Bát/đĩa',*STOCK_COST]:
                assert w.restock(name,12)
            assert w.open_shop()
            w.spawn_left=100000
            party=w.add_party(2)
            assert w.respond(party.id,'accept')
            w.update(8)
            assert w.collect(party.id)
            assert w.seat(party.id,0)
            assert w.start_pot(0)
            w.update(73)
            app.modal='help'
            before=save_path().with_name('expected.json')
            w.save(before)
            # Real OS close event through the same loop as the shipped game.
            pg.event.clear()
            pg.event.post(pg.event.Event(pg.QUIT))
            app.run()
            assert not app.running and app.world.open
            assert save_path().read_bytes()==before.read_bytes(), 'Exit changed active shift'
            restored=App(headless=True)
            assert restored.has_save and restored.world.open
            assert restored.world.cash==w.cash
            assert restored.world.pots==w.pots
            assert restored.world.parties==w.parties
            assert restored.world.tables==w.tables
            assert restored.world.stock==w.stock
            assert restored.world.ledger==w.ledger
            # Closed-shop exit still works without a simulation step after saving.
            restored.world=World()
            pg.event.clear()
            pg.event.post(pg.event.Event(pg.QUIT))
            restored.run()
            assert not restored.running and not World.load(save_path()).open
    finally:
        pg.quit()
        if previous is None:os.environ.pop('LOCALAPPDATA',None)
        else:os.environ['LOCALAPPDATA']=previous
