"""Exercise real projected input and contextual guest actions in the web app."""
import os,sys
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'game'))
import pygame as pg
from app import App,TICKET
from camera import CameraMixin,VIEW,ZOOM,DESK,DOOR
class TestApp(CameraMixin,App):
    def __init__(self):
        super().__init__(headless=True,persistent=False);self.init_camera()
a=TestApp();a.modal=None;a.world.open=True;a.screen_open=True
a.world.clean=20;a.world.dishes_owned=20
for name in a.world.stock:a.world.stock[name]=100
p=a.world.add_party(2)
def tap(xy,world=False):
    if world:xy=(VIEW.x+(xy[0]-a.camera_origin.x)*ZOOM,VIEW.y+(xy[1]-a.camera_origin.y)*ZOOM)
    pos=(a.offset[0]+xy[0]*a.scale,a.offset[1]+xy[1]*a.scale)
    a.event(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=pos))
    a.event(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=pos))
def place(x,y):
    a.owner.update(x,y);a.camera_origin=a.camera_goal();a.draw()
# No permanent side-panel buttons; the view now fills the whole width.
place(370,380)
assert VIEW.right==1600
assert not any(action[0] in ('answer','close','refund_review','staff_panel') for _,action in a.buttons)
tap((p.x,p.y),True)
assert a.modal is None and p.phase=='door' and 'gần' in a.last_warning
place(280,300);tap((p.x,p.y),True);assert a.modal=='guest'
a.draw();assert len([1 for _,action in a.buttons if action[0]=='answer'])==3
pg.image.save(a.display,str(root/'context-preview.png'))
tap((800,420));assert a.modal is None and p.phase not in ('door','waiting')
# Paid receipt opens in a dialog, then drag-to-seat remains available.
p.phase='ticket';p.x,p.y=667,452;p.paid=sum(p.prices)
place(742,425);tap(TICKET.center,True)
assert p.ticket_read and a.modal=='guest'
a.draw();assert any(action[0]=='refund_review' for _,action in a.buttons)
tap((800,800));assert a.modal is None
a.draw();assert a.source((p.x,p.y))==('party',p.id)
# Staff may take a guest while a dialog is open: stale choices must do nothing.
q=a.world.add_party(1);q.x,q.y=280,220
place(280,300);tap((q.x,q.y),True);assert a.modal=='guest'
q.phase='leaving';a.action(('answer',q.id,'accept'));assert q.phase=='leaving' and a.modal is None
# Entrance closes only on interaction; management remains reachable in the world.
a.world.parties=[]
place(485,310);tap(DESK.center,True);assert a.modal=='desk'
a.draw();tap((800,310));assert a.staff_panel and a.modal is None
a.action(('enter_shop',));assert not a.staff_panel
place(280,300);tap(DOOR.center,True);assert a.modal=='entrance'
a.draw();assert any(action[0]=='close' for _,action in a.buttons)
a.modal=None;place(480,480);pg.image.save(a.display,str(root/'context-world-preview.png'))
print('PASS: full-width world, no sidebar actions, proximity gate, three guest choices, receipt, drag source, stale guest, staff board and entrance')
