"""Exercise 1.2 controls and, on Windows, the real tray and shutdown channel."""
import json,sys,time,tempfile,os
from pathlib import Path
from datetime import datetime
import pygame as pg
from model import World,STOCK_COST,save_path
from vn_calendar import VIETNAM


def check_staff_ui(app,output):
    app.world=World(seed=99,clock=lambda:datetime(2026,10,2,9,tzinfo=VIETNAM))
    app.init_management();app.modal=None;app.staff_panel=False;app.manager_tab='staff'
    def button(action):
        app.draw();matches=[r for r,a in app.buttons if a==action]
        assert matches,('Missing staff button',action)
        app.click(matches[0].center)
    button(('staff_tab','hire'))
    assert not app.world.applicants()
    button(('post_recruitment',))
    candidate=next(c for c in app.world.applicants() if c['role']=='contract')
    button(('hire_review',candidate['id']));button(('hire_confirm',))
    employee=app.world.employee(candidate['id']);assert employee and not employee['enabled']
    button(('staff_tab','team'));button(('shift_toggle',employee['id']));assert employee['enabled']
    button(('overtime',employee['id'],1));assert employee['shift_hours']==8 and employee['overtime_hours']==1
    button(('staff_tab','leave'));button(('request_leave',));assert employee['leave_sent']=='2026-10'
    button(('staff_tab','coverage'));assert app.world.coverage_report()
    app.draw();pg.image.save(app.canvas,str(Path(output).with_name('staff-preview.png')))
    button(('staff_tab','clock'));app.draw()
    pg.image.save(app.canvas,str(Path(output).with_name('timeclock-preview.png')))
    button(('staff_tab','settings'))
    app.draw();pg.image.save(app.canvas,str(Path(output).with_name('background-preview.png')))
    employee['leaves']['2026-10']=[]
    for name in ['Bát/đĩa',*STOCK_COST]:app.world.restock(name,4)
    app.step(1);assert app.world.open
    button(('staff_panel',));assert app.staff_panel
    button(('enter_shop',));assert not app.staff_panel
    path=Path(output).with_name('staff-test-save.json');app.world.save(path)
    assert World.load(path).employees==app.world.employees
    app.world=World();app.init_management();app.staff_panel=False


def check_windows_background(App,output):
    if sys.platform!='win32':return
    from background import Background,request_path
    previous=os.environ.get('LOCALAPPDATA')
    try:
        with tempfile.TemporaryDirectory(prefix='quanmi-tray-test-') as profile:
            os.environ['LOCALAPPDATA']=profile
            pg.quit()
            video=os.environ.pop('SDL_VIDEODRIVER',None)
            app=App(headless=True);app.modal=None
            for name in ('Bát/đĩa','Mì tươi','Nước dùng','Hành'):app.world.restock(name,2)
            assert app.world.open_shop();app.world.spawn_left=100000;app.world.start_pot(0)
            app.background=Background(app)
            assert app.background.enable(True),'Tray could not start'
            app.world.background_enabled=True
            app.event(pg.event.Event(pg.QUIT))
            assert app.running and app.background.hidden,'Window X must keep background game running'
            app.step(3);assert app.world.pots[0]>=3
            app.background.show();assert not app.background.hidden
            app.background.hide()
            p=request_path('shutdown');p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps({'exe':sys.executable,'at':time.time()}),encoding='utf-8')
            app.step(.1);assert not app.running
            restored=World.load(save_path());assert restored.pots[0]>=3 and restored.open
            app.background.enable(False)
            app.background.stop();pg.quit()
            if video is not None:os.environ['SDL_VIDEODRIVER']=video
            Path(output).with_name('background-verification.json').write_text(json.dumps({'ok':True,'checks':['tray-start','close-hides-game','background-cooking','restore-window','installer-shutdown-saves']}),encoding='utf-8')
    finally:
        if previous is None:os.environ.pop('LOCALAPPDATA',None)
        else:os.environ['LOCALAPPDATA']=previous
