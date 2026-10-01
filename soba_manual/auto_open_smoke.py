"""Real scheduled arrival must reveal the restaurant and its usable controls."""
from datetime import datetime,timedelta
from pathlib import Path
import pygame as pg
from model import World,STOCK_COST
from vn_calendar import VIETNAM


def scheduled_world():
    now=[datetime(2026,10,5,7,59,59,tzinfo=VIETNAM)]
    w=World(seed=132,clock=lambda:now[0])
    w.post_recruitment()
    c=next(c for c in w.applicants() if c['role']=='contract')
    w.hire(c['id']);e=w.employee(c['id']);e['leaves']['2026-10']=[]
    w.set_shift(e['id'],480,8)
    for name in ('Bát/đĩa',*STOCK_COST):w.restock(name,4)
    w.spawn_left=1e9
    return w,now,e


def check_auto_open_ui(app,output):
    app.world,now,e=scheduled_world()
    app.screen_open=False;app.staff_panel=True;app.modal='hire_contract'
    app.manager_tab='staff';app.input_focus='name';app.drag=('raw',0)
    app.down=(100,100);app.pending_drag=('raw',0)
    now[0]+=timedelta(seconds=1);app.step(1)
    assert e['present'] and app.world.open
    assert not app.staff_panel and app.modal is None and app.input_focus is None
    assert app.drag is None and app.down is None and app.pending_drag is None
    app.draw();assert ('close',) in [a for r,a in app.buttons]
    pg.image.save(app.canvas,str(Path(output).with_name('auto-open-preview.png')))
    def click(action):
        app.draw();r=next(r for r,a in app.buttons if a==action);app.click(r.center)
    click(('staff_panel',));assert app.staff_panel
    app.step(1);app.draw();assert app.staff_panel
    click(('enter_shop',));assert not app.staff_panel
    app.draw();assert ('close',) in [a for r,a in app.buttons]
    app.world=World();app.screen_open=False;app.init_management();app.modal=None
