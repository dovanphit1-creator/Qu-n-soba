import os,sys
from pathlib import Path
from collections import deque
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'game'))
import pygame as pg
from app import App,RAW,SINK,TOPPING_RECTS
from model import POT_POS,BOWL_POS,COOK_SECONDS
from camera import CameraMixin
class TestApp(CameraMixin,App):
    def __init__(self):
        super().__init__(headless=True,persistent=False);self.init_camera()
a=TestApp();a.modal=None;a.world.open=True;a.screen_open=True
for name in a.world.stock:a.world.stock[name]=100
a.world.clean=a.world.dishes_owned=30
# Connected aisle from the unchanged dining room to cooking, topping, pass and wash.
start=(750,600);seen={start};queue=deque([start])
while queue:
    x,y=queue.popleft()
    for q in ((x+10,y),(x-10,y),(x,y+10),(x,y-10)):
        if q not in seen and a.camera_free(q):seen.add(q);queue.append(q)
for target in [(1020,400),(1020,650),(1020,780),(1120,530),(1430,530),(1120,710),(1430,710)]:
    assert target in seen,('blocked station approach',target)
assert not a.camera_free(SINK.center)
# Real model operations use exactly the same new equipment locations as the UI.
for i,pos in enumerate(POT_POS):
    assert a.source(RAW.center)==('raw',0)
    a.drop(('raw',0),pos);assert a.world.pots[i] is not None
    a.world.pots[i]=COOK_SECONDS;a.click(pos)
    b=next(b for b in a.world.bowls if b.stage=='lifted' and b.slot==i)
    a.drop(('bowl',b.id),BOWL_POS[i]);assert b.stage=='prep' and b.slot==i
    assert a.source(TOPPING_RECTS['Hành'].center)==('topping','Hành')
    a.drop(('topping','Hành'),BOWL_POS[i]);assert 'Hành' in b.toppings
# Inventory-dependent ingredients never become draggable when absent.
a.world.stock['Nori']=0;assert a.source(TOPPING_RECTS['Nori'].center) is None
# Empty-world overview and in-game close view for visual layout review.
a.buttons=[];a.render_floor();a.render_side();pg.image.save(a.canvas,str(root/'kitchen-overview-preview.png'))
a.owner.update(1020,620);a.camera_origin=a.camera_goal();a.draw();pg.image.save(a.display,str(root/'kitchen-close-preview.png'))
print('PASS: connected station aisles, fixed horu, six new pot/prep positions, toppings and stock-aware sources')
