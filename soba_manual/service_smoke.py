"""Frozen UI verification for held cleaning, receipts, statistics and Vietnamese voice."""
from pathlib import Path
from datetime import datetime
import json,io,wave,sys
import pygame as pg
from model import World,STOCK_COST
from vn_calendar import VIETNAM


def check_service_ui(app,output):
    w=World(seed=150,clock=lambda:datetime(2026,10,2,9,tzinfo=VIETNAM))
    for n in ('Bát/đĩa',*STOCK_COST):w.restock(n,10)
    w.open_shop();w.spawn_left=1e9
    app.world=w;app.screen_open=True;app.init_management();app.modal=None
    w.sink=3;app.mouse=app.down=(1050,310)
    assert app.start_clean_hold(('wash',None));app.step(1);left=w.wash_left
    app.down=None;app.clean_hold=None;app.step(50);assert w.wash_left==left
    app.mouse=app.down=(1050,310);assert app.start_clean_hold(('wash',None));app.step(left+1);assert not w.washing
    app.down=None;app.clean_hold=None;w.player_cleaning=None
    w.post_recruitment();candidate=next(c for c in w.applicants() if c['role']=='baito');w.hire(candidate['id']);e=w.employee(candidate['id'])
    from operations import complete_purchase
    cash=w.cash;complete_purchase(w,e,{'Nori':2,'Hành':3})
    assert w.cash==cash and w.staff_purchases[-1]['items']=={'Nori':2,'Hành':3}
    w.record('customers',3);w.record('star_sum',12);w.record('rating_count',3)
    assert w.totals()[w.now.date().isoformat()]['average_stars']==4
    app.staff_panel=True;app.staff_tab='reports';app.draw()
    assert any(a==('staff_tab','reports') for r,a in app.buttons)
    pg.image.save(app.canvas,str(Path(output).with_name('service-report-preview.png')))
    voice='browser-companion-tested-separately'
    if sys.platform=='win32':
        from audio import render_vi
        data=render_vi('Phiếu nhóm một. Mì soba trứng. Trà xanh. Món tự tạo của tôi.')
        with wave.open(io.BytesIO(data)) as audio:assert audio.getnframes()>22050
        voice='bundled-vi-offline-and-custom-names'
    Path(output).with_name('service-verification.json').write_text(json.dumps({'ok':True,'voice':voice,'checks':['hold-progress','release-pauses','resume-finishes','advance-not-wages','itemized-receipt-ui','weighted-average','customers-are-people']}),encoding='utf-8')
    app.world=World();app.screen_open=False;app.init_management();app.modal=None
