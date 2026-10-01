"""Exercise per-baito support controls inside the graphical application."""
from datetime import datetime
from pathlib import Path
import pygame as pg
from model import World,STOCK_COST
from vn_calendar import VIETNAM


def check_baito_kitchen_ui(app,output):
    w=World(seed=140,clock=lambda:datetime(2026,10,2,9,tzinfo=VIETNAM))
    for name in ('Bát/đĩa',*STOCK_COST):w.restock(name,20)
    w.spawn_left=1e9;w.post_recruitment()
    c=next(c for c in w.applicants() if c['role']=='baito');w.hire(c['id'])
    e=w.employee(c['id']);e['leaves']['2026-10']=[];w.set_shift(c['id'],480,10)
    e['plans']['2026-10-02']=dict(segments=[[480,1080,'baito']],start=480,end=1080,late=0,absence=False,early=0)
    app.world=w;app.screen_open=False;app.init_management();app.modal=None
    app.step(0);assert w.open;app.staff_panel=True
    def click(action):
        app.draw();r=next(r for r,a in app.buttons if a==action);app.click(r.center)
    assert e['kitchen_support'];click(('kitchen_support',e['id']));assert not e['kitchen_support']
    click(('kitchen_support',e['id']));assert e['kitchen_support']
    app.draw();pg.image.save(app.canvas,str(Path(output).with_name('baito-kitchen-preview.png')))
    click(('enter_shop',));assert not app.staff_panel
    p=w.add_party(1);p.drinks=[''];p.drinks_served=['']
    assert w.respond(p.id,'accept');w.update(p.buy_seconds);w.collect(p.id);w.seat(p.id,0)
    e['job']=None
    assert w.choose_staff_job(e,[e])[0][0]=='start'
    path=Path(output).with_name('baito-kitchen-save.json');w.save(path)
    assert World.load(path).employee(e['id'])['kitchen_support']
    app.world=World();app.screen_open=False;app.init_management();app.modal=None
