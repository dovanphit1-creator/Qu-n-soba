"""Regression coverage for placed furniture, stale UI and delivery overflow."""
import os,sys,math
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'game'))
import pygame as pg
from v2app import V2App
from v2world import V2World
from model import Bowl
w=V2World()
# Crowded delivery slots cannot hide one carton behind another.
for _ in range(47):w.queue_goods({'Mì tươi':1},{'Mì tươi':32000})
w.delivery_tick(10)
positions=[(p['x'],p['y']) for p in w.parcels]
assert len(positions)==len(set(positions)) and len(w.parcels)+len(w.shipments)==47
assert all(math.dist(a,b)>=32 for i,a in enumerate(positions) for b in positions[i+1:])
# AI must route around a player-placed counter, not cut through it.
w=V2World();f=w.place('pass',650,440)
assert f
pos=(560,500)
for _ in range(120):
 pos=w.navigate('regression',pos,(1000,500),.1)
 assert w.walkable(pos),pos
assert math.dist(pos,(1000,500))<2,pos
# Floor switch cannot put the owner in the old fixed spawn location.
a=V2App(headless=True,persistent=False);a.modal=None;a.world.floors=2
assert a.world.place('square4',260,400,1,name='Tầng hai')
a.action(('floor',1));a.step(.016);assert a.world.walkable(a.owner,1)
# Safe UI behavior after delayed menu actions, and dropped bowls stay reserved.
a.action(('open_store',999));a.action(('serve',0,1));a.interact(('guest',999))
b=Bowl(100,0,False,[],'prep');a.world.bowls.append(b);a.world.free_bowls[100]=(300,400,1)
assert a.world.reserved_action(('serve',100,0,1))
# Opening and storing a sealed carton is one complete atomic user action.
f=a.world.place('fridge',700,400,1);assert f
a.world.parcels.append({'id':90,'name':'Mì tươi','qty':2,'cost':64000,'x':300,'y':205,'floor':0,'opened':False,'held':True})
a.hand={'kind':'parcel','id':90};a.action(('open_store',f.id))
assert not a.hand and a.world.stock['Mì tươi']==2
# Focus loss clears every held-input state, including a wash hold.
a.down=(1,1);a.clean_hold=('wash',None);a.pressed_action=('phone',)
a.event(pg.event.Event(pg.WINDOWFOCUSLOST));assert a.down is None and a.clean_hold is None and a.pressed_action is None
# Escort group no longer gets pulled back toward the ticket machine each frame.
p=a.world.add_party(1);a.world.escorting=p.id;p.phase='ready';before=(p.x,p.y)
a.world.move_guest(p,(900,800),1);assert (p.x,p.y)==before
# Every sprite sheet is bundled; rendering all 16 furniture sprites must be safe.
a.draw()
for sheet in ('furniture','environment','owner','guests','actions'):
 for i in range(16):assert a.art(sheet,i,(64,64)).get_size()==(64,64)
print('PASS: delivery overflow, obstacle paths, floor spawn, stale actions, dropped-bowl reservation, sealed storage, focus release, escort ownership, all 80 sprite cells')
# Exercise hold-to-wash using actual screen-space mouse events, then release.
a=V2App(headless=True,persistent=False);a.modal=None;w=a.world
sink=w.place('sink',800,400);a.owner.update(710,450);a.camera_origin=a.camera_goal()
w.open=True;w.sink=2;a.draw()
from camera import VIEW,ZOOM
x=VIEW.x+(sink.rect.centerx-a.camera_origin.x)*ZOOM
y=VIEW.y+(sink.rect.centery-a.camera_origin.y)*ZOOM
pos=(x*a.scale+a.offset[0],y*a.scale+a.offset[1])
a.event(pg.event.Event(pg.MOUSEBUTTONDOWN,pos=pos,button=1))
assert a.clean_hold==('wash',None)
left=w.wash_left
a.step(.5);assert w.wash_left<left
before=w.wash_left
a.event(pg.event.Event(pg.MOUSEBUTTONUP,pos=pos,button=1));a.step(.5)
assert w.wash_left==before and a.clean_hold is None
print('PASS: real pointer hold advances washing; releasing pauses the task')
# Every illustrated pot has an independent matching hit target in either layout.
a=V2App(headless=True,persistent=False);a.modal=None
f=a.world.place('stove',900,400)
for rotated in (0,1):
 f.rot=rotated
 for i in range(6):assert a.hit(f.slot_point(i))==('pot',i),(rotated,i,a.hit(f.slot_point(i)))
print('PASS: six pot sprite centers map to six correct interactive pots')
