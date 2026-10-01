import json
from pathlib import Path
from datetime import datetime
import pygame as pg
from model import World
from vn_calendar import VIETNAM

def check_shifts_ui(app,output):
    app.world=World(seed=55,clock=lambda:datetime(2026,10,5,8,tzinfo=VIETNAM));app.init_management()
    app.modal=None;app.staff_panel=False;app.manager_tab='staff';app.staff_tab='shifts'
    app.action(('shift_name',));app.event(pg.event.Event(pg.TEXTINPUT,text='Ca của chủ quán'))
    app.event(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN));app.action(('shift_create',))
    assert app.world.shifts[-1]['name']=='Ca của chủ quán'
    app.draw();assert any(a[0]=='shift_available' for r,a in app.buttons)
    pg.image.save(app.canvas,str(Path(output).with_name('shifts-preview.png')))
    app.world.post_recruitment();c=next(c for c in app.world.candidates if c['role']=='contract')
    app.staff_review_id=c['id'];app.modal='hire_contract';app.draw()
    app.action(('hire_confirm',));e=app.world.employee(c['id'])
    assert e['agreed_shift']==c['requested_shift'] and not app.world.set_shift(e['id'],60,8)
    app.staff_tab='team';app.draw();assert not any(a[0]=='shift_start' for r,a in app.buttons)
    app.staff_tab='shifts';app.action(('shifts_view',));app.draw()
    assert any(a==('shift_day',1) for r,a in app.buttons)
    pg.image.save(app.canvas,str(Path(output).with_name('shift-registration-preview.png')))
    Path(output).with_name('shifts-verification.json').write_text(json.dumps(dict(ok=True,checks=['unicode-custom-shift','cv-shift-snapshot','contract-shift-locked','daily-registration-ui'])),encoding='utf-8')
    app.world=World();app.init_management();app.staff_panel=False;app.modal=None
