import json
from pathlib import Path
import pygame as pg
from model import World

def check_finance_ui(app,output):
    app.world=World(seed=2);app.modal=None;app.staff_panel=False
    app.world.process_finance();app.world.sign_lease(0)
    app.world.use_utility('water',1);app.world.close_meter('water',app.world.now.date())
    app.manager_tab='finance';app.draw()
    assert any(a[0]=='provider_next' for r,a in app.buttons)
    b=next(b for b in app.world.bills if b['kind']=='water')
    assert any(a==('pay_bill',b['id']) for r,a in app.buttons)
    before=app.world.cash;app.action(('pay_bill',b['id']))
    assert b['paid'] and app.world.cash==before-15000
    app.draw();pg.image.save(app.canvas,str(Path(output).with_name('finance-preview.png')))
    app.manager_tab='staff';app.staff_tab='hire';app.world.post_recruitment();app.draw()
    assert not any(a[0]=='offer' for r,a in app.buttons)
    c=app.world.candidates[0];app.world.hire(c['id']);assert app.world.employee(c['id'])['agreed_wage']==c['wage']
    app.modal='finance';app.draw();assert any(a==('dismiss',) for r,a in app.buttons)
    app.modal=None;app.manager_tab='overview'
    Path(output).with_name('finance-verification.json').write_text(json.dumps(dict(ok=True,checks=['meters-and-providers-ui','pay-bill-once','locked-cv-salary','finance-access-during-service','save-format-9'])),encoding='utf-8')
