import os, sys, ast
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'game'))
import pygame as pg
from app import App, RAW
from camera import CameraMixin, VIEW, ZOOM, CONTROLS
from model import POT_POS

class TestApp(CameraMixin,App):
    def __init__(self):
        super().__init__(headless=True,persistent=False)
        self.init_camera()

a=TestApp(); a.modal=None
a.world.open=True; a.screen_open=True
a.world.stock['Mì tươi']=20
a.world.clean=10
def logical_to_display(p):return (p[0]*a.scale+a.offset[0],p[1]*a.scale+a.offset[1])
def world_to_display(p):return logical_to_display((VIEW.x+(p[0]-a.camera_origin.x)*ZOOM,VIEW.y+(p[1]-a.camera_origin.y)*ZOOM))
a.draw()
# Real movement and follow, including wall and counter collision.
before=a.owner.copy(); origin=a.camera_origin.copy()
a.event(pg.event.Event(pg.KEYDOWN,key=pg.K_d))
for _ in range(60):a.step(1/60)
a.event(pg.event.Event(pg.KEYUP,key=pg.K_d))
assert a.owner.x>before.x+150 and a.camera_origin.x>origin.x
assert a.camera_free(a.owner)
assert not a.camera_free((836,396)) and not a.camera_free((100,260))
# Projected points round-trip while the fixed UI keeps its own coordinates.
for p in (a.owner, (a.camera_origin.x+100,a.camera_origin.y+100)):
 q=a.point(world_to_display(p)); assert abs(q[0]-p[0])<.01 and abs(q[1]-p[1])<.01
assert a.point(logical_to_display((1400,300)))==(1400,300)
# Actual event chain: drag fresh noodles into a pot after the camera moves.
a.owner.update(750,620);a.camera_origin=a.camera_goal();a.draw()
start=world_to_display(RAW.center);end=world_to_display(POT_POS[0])
a.event(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=start))
a.event(pg.event.Event(pg.MOUSEMOTION,pos=end,rel=(0,0),buttons=(1,0,0)))
assert a.drag==('raw',0)
frozen=a.camera_origin.copy();a.camera_keys.add(pg.K_a);a.step(.1)
assert a.camera_origin!=frozen
end=world_to_display(POT_POS[0])
a.event(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=end));a.camera_keys.clear()
assert a.world.pots[0] is not None
# Hold-to-clean keeps the same world target and camera until release.
a.world.sink=2;a.world.dishes_owned=12
from app import SINK
a.owner.update(750,365);a.camera_origin=a.camera_goal();a.draw()
sink=world_to_display(SINK.center)
a.event(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=sink))
assert a.clean_hold==('wash',None)
frozen=a.camera_origin.copy();a.step(.1);assert a.camera_origin==frozen
a.event(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=sink));assert a.clean_hold is None
# On-screen direction pad moves and stops on release without triggering a drag.
a.owner.update(370,570);a.camera_origin=a.camera_goal()
pos=logical_to_display(CONTROLS[3][0].center);x=a.owner.x
a.event(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=pos));a.step(.1)
assert a.owner.x>x and a.down is None
a.event(pg.event.Event(pg.MOUSEBUTTONUP,button=1,pos=pos));assert a.camera_touch is None
# Dialogs and management revert to unprojected input; focus loss clears movement.
a.modal='help';assert a.point(logical_to_display((500,500)))==(500,500)
a.camera_keys.add(pg.K_w);a.event(pg.event.Event(pg.WINDOWFOCUSLOST));assert not a.camera_keys
a.modal=None;a.draw()
pg.image.save(a.display,str(root/'camera-preview.png'))
print('PASS: movement, follow, collision, fixed UI, projected drag/drop while panning, stable cleanup, touch pad, modal input, focus loss')
