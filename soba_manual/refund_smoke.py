"""Verify real refund controls and saved state in the graphical executable."""
from pathlib import Path
import pygame as pg
from model import World,STOCK_COST


def check_refund_ui(app,output):
    app.world=World(seed=81);app.modal=None;app.staff_panel=False
    for name in ('Bát/đĩa',*STOCK_COST):app.world.restock(name,4)
    assert app.world.open_shop();app.sync_shop_screen();app.world.spawn_left=1e9
    p=app.world.add_party(1);p.drinks=[''];p.drinks_served=['']
    assert app.world.respond(p.id,'accept');app.world.update(p.buy_seconds)
    app.selected=p.id;cash=app.world.cash
    def click(action):
        app.draw();rect=next(r for r,a in app.buttons if a==action);app.click(rect.center)
    click(('refund_review',p.id));assert app.modal=='refund'
    app.draw();pg.image.save(app.canvas,str(Path(output).with_name('refund-preview.png')))
    click(('dismiss',));assert p.phase=='ticket' and app.world.cash==cash
    click(('refund_review',p.id));click(('refund_confirm',p.id))
    assert p.phase=='leaving' and app.world.cash==cash-p.paid and p.refunded==p.paid
    path=Path(output).with_name('refund-save.json');app.world.save(path)
    saved=World.load(path);assert saved.group(p.id).refunded==p.paid and not saved.refund_party(p.id)
    app.world=World();app.init_management();app.staff_panel=False;app.modal=None
